from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from app import db
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Query


class BaseRepository(ABC):
    def __init__(self, model):
        self.model = model
    
    def get_by_id(self, id: Any) -> Optional[Any]:
        return db.session.get(self.model, id)
    
    def get_all(self, page: int = 1, per_page: int = 20, **filters) -> Any:
        query = self._apply_filters(db.select(self.model), filters)
        return db.paginate(query, page=page, per_page=per_page, error_out=False)
    
    def get_all_list(self, **filters) -> List[Any]:
        query = self._apply_filters(db.select(self.model), filters)
        return db.session.execute(query).scalars().all()
    
    def create(self, **kwargs) -> Any:
        obj = self.model(**kwargs)
        db.session.add(obj)
        db.session.flush()
        return obj
    
    def update(self, id: Any, **kwargs) -> Optional[Any]:
        obj = self.get_by_id(id)
        if obj:
            for key, value in kwargs.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            db.session.flush()
        return obj
    
    def delete(self, id: Any) -> bool:
        obj = self.get_by_id(id)
        if obj:
            db.session.delete(obj)
            db.session.flush()
            return True
        return False
    
    def _apply_filters(self, query: Query, filters: Dict) -> Query:
        for key, value in filters.items():
            if value is None or value == '':
                continue
            if hasattr(self.model, key):
                column = getattr(self.model, key)
                if isinstance(value, str) and '%' in value:
                    query = query.where(column.ilike(value))
                elif isinstance(value, (list, tuple)):
                    query = query.where(column.in_(value))
                else:
                    query = query.where(column == value)
        return query


class UsuarioRepository(BaseRepository):
    def __init__(self):
        from app.models import Usuario
        super().__init__(Usuario)
    
    def get_by_matricula(self, matricula: str) -> Optional[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.matricula == matricula)
        ).scalar_one_or_none()
    
    def get_by_email(self, email: str) -> Optional[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.email == email)
        ).scalar_one_or_none()
    
    def search(self, term: str, page: int = 1, per_page: int = 20) -> Any:
        query = db.select(self.model).where(
            or_(
                self.model.matricula.ilike(f'%{term}%'),
                self.model.nome.ilike(f'%{term}%')
            )
        )
        return db.paginate(query, page=page, per_page=per_page, error_out=False)


class EfetivoPMRepository(BaseRepository):
    def __init__(self):
        from app.models import EfetivoPM
        super().__init__(EfetivoPM)
    
    def get_by_matricula(self, matricula: str) -> Optional[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.matricula == matricula)
        ).scalar_one_or_none()
    
    def search(self, term: str, page: int = 1, per_page: int = 20) -> Any:
        query = db.select(self.model).where(
            or_(
                self.model.matricula.ilike(f'%{term}%'),
                self.model.nome.ilike(f'%{term}%')
            )
        )
        return db.paginate(query, page=page, per_page=per_page, error_out=False)
    
    def get_by_opm(self, opm_id: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.opm_id == opm_id)
        ).scalars().all()
    
    def get_by_cargo(self, cargo_id: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.cargo == cargo_id)
        ).scalars().all()


class EventoRepository(BaseRepository):
    def __init__(self):
        from app.models import Evento
        super().__init__(Evento)
    
    def get_with_opms(self, evento_id: int) -> Optional[Any]:
        from app.models import OpmEvento, OPM
        evento = self.get_by_id(evento_id)
        if evento:
            evento.opms = db.session.execute(
                db.select(OPM).join(OpmEvento).where(OpmEvento.evento_id == evento_id)
            ).scalars().all()
        return evento
    
    def get_by_tipo_pagamento(self, tipo: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.tipo_pagamento == tipo)
        ).scalars().all()


class EscalaRepository(BaseRepository):
    def __init__(self):
        from app.models import Escala
        super().__init__(Escala)
    
    def get_by_opm_evento(self, opm_evento_id: int) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.opm_evento_id == opm_evento_id)
        ).scalars().all()
    
    def get_by_matricula_data(self, matricula: str, data_inicio: str, data_fim: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(
                and_(
                    self.model.matricula == matricula,
                    self.model.escala_data >= data_inicio,
                    self.model.escala_data <= data_fim
                )
            )
        ).scalars().all()
    
    def get_horas_por_militar(self, evento_id: int, tipo_pagamento: str = None) -> List[Dict]:
        from app.models import OpmEvento, EfetivoPM, Cargo
        query = db.select(
            EfetivoPM.matricula,
            EfetivoPM.nome,
            EfetivoPM.cargo,
            func.sum(self.model.escala_ch_diurna).label('ch_diurna'),
            func.sum(self.model.escala_ch_noturna).label('ch_noturna'),
            func.count(self.model.escala_data).label('dias')
        ).join(
            self.model, self.model.matricula == EfetivoPM.matricula
        ).join(
            OpmEvento, self.model.opm_evento_id == OpmEvento.opm_evento_id
        ).where(
            OpmEvento.evento_id == evento_id
        )
        
        if tipo_pagamento:
            query = query.where(self.model.tipo_pagamento == tipo_pagamento)
        
        query = query.group_by(EfetivoPM.matricula, EfetivoPM.nome, EfetivoPM.cargo)
        return db.session.execute(query).mappings().all()


class TabelaValoresRepository(BaseRepository):
    def __init__(self):
        from app.models import TabelaValores
        super().__init__(TabelaValores)
    
    def get_by_posto(self, posto_grad: str) -> Optional[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.posto_grad == posto_grad)
        ).scalar_one_or_none()


class OcorrenciaRepository(BaseRepository):
    def __init__(self):
        from app.models import Ocorrencia
        super().__init__(Ocorrencia)
    
    def get_by_date_range(self, data_inicio: str, data_fim: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(
                and_(
                    self.model.data_hora >= data_inicio,
                    self.model.data_hora <= data_fim
                )
            ).order_by(self.model.data_hora.desc())
        ).scalars().all()
    
    def get_by_tipo(self, tipo: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.tipo == tipo)
        ).scalars().all()


class EscalaSalvaRepository(BaseRepository):
    def __init__(self):
        from app.models import EscalaSalva
        super().__init__(EscalaSalva)
    
    def get_ativa(self, mes: int, ano: int) -> Optional[Any]:
        return db.session.execute(
            db.select(self.model).where(
                and_(
                    self.model.mes == mes,
                    self.model.ano == ano,
                    self.model.ativa == 1
                )
            )
        ).scalar_one_or_none()
    
    def set_ativa(self, escala_id: int) -> bool:
        escala = self.get_by_id(escala_id)
        if escala:
            db.session.execute(
                db.update(self.model).where(
                    and_(
                        self.model.mes == escala.mes,
                        self.model.ano == escala.ano
                    )
                ).values(ativa=0)
            )
            escala.ativa = 1
            db.session.flush()
            return True
        return False


class ViaturaRepository(BaseRepository):
    def __init__(self):
        from app.models import Viatura
        super().__init__(Viatura)
    
    def get_by_municipio(self, municipio: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.municipio == municipio)
        ).scalars().all()
    
    def get_by_situacao(self, situacao: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.situacao == situacao)
        ).scalars().all()


class MunicipioRepository(BaseRepository):
    def __init__(self):
        from app.models import Municipio
        super().__init__(Municipio)
    
    def get_by_uf(self, uf: str) -> List[Any]:
        return db.session.execute(
            db.select(self.model).where(self.model.uf == uf)
        ).scalars().all()


# Repository instances
usuario_repo = UsuarioRepository()
efetivo_repo = EfetivoPMRepository()
evento_repo = EventoRepository()
escala_repo = EscalaRepository()
tabela_valores_repo = TabelaValoresRepository()
ocorrencia_repo = OcorrenciaRepository()
escala_salva_repo = EscalaSalvaRepository()
viatura_repo = ViaturaRepository()
municipio_repo = MunicipioRepository()