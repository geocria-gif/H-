"""Firestore data-access layer.

Replaces the former SQLAlchemy models/repository layer. Every entity is
accessed through functions that return `base.Doc` objects (attribute +
item access) so templates keep working unchanged.
"""
from . import base
from . import org
from . import escala_app
from . import ocorrencia_data
from . import usuarios

# Flatten key functions for convenience.
from .org import (
    list_cargos, get_cargo, add_cargo, update_cargo, delete_cargo,
    list_opms, get_opm, add_opm, update_opm, delete_opm, count_opms,
    get_efetivo, list_efetivos, list_all_efetivos, list_efetivos_by_opm,
    list_efetivos_by_cargo, search_efetivos, search_efetivos_json,
    add_efetivo, update_efetivo, delete_efetivo, count_efetivos, efetivo_matriculas,
    list_tabela_valores, get_tabela_valor, get_tabela_valor_by_posto,
    add_tabela_valor, update_tabela_valor, delete_tabela_valor,
    list_municipios, get_municipio, add_municipio, update_municipio, delete_municipio,
)
from .escala_app import (
    list_eventos, list_eventos_proximos, list_eventos_por_mes_ano,
    get_evento, get_evento_with_opms, add_evento, update_evento, delete_evento,
    count_eventos, next_evento_id, list_eventos_with_opms,
    list_opm_eventos, list_opm_eventos_by_evento, get_opm_evento,
    add_opm_evento, update_opm_evento, delete_opm_evento, count_opm_eventos,
    next_opm_evento_id, opm_evento_exists, list_opm_eventos_dropdown,
    list_escalas, list_escalas_by_opm_evento, get_escala, add_escala,
    update_escala, delete_escala, count_escalas_by_opm_evento, horas_por_militar,
    list_escalas_with_militar, get_escala_with_militar,
    list_p2, get_p2, add_p2, update_p2, delete_p2, count_p2, next_p2_id,
    p2_dias_dict, list_p2_funcs, list_p2_ghs, list_p2_opms,
    get_p2_meta, save_p2_meta,
    list_p2_legendas, get_p2_legenda, add_p2_legenda, update_p2_legenda,
    delete_p2_legenda, next_p2_legenda_id,
    list_escalas_salvas, list_all_escalas_salvas, list_escalas_salvas_ativas,
    get_escala_salva,
    get_escala_salva_ativa, set_escala_salva_ativa, add_escala_salva,
    update_escala_salva, delete_escala_salva, next_escala_salva_id,
)
from .ocorrencia_data import (
    list_ocorrencias, list_all_ocorrencias, list_ocorrencias_recentes,
    list_ocorrencias_por_tipo, get_ocorrencia, add_ocorrencia,
    update_ocorrencia, delete_ocorrencia, count_ocorrencias, next_ocorrencia_id,
    list_ocorrencia_eventos, list_ocorrencia_eventos_todos,
    get_ocorrencia_evento, add_ocorrencia_evento, update_ocorrencia_evento,
    delete_ocorrencia_evento, delete_ocorrencia_eventos_by_data_ref,
    list_ocorrencia_meta, get_ocorrencia_meta, add_ocorrencia_meta,
    update_ocorrencia_meta, delete_ocorrencia_meta,
    list_ocorrencia_config, get_ocorrencia_config, set_ocorrencia_config,
    delete_ocorrencia_config,
    list_viaturas, list_all_viaturas, get_viatura, add_viatura,
    update_viatura, delete_viatura, viatura_situacoes, viatura_municipios,
)
from .usuarios import (
    get_usuario, get_usuario_by_email, list_usuarios, add_usuario,
    update_usuario, delete_usuario, usuario_to_dict, auth_email,
    create_auth_user, reset_auth_password, update_auth_user,
    verify_id_token, get_user_by_uid, touch_ultimo_login,
)