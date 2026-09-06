"""Canonicalize legacy Firestore doc ids (``tb<Table>_N``) to natural keys.

Background:
    The first Firestore migration (2026-07) wrote every document under
    fallback ids like ``tbEfetivoPM_0`` / ``tbOPM_1`` instead of the project's
    natural keys (matricula, opm_id, cargo_id, ...).  ``app.firebase_db._resolve``
    masks the problem with a fallback equality query on the natural field, but
    every keyed lookup still pays an extra query.

    This script moves each legacy doc to its canonical id:
        set(natural_id, data)  +  delete(legacy_id)      (2 writes per doc)

Usage:
    py -3.14 scripts/canonicalize_ids.py [--collection COL] [--limit N]
        [--dry-run] [--service-account PATH] [--scan-limit N] [--self-test]

Quota warning:
    efetivopm alone has ~30.5k legacy docs -> ~61k writes.  Firestore free tier
    (Spark) allows ~20k writes/day, so run repeatedly with --limit (resume is
    persisted to ``instance/canonicalize_state.json``).  The collection scan
    also costs ~1 read/doc (+~30.5k reads for efetivopm on the first pass).
"""
import argparse
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.firebase_db import _safe  # noqa: E402

try:
    from app.firebase_db import get_fs  # noqa: E402
except Exception:  # pragma: no cover - importable without init
    get_fs = None

# Single-field natural keys (mirror of app.firebase_db.NATURAL_KEYS).
NATURAL_KEYS = {
    'usuarios': 'matricula',
    'efetivopm': 'matricula',
    'cargos': 'cargo_id',
    'opms': 'opm_id',
    'tabela_valores': 'id',
    'municipios': 'id',
    'viaturas': 'prefixo',
    'eventos': 'evento_id',
    'opm_eventos': 'opm_evento_id',
    'escala_p2': 'id',
    'escala_p2_meta': 'id',
    'escala_p2_legendas': 'id',
    'escalas_salvas': 'escala_salva_id',
    'ocorrencias': 'id',
    'ocorrencia_meta': 'data_ref',
    'ocorrencia_config': 'chave',
}

# Composite-key collections: canonical id is built from several fields.
COMPOSITE_KEYS = {
    'escalas': lambda d: '{}_{}_{}'.format(
        d.get('opm_evento_id'), d.get('matricula'), d.get('escala_data')),
    'ocorrencia_eventos': lambda d: '{}_{}_{}'.format(
        d.get('data_ref'), d.get('grupo'), d.get('metrica')),
}

# Small collections first, the 30k swamp last so a partial run still helps.
COLLECTION_ORDER = (
    'cargos', 'opms', 'usuarios', 'eventos', 'opm_eventos', 'viaturas',
    'tabela_valores', 'municipios', 'escala_p2', 'escala_p2_meta',
    'escala_p2_legendas', 'escalas_salvas', 'ocorrencias', 'ocorrencia_meta',
    'ocorrencia_config', 'ocorrencia_eventos', 'escalas', 'efetivopm',
)

DEFAULT_RESUME = os.path.join(ROOT, 'instance', 'canonicalize_state.json')


def canonical_id_for(collection, data):
    """Return the canonical doc id for ``data`` or None if it can't be derived."""
    if collection in COMPOSITE_KEYS:
        key = COMPOSITE_KEYS[collection](data)
        if all((data.get(f) not in (None, '')) for f in
               ('opm_evento_id', 'matricula', 'escala_data')
               if collection == 'escalas') or \
           all((data.get(f) not in (None, '')) for f in
               ('data_ref', 'grupo', 'metrica')
               if collection == 'ocorrencia_eventos'):
            return str(key) if key else None
        return str(key) if key else None
    field = NATURAL_KEYS.get(collection)
    if not field:
        return None
    value = str(data.get(field) or '').strip()
    return value or None


class MemoryStore:
    """In-memory fake for --self-test (no Firebase involved)."""

    def __init__(self, docs):
        self.docs = {c: dict(d) for c, d in docs.items()}
        self.ops_log = []

    def count(self, collection):
        return len(self.docs.get(collection, {}))

    def all(self, collection, scan_limit=None):
        out = dict(self.docs.get(collection, {}))
        if scan_limit is not None:
            return {k: out[k] for k in list(out)[:scan_limit]}
        return out

    def batch(self, collection, ops):
        for op, doc_id, *rest in ops:
            if op == 'set':
                _, doc_id, data, merge = op, doc_id, rest[0], rest[1]
                target = self.docs.setdefault(collection, {})
                if merge and doc_id in target:
                    merged = dict(data)
                    merged.update(target[doc_id])
                    target[doc_id] = merged
                else:
                    target[doc_id] = dict(data)
            elif op == 'del':
                self.docs.get(collection, {}).pop(doc_id, None)
            self.ops_log.append((collection, op, doc_id))


