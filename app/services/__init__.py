from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import (
    Usuario, EfetivoPM, Cargo, OPM, Evento, OpmEvento, Escala,
    TabelaValores, EscalaP2, EscalaP2Meta, EscalaP2Legenda,
    Ocorrencia, Viatura, Municipio, EscalaSalva, EscalaSalvaItem, EscalaSalvaMeta
)
from app.repository import (
    usuario_repo, efetivo_repo, evento_repo, escala_repo,
    tabela_valores_repo, ocorrencia_repo, escala_salva_repo,
    viatura_repo, municipio_repo
)
from werkzeug.security import generate_password_hash
import json
import os


class BaseService:
    def __init__(self, repository):
        self.repo = repository
    
    def get(self, id):
        return self.repo.get_by_id(id)
    
    def get_all(self, page=1, per_page=20, **filters):
        return self.repo.get_all(page=page, per_page=per_page, **filters)
    
    def create(self, **kwargs):
        obj = self.repo.create(**kwargs)
        db.session.commit()
        return obj
    
    def update(self, id, **kwargs):
        obj = self.repo.update(id, **kwargs)
        if obj:
            db.session.commit()
        return obj
    
    def delete(self, id):
        result = self.repo.delete(id)
        if result:
            db.session.commit()
        return result


class UsuarioService(BaseService):
    def __init__(self):
        super().__init__(usuario_repo)
    
    def autenticar(self, matricula: str, senha: str) -> Optional[Usuario]:
        usuario = usuario_repo.get_by_matricula(matricula)
        if usuario and usuario.check_senha(senha) and usuario.ativo:
            usuario.ultimo_login = datetime.utcnow()
            db.session.commit()
            return usuario
        return None
    
    def criar_usuario(self, matricula: str, nome: str, senha: str, tipo: str = 'USER') -> Usuario:
        if usuario_repo.get_by_matricula(matricula):
            raise ValueError('Matrícula já cadastrada')
        usuario = Usuario(matricula=matricula, nome=nome, tipo=tipo)
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
        return usuario
    
    def alterar_senha(self, usuario_id: int, senha_atual: str, nova_senha: str) -> bool:
        usuario = self.get(usuario_id)
        if usuario and usuario.check_senha(senha_atual):
            usuario.set_senha(nova_senha)
            db.session.commit()
            return True
        return False
    
    def resetar_senha(self, matricula: str, nova_senha: str) -> bool:
        usuario = usuario_repo.get_by_matricula(matricula)
        if usuario:
            usuario.set_senha(nova_senha)
            db.session.commit()
            return True
        return False


class EfetivoService(BaseService):
    def __init__(self):
        super().__init__(efetivo_repo)
    
    def buscar_por_matricula_ou_nome(self, termo: str) -> List[EfetivoPM]:
        return efetivo_repo.search(termo).items
    
    def importar_csv(self, filepath: str) -> Dict[str, int]:
        import csv
        stats = {'criados': 0, 'atualizados': 0, 'erros': 0}
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    matricula = row.get('Matricula', '').strip()
                    if not matricula:
                        stats['erros'] += 1
                        continue
                    efetivo = efetivo_repo.get_by_matricula(matricula)
                    if efetivo:
                        for key, value in row.items():
                            attr = key.lower().replace(' ', '_')
                            if hasattr(efetivo, attr):
                                setattr(efetivo, attr, value)
                        stats['atualizados'] += 1
                    else:
                        efetivo = EfetivoPM(**{k.lower().replace(' ', '_'): v for k, v in row.items()})
                        db.session.add(efetivo)
                        stats['criados'] += 1
                except Exception as e:
                    stats['erros'] += 1
        db.session.commit()
        return stats


class EventoService(BaseService):
    def __init__(self):
        super().__init__(evento_repo)
    
    def criar_com_opms(self, dados: Dict, opm_ids: List[str]) -> Evento:
        evento = Evento(
            evento_desc=dados['evento_desc'],
            evento_dta_inicio=dados.get('evento_dta_inicio'),
            evento_dta_fim=dados.get('evento_dta_fim'),
            campo1=dados.get('campo1'),
            tipo_pagamento=dados.get('tipo_pagamento', 'HE')
        )
        db.session.add(evento)
        db.session.flush()
        
        for opm_id in opm_ids:
            opm_evento = OpmEvento(evento_id=evento.evento_id, opm_id=opm_id)
            db.session.add(opm_evento)
        
        db.session.commit()
        return evento
    
    def adicionar_opm(self, evento_id: int, opm_id: str) -> OpmEvento:
        opm_evento = OpmEvento(evento_id=evento_id, opm_id=opm_id)
        db.session.add(opm_evento)
        db.session.commit()
        return opm_evento
    
    def remover_opm(self, evento_id: int, opm_id: str) -> bool:
        opm_evento = db.session.execute(
            db.select(OpmEvento).where(
                and_(OpmEvento.evento_id == evento_id, OpmEvento.opm_id == opm_id)
            )
        ).scalar_one_or_none()
        if opm_evento:
            db.session.delete(opm_evento)
            db.session.commit()
            return True
        return False


class EscalaService(BaseService):
    def __init__(self):
        super().__init__(escala_repo)
    
    def calcular_ch(self, hora_inicio: str, hora_fim: str) -> tuple:
        """Calcula carga horária diurna e noturna."""
        if not hora_inicio or not hora_fim:
            return 0, 0
        
        try:
            hi = datetime.strptime(hora_inicio, '%H:%M')
            hf = datetime.strptime(hora_fim, '%H:%M')
        except ValueError:
            return 0, 0
        
        if hf <= hi:
            hf += timedelta(days=1)
        
        dia_inicio = hi.replace(hour=5, minute=0)
        dia_fim = hi.replace(hour=22, minute=0)
        noite_inicio = hi.replace(hour=22, minute=0)
        noite_fim = hi.replace(hour=5, minute=0) + timedelta(days=1)
        
        ch_diurna = 0
        ch_noturna = 0
        
        atual = hi
        while atual < hf:
            prox = min(atual + timedelta(hours=1), hf)
            hora_atual = atual.hour + atual.minute / 60
            
            if 5 <= hora_atual < 22:
                ch_diurna += (prox - atual).total_seconds() / 3600
            else:
                ch_noturna += (prox - atual).total_seconds() / 3600
            
            atual = prox
        
        return round(ch_diurna, 2), round(ch_noturna, 2)
    
    def salvar_escala(self, opm_evento_id: int, matricula: str, data: str, 
                      hora_inicio: str, hora_fim: str, tipo_pagamento: str = 'HE') -> Escala:
        ch_diurna, ch_noturna = self.calcular_ch(hora_inicio, hora_fim)
        
        escala = db.session.execute(
            db.select(Escala).where(
                and_(
                    Escala.opm_evento_id == opm_evento_id,
                    Escala.matricula == matricula,
                    Escala.escala_data == data
                )
            )
        ).scalar_one_or_none()
        
        if escala:
            escala.escala_ch_diurna = ch_diurna
            escala.escala_ch_noturna = ch_noturna
            escala.hora_inicio = hora_inicio
            escala.hora_fim = hora_fim
            escala.tipo_pagamento = tipo_pagamento
        else:
            escala = Escala(
                opm_evento_id=opm_evento_id,
                matricula=matricula,
                escala_data=data,
                escala_ch_diurna=ch_diurna,
                escala_ch_noturna=ch_noturna,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim,
                tipo_pagamento=tipo_pagamento
            )
            db.session.add(escala)
        
        db.session.commit()
        return escala
    
    def get_relatorio_horas(self, evento_id: int, tipo_pagamento: str = None) -> List[Dict]:
        return escala_repo.get_horas_por_militar(evento_id, tipo_pagamento)
    
    def exportar_csv(self, evento_id: int, tipo_pagamento: str = None) -> str:
        import csv
        import io
        
        dados = self.get_relatorio_horas(evento_id, tipo_pagamento)
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Matrícula', 'Nome', 'Posto/Grad', 'CH Diurna', 'CH Noturna', 'Total Dias', 'Tipo Pagamento'])
        
        for row in dados:
            total = (row['ch_diurna'] or 0) + (row['ch_noturna'] or 0)
            writer.writerow([
                row['matricula'],
                row['nome'],
                row['cargo'],
                row['ch_diurna'],
                row['ch_noturna'],
                row['dias'],
                tipo_pagamento or 'HE/VD/SO'
            ])
        
        return output.getvalue()


class TabelaValoresService(BaseService):
    def __init__(self):
        super().__init__(tabela_valores_repo)
    
    def get_valor(self, posto_grad: str, tipo_pagamento: str, noturno: bool = False) -> float:
        valor = tabela_valores_repo.get_by_posto(posto_grad)
        if not valor:
            return 0.0
        
        if tipo_pagamento == 'HE':
            return valor.ad_he_noturna if noturno else valor.he_diurna
        elif tipo_pagamento == 'VD':
            return valor.vd_noturno if noturno else valor.vd_diurno
        return 0.0
    
    def calcular_valor_militar(self, militar: EfetivoPM, ch_diurna: float, ch_noturna: float, tipo_pagamento: str) -> float:
        posto = militar.posto_grad
        if not posto:
            return 0.0
        
        valor_diurno = self.get_valor(posto, tipo_pagamento, False)
        valor_noturno = self.get_valor(posto, tipo_pagamento, True)
        
        return round((ch_diurna * valor_diurno) + (ch_noturna * valor_noturno), 2)


class OcorrenciaService(BaseService):
    def __init__(self):
        super().__init__(ocorrencia_repo)
    
    def criar_com_coordenadas(self, dados: Dict) -> Ocorrencia:
        ocorrencia = Ocorrencia(**dados)
        db.session.add(ocorrencia)
        db.session.commit()
        return ocorrencia
    
    def get_estatisticas(self, data_inicio: str = None, data_fim: str = None) -> Dict:
        query = db.select(Ocorrencia)
        if data_inicio:
            query = query.where(Ocorrencia.data_hora >= data_inicio)
        if data_fim:
            query = query.where(Ocorrencia.data_hora <= data_fim)
        
        ocorrencias = db.session.execute(query).scalars().all()
        
        stats = {
            'total': len(ocorrencias),
            'por_tipo': {},
            'por_cidade': {},
            'por_mes': {}
        }
        
        for oc in ocorrencias:
            stats['por_tipo'][oc.tipo] = stats['por_tipo'].get(oc.tipo, 0) + 1
            if oc.cidade:
                stats['por_cidade'][oc.cidade] = stats['por_cidade'].get(oc.cidade, 0) + 1
            try:
                mes = oc.data_hora[:7]
                stats['por_mes'][mes] = stats['por_mes'].get(mes, 0) + 1
            except:
                pass
        
        return stats


class EscalaSalvaService(BaseService):
    def __init__(self):
        super().__init__(escala_salva_repo)
    
    def salvar_escala_atual(self, nome: str, mes: int, ano: int, 
                            itens: List[Dict], meta: Dict = None) -> EscalaSalva:
        escala_salva = EscalaSalva(nome=nome, mes=mes, ano=ano)
        db.session.add(escala_salva)
        db.session.flush()
        
        for item in itens:
            item_obj = EscalaSalvaItem(
                escala_salva_id=escala_salva.id,
                **item
            )
            db.session.add(item_obj)
        
        if meta:
            meta_obj = EscalaSalvaMeta(escala_salva_id=escala_salva.id, **meta)
            db.session.add(meta_obj)
        
        db.session.commit()
        return escala_salva
    
    def carregar_escala(self, escala_id: int) -> Dict:
        escala = self.get(escala_id)
        if not escala:
            return {}
        
        itens = [item.to_dict() for item in escala.itens]
        meta = escala.meta.to_dict() if escala.meta else {}
        
        return {
            'escala': escala.to_dict(),
            'itens': itens,
            'meta': meta
        }
    
    def ativar_escala(self, escala_id: int) -> bool:
        return escala_salva_repo.set_ativa(escala_id)


class BackupService:
    def __init__(self, backup_dir: str = None):
        self.backup_dir = backup_dir or os.environ.get('BACKUP_DIR', '/app/backups')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def backup_postgresql(self, database_url: str) -> str:
        import subprocess
        from urllib.parse import urlparse
        
        parsed = urlparse(database_url)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{parsed.path[1:]}_{timestamp}.sql'
        filepath = os.path.join(self.backup_dir, filename)
        
        cmd = [
            'pg_dump',
            '-h', parsed.hostname or 'localhost',
            '-p', str(parsed.port or 5432),
            '-U', parsed.username or 'postgres',
            '-d', parsed.path[1:],
            '-f', filepath,
            '--no-owner', '--no-privileges'
        ]
        
        env = os.environ.copy()
        if parsed.password:
            env['PGPASSWORD'] = parsed.password
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f'Backup failed: {result.stderr}')
        
        return filepath
    
    def restore_postgresql(self, database_url: str, backup_file: str) -> bool:
        import subprocess
        from urllib.parse import urlparse
        
        parsed = urlparse(database_url)
        
        cmd = [
            'psql',
            '-h', parsed.hostname or 'localhost',
            '-p', str(parsed.port or 5432),
            '-U', parsed.username or 'postgres',
            '-d', parsed.path[1:],
            '-f', backup_file
        ]
        
        env = os.environ.copy()
        if parsed.password:
            env['PGPASSWORD'] = parsed.password
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        return result.returncode == 0
    
    def list_backups(self) -> List[Dict]:
        backups = []
        for f in os.listdir(self.backup_dir):
            if f.endswith('.sql'):
                path = os.path.join(self.backup_dir, f)
                stat = os.stat(path)
                backups.append({
                    'filename': f,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def cleanup_old_backups(self, keep: int = 30):
        backups = self.list_backups()
        for backup in backups[keep:]:
            os.remove(os.path.join(self.backup_dir, backup['filename']))


class UploadService:
    ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'csv'}
    MAX_FILE_SIZE = 16 * 1024 * 1024
    
    def __init__(self, upload_folder: str = None):
        self.upload_folder = upload_folder or os.environ.get('UPLOAD_FOLDER', '/app/uploads')
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def allowed_file(self, filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def save_file(self, file, subfolder: str = '') -> str:
        from werkzeug.utils import secure_filename
        import uuid
        
        if not self.allowed_file(file.filename):
            raise ValueError('Tipo de arquivo não permitido')
        
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        folder = os.path.join(self.upload_folder, subfolder)
        os.makedirs(folder, exist_ok=True)
        
        filepath = os.path.join(folder, unique_name)
        file.save(filepath)
        
        return filepath
    
    def delete_file(self, filepath: str) -> bool:
        try:
            os.remove(filepath)
            return True
        except:
            return False


# Service instances
usuario_service = UsuarioService()
efetivo_service = EfetivoService()
evento_service = EventoService()
escala_service = EscalaService()
tabela_valores_service = TabelaValoresService()
ocorrencia_service = OcorrenciaService()
escala_salva_service = EscalaSalvaService()
backup_service = BackupService()
upload_service = UploadService()