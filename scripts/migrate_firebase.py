"""Migrate the legacy SQLite database (hextra) into Google Cloud Firestore.

Usage:
    py -3.14 scripts/migrate_firebase.py [--sqlite PATH] [--service-account PATH] [--limit N]

- Copies every table under tb* into a Firestore collection using the project's
  natural keys as document ids where possible.
- Creates Firebase Auth users from tbUsuario (email = <matricula>@gestoper.local).
"""
import os
import sys
import time
import json
import argparse
import sqlite3
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, auth, firestore

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SQLITE = r"C:\Users\frj_c\Downloads\hextra_2026-07-13 (2).sqlite"
DEFAULT_SA = os.path.join(ROOT, "gestoper-4ba86-firebase-adminsdk-fbsvc-aa0f68e3bb.json")

COLLECTIONS = [
    # (table, collection, doc_id_fn)  doc_id_fn(row dict) -> document id
    ("tbCargo",          "cargos",           lambda r: str(r["CargoId"])),
    ("tbOPM",            "opms",             lambda r: str(r["OpmId"])),
    ("tbEfetivoPM",      "efetivopm",        lambda r: str(r["Matricula"])),
    ("tbEvento",         "eventos",          lambda r: str(r["EventoId"])),
    ("tbOpmEvento",      "opm_eventos",      lambda r: str(r["OpmEventoId"])),
    ("tbEscala",         "escalas",          lambda r: f"{r['OpmEventoId']}_{r['Matricula']}_{r['EscalaData']}"),
    ("tbTabelaValores",  "tabela_valores",   lambda r: str(r["Id"])),
    ("tbEscalaP2",       "escala_p2",        lambda r: str(r["Id"])),
    ("tbEscalaP2Meta",   "escala_p2_meta",   lambda r: str(r["Id"])),
    ("tbEscalaP2Legenda","escala_p2_legendas", lambda r: str(r["Id"])),
    ("tbOcorrencia",     "ocorrencias",      lambda r: str(r["Id"])),
    ("tbOcorrenciaEvento","ocorrencia_eventos",
        lambda r: f"{r['DataRef']}_{r['Grupo']}_{r['Metrica']}"),
    ("tbOcorrenciaMeta", "ocorrencia_meta",  lambda r: str(r["DataRef"])),
    ("tbOcorrenciaConfig","ocorrencia_config", lambda r: str(r["Chave"])),
    ("tbMunicipio",      "municipios",       lambda r: str(r["Id"])),
    ("tbViatura",        "viaturas",         lambda r: str(r["Prefixo"])),
    ("tbUsuario",        "usuarios",         lambda r: str(r["Matricula"])),
]

# Source DB column -> Firestore field (snake_case, matching the app model attributes)
FIELD_MAP = {
    "CargoId": 'cargo_id', "PostoGrad": 'posto_grad', "TipoServidor": 'tipo_servidor',
    "TipoMilitar": 'tipo_militar', "ClassifOf": 'classif_of',
    "OpmId": 'opm_id', "OpmDesc": 'opm_desc', "OpmSigla": 'opm_sigla',
    "OpmOrdem": 'opm_ordem', "OpmAtv": 'opm_atv', "OpmRegiao": 'opm_regiao',
    "OpmMunicipio": 'opm_municipio', "OpmBairro": 'opm_bairro',
    "Comandante": 'comandante', "Funcao": 'funcao',
    "Matricula": 'matricula', "Nome": 'nome', "Cargo": 'cargo', "Sit": 'sit',
    "F6": 'f6', "LcTrabDesc": 'lc_trab_desc', "CPF": 'cpf', "RG": 'rg',
    "Titulo": 'titulo', "CNH": 'cnh', "Categoria": 'categoria',
    "TipoSanguineo": 'tipo_sanguineo', "Telefone": 'telefone',
    "Admissao": 'admissao', "DataNascimento": 'data_nascimento',
    "LocalTrabalho": 'local_trabalho', "Comportamento": 'comportamento',
    "EventoId": 'evento_id', "EventoDesc": 'evento_desc',
    "EventoDtaInicio": 'evento_dta_inicio', "EventoDtaFim": 'evento_dta_fim',
    "Campo1": 'campo1', "TipoPagamento": 'tipo_pagamento',
    "OpmEventoId": 'opm_evento_id', "EscalaCHDiurna": 'escala_ch_diurna',
    "EscalaCHNoturna": 'escala_ch_noturna', "EscalaData": 'escala_data',
    "HoraInicio": 'hora_inicio', "HoraFim": 'hora_fim',
    "HEDiurna": 'he_diurna', "AdHENoturna": 'ad_he_noturna',
    "VDDiurno": 'vd_diurno', "VDNoturno": 'vd_noturno',
    "Mes": 'mes', "Ano": 'ano', "OPM": 'opm', "GH": 'gh', "Dias": 'dias',
    "IsSeparador": 'is_separador', "SeparadorTexto": 'separador_texto',
    "Ordem": 'ordem', "Local": 'local', "Responsavel": 'responsavel',
    "Emissao": 'emissao', "Nota": 'nota', "Titulo": 'titulo', "Codigo": 'codigo',
    "Descricao": 'descricao', "DataHora": 'data_hora', "Cidade": 'cidade',
    "Latitude": 'latitude', "Longitude": 'longitude', "VTR": 'vtr',
    "DadosRelevantes": 'dados_relevantes', "CreatedAt": 'created_at',
    "DataRef": 'data_ref', "Grupo": 'grupo', "Metrica": 'metrica', "Valor": 'valor',
    "OrdemGrupo": 'ordem_grupo', "OrdemMetrica": 'ordem_metrica',
    "SourceId": 'source_id', "SheetName": 'sheet_name',
    "OperationTitle": 'operation_title', "Category": 'category',
    "Subtitle": 'subtitle', "SourceType": 'source_type', "HighlightsJson": 'highlights_json',
    "Chave": 'chave', "Valor": 'valor',
    "Id": 'id', "UF": 'uf', "Regiao": 'regiao', "CodigoIBGE": 'codigo_ibge',
    "Area": 'area', "CEP": 'cep', "Populacao": 'populacao', "DistIrece": 'dist_irece',
    "Prefeito": 'prefeito', "Partido": 'partido',
    "Prefixo": 'prefixo', "Item": 'item', "Placa": 'placa', "Chassi": 'chassi',
    "Renavam": 'renavam', "Patrimonio": 'patrimonio', "CodSecretaria": 'cod_secretaria',
    "CodUnidadeGestora": 'cod_unidade_gestora', "Municipio": 'municipio',
    "Combustivel": 'combustivel', "Marca": 'marca', "Modelo": 'modelo',
    "AnoModelo": 'ano_modelo', "AnoFabricacao": 'ano_fabricacao', "Cor": 'cor',
    "Propriedade": 'propriedade', "Situacao": 'situacao', "Unidade": 'unidade',
    "Senha": 'senha', "Tipo": 'tipo', "CriadoEm": 'criado_em',
    "EscalaSalvaId": 'escala_salva_id',
}


def map_row(row):
    out = {}
    for k, v in row.items():
        f = FIELD_MAP.get(k)
        if f is None:
            continue
        if isinstance(v, bytes):
            v = v.decode('utf-8', errors='replace')
        out[f] = v
    # Never persist plaintext passwords in Firestore; the password lives only
    # in Firebase Auth (see create_auth_users).
    out.pop('senha', None)
    return out


def normalize(value):
    """Make values Firestore-safe (no NaN, convert datetime to string)."""
    if isinstance(value, float) and value != value:  # NaN
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def write_collection(db, table, collection, doc_id_fn, limit=None):
    con = sqlite3.connect(_SQLITE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    total = cur.fetchone()[0]
    print(f"[{table}] -> {collection}: {total} rows")

    col = db.collection(collection)
    # Idempotent resume: skip documents that already exist.
    existing = {s.id for s in col.get()}
    print(f"   existing docs: {len(existing)}")
    count = 0
    skipped = 0
    while True:
        cur.execute(f'SELECT * FROM {table}')
        batch = db.batch()
        ops = 0
        for row in cur.fetchall():
            doc_data = map_row(dict(row))
            doc_data = {k: normalize(v) for k, v in doc_data.items()}
            # Ensure no empty-string document ids / empty bytes
            try:
                doc_id = doc_id_fn(doc_data)
            except KeyError:
                doc_id = None
            if not doc_id:
                doc_id = f"{table}_{count}"
            if doc_id in existing:
                skipped += 1
                count += 1
                continue
            batch.set(col.document(doc_id), doc_data)
            existing.add(doc_id)
            count += 1
            ops += 1
            if count >= (limit if limit else float('inf')):
                break
            if ops >= 500:
                batch.commit()
                print(f"   +{ops} (total {count}, skipped {skipped})")
                time.sleep(0.8)
                ops = 0
                batch = db.batch()
        if ops:
            batch.commit()
            print(f"   +{ops} (total {count}, skipped {skipped})")
        break
    con.close()
    return count


def create_auth_users():
    con = sqlite3.connect(_SQLITE)
    con.row_factory = sqlite3.Row
    rows = con.execute('SELECT * FROM tbUsuario').fetchall()
    con.close()
    print("Firebase Auth users from tbUsuario:", len(rows))
    for row in rows:
        email = f"{row['Matricula']}@gestoper.local"
        try:
            auth.get_user_by_email(email)
            print("  exists:", email)
            continue
        except auth.UserNotFoundError:
            pass
        try:
            u = auth.create_user(
                email=email,
                password=str(row['Senha']),
                display_name=row['Nome'],
                disabled=False,
            )
            print("  created:", email, u.uid)
        except auth.AuthError as e:
            print("  ERROR:", email, e)


def main():
    global _SQLITE
    parser = argparse.ArgumentParser(description="Migrate SQLite -> Firestore")
    parser.add_argument('--sqlite', default=DEFAULT_SQLITE)
    parser.add_argument('--service-account', default=DEFAULT_SA)
    parser.add_argument('--limit', type=int, default=None, help="max docs per collection")
    parser.add_argument('--skip-auth', action='store_true')
    args = parser.parse_args()

    if not os.path.exists(args.sqlite):
        sys.exit(f"SQLite file not found: {args.sqlite}")
    if not os.path.exists(args.service_account):
        sys.exit(f"Service account not found: {args.service_account}")
    _SQLITE = args.sqlite

    cred = credentials.Certificate(args.service_account)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    totals = {}
    for table, collection, doc_id_fn in COLLECTIONS:
        totals[table] = write_collection(db, table, collection, doc_id_fn, args.limit)
        time.sleep(0.5)

    print("\n=== MIGRATION SUMMARY ===")
    for t, c in totals.items():
        print(f"  {t}: {c} docs")
    print("Total:", sum(totals.values()))

    if not args.skip_auth:
        try:
            create_auth_users()
        except auth.AuthError as e:
            print("Auth users NOT created (Auth API may be disabled):", e)


if __name__ == '__main__':
    main()