class FirestoreStore:
    """Real store over the Firebase Admin SDK."""

    def count(self, collection):
        ref = get_fs().collection(collection)
        try:
            return int(ref.count().get()[0][0].value)
        except Exception:
            return len(list(ref.stream()))

    def all(self, collection, scan_limit=None):
        stream = get_fs().collection(collection)
        if scan_limit is not None:
            stream = stream.limit(scan_limit)
        return {s.id: dict(s.to_dict() or {}) for s in stream.stream()}

    def batch(self, collection, ops):
        fs = get_fs()
        batch = fs.batch()
        ops_count = 0
        for op in ops:
            ref = fs.collection(collection).document(op[1])
            if op[0] == 'set':
                batch.set(ref, _safe(op[2]), merge=op[3])
            else:
                batch.delete(ref)
            ops_count += 1
            if ops_count >= 400:
                batch.commit()
                batch = fs.batch()
                ops_count = 0
        if ops_count:
            batch.commit()


def canonicalize_collection(store, collection, limit, resume, dry_run, log,
                            scan_limit=None):
    """Move legacy docs to canonical ids. Returns (stats, done_for_now)."""
    natural_field = NATURAL_KEYS.get(collection)
    composite = collection in COMPOSITE_KEYS
    total = store.count(collection)
    if total == 0 and not composite:
        return {'collection': collection, 'total': 0, 'legacy': 0,
                'created': 0, 'merged': 0, 'deleted': 0, 'sem_chave': 0,
                'pulados': 0}, False

    log(f"[{collection}] total={total} (chave="
        + (natural_field or 'composta') + ")")

    all_docs = store.all(collection, scan_limit=scan_limit)
    now_ids = set(all_docs)
    legacy = []
    sem_chave = 0
    for doc_id, data in all_docs.items():
        cid = canonical_id_for(collection, data)
        if not cid:
            sem_chave += 1
            continue
        if doc_id == cid:
            continue
        legacy.append((doc_id, cid))

    log(f"   canonicos={total - len(legacy) - sem_chave} "
        f"legados={len(legacy)} sem_chave={sem_chave}")

    ops = []
    created = merged = deleted = pulados = 0
    processed_total = 0
    done_for_now = False
    added = set()
    resume_col = resume.setdefault(str(collection), [])
    resume_seen = set(resume_col)
    for doc_id, cid in legacy:
        if processed_total >= limit:
            done_for_now = True
            break
        if cid in resume_seen:
            pulados += 1
            continue
        existed = cid in now_ids or cid in added
        if dry_run:
            log(f"   [PLAN] {doc_id} -> {cid} "
                f"({'mescla' if existed else 'cria'})")
            processed_total += 1
            if existed:
                merged += 1
            else:
                created += 1
            continue
        if existed:
            target = dict(all_docs.get(cid, {}))
            merged_data = dict(all_docs.get(doc_id, {}))
            merged_data.update({k: v for k, v in target.items()})
            ops.append(('set', cid, merged_data, True))
            merged += 1
        else:
            ops.append(('set', cid, dict(all_docs.get(doc_id, {})), True))
            created += 1
            added.add(cid)
        ops.append(('del', doc_id, None, None))
        deleted += 1
        resume_col.append(cid)
        resume_seen.add(cid)
        processed_total += 1

    stats = {'collection': collection, 'total': total, 'legacy': len(legacy),
             'created': created, 'merged': merged, 'deleted': deleted,
             'sem_chave': sem_chave, 'pulados': pulados}
    if dry_run:
        log(f"   [DRY-RUN] plano: +{created + merged} cria/mescla, "
            f"-{deleted} delecoes")
    elif ops:
        store.batch(collection, ops)
    return stats, done_for_now


def run(store, args):
    resume = {}
    state_path = args.resume_file
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            resume = json.load(f)

    collections = ([args.collection] if args.collection and args.collection != 'all'
                   else COLLECTION_ORDER)

    grand = {'created': 0, 'merged': 0, 'deleted': 0}
    for collection in collections:
        stats, done = canonicalize_collection(
            store, collection, args.limit, resume, args.dry_run,
            lambda m: print(m), scan_limit=args.scan_limit)
        for k in ('created', 'merged', 'deleted'):
            grand[k] += stats[k]
        if not args.dry_run:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump({c: sorted(v) for c, v in resume.items()}, f,
                          ensure_ascii=False, indent=1)
        if done:
            print(f"[{collection}] atingiu --limit={args.limit}; "
                  f"re-execute para continuar (resume em {state_path})")
            break
        time.sleep(0.3)

    writes = 2 * (grand['created'] + grand['merged'])
    print("\n=== RESUMO ===")
    print(f"  criados={grand['created']} mesclados={grand['merged']} "
          f"deletados={grand['deleted']}")
    if writes:
        print(f"  escritas estimadas={writes} "
              f"(cota diaria ~20k => ~{math.ceil(writes / 20000)} dia(s) de cota)")
    else:
        print("  (sem escrita; use --dry-run como plano)")


def self_test():
    docs = {
        'cargos': {
            'tbCargo_0': {'cargo_id': '03330', 'posto_grad': 'SD PM'},
            'tbCargo_1': {'cargo_id': '03331', 'posto_grad': 'CB PM'},
            '03332': {'cargo_id': '03332'},  # already canonical
        },
        'efetivopm': {
            'tbEfetivoPM_5': {'matricula': '30527478', 'nome': 'A',
                              'telefone': '111'},
            '30527478': {'matricula': '30527478', 'nome': 'B'},  # target exists
            'tbEfetivoPM_6': {'matricula': '99999999', 'nome': 'C'},
            'tbSemChave': {'nome': 'D'},  # no matricula -> skip
        },
        'ocorrencia_eventos': {
            'tbOcorrenciaEvento_0': {'data_ref': '2026-01-01', 'grupo': 'R',
                                     'metrica': 'OCOR', 'valor': 3},
        },
        'escalas': {},
    }
    store = MemoryStore(docs)
    state = {'ocorrencia_eventos': []}
    for col in COLLECTION_ORDER:
        canonicalize_collection(store, col, limit=10, resume=state,
                                dry_run=False, log=print)
        json.dumps(state)
    ef = store.docs['efetivopm']
    cargos = store.docs['cargos']
    oe = store.docs.get('ocorrencia_eventos', {})
    assert 'tbEfetivoPM_5' not in ef and 'tbEfetivoPM_6' not in ef, ef
    assert set(ef) == {'30527478', '99999999', 'tbSemChave'}, set(ef)
    # merged: legacy nome A gets overridden by canonical B, telefone preserved
    assert ef['30527478']['nome'] == 'B' and ef['30527478'].get('telefone') == '111'
    assert 'tbCargo_0' not in cargos and '03330' in cargos
    assert 'TB' not in {'03332'} and '03332' in cargos
    assert 'tbSemChave' in ef, 'doc sem chave deve permanecer intacto'
    expected = f"2026-01-01_R_OCOR"
    assert 'tbOcorrenciaEvento_0' not in oe and expected in oe, oe
    assert state['efetivopm'] == ['30527478', '99999999']
    print("\nSELF-TEST PASSED")


def main():
    parser = argparse.ArgumentParser(
        description="Canonicalize legacy tb*_N Firestore ids to natural keys")
    parser.add_argument('--collection', default='all',
                        help="collection name or 'all'")
    parser.add_argument('--limit', type=int, default=5000,
                        help="max legacy docs processed per run (writes ~2x)")
    parser.add_argument('--scan-limit', type=int, default=None,
                        help="cap the collection scan (fewer reads; partial plan)")
    parser.add_argument('--dry-run', action='store_true',
                        help="print the plan, write nothing")
    parser.add_argument('--resume-file', default=DEFAULT_RESUME,
                        help="path to resume state json")
    parser.add_argument('--service-account', default=None,
                        help="firebase service account json (default env/file)")
    parser.add_argument('--self-test', action='store_true',
                        help="run in-memory correctness test, no Firebase")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if args.service_account:
        os.environ['FIREBASE_SERVICE_ACCOUNT'] = args.service_account
    try:
        from app.firebase_db import init_firebase
        init_firebase()
    except Exception as exc:
        sys.exit(f"Falha ao inicializar Firebase: {exc}")

    if args.dry_run and args.limit:
        print(f"WARNING: dry-run vai LER as colecoes inteiras "
              f"(~30.5k docs em efetivopm ~= 30.5k leituras).")
    run(FirestoreStore(), args)


if __name__ == '__main__':
    main()