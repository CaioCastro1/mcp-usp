"""Camada 1 — Invariante 2: a superfície é allowlist, e o bloqueio é permanente.

Nenhum destes toca em rede, fixture ou SDK. São tabela de nomes contra uma
decisão. É a camada mais barata e a que protege o risco mais caro do projeto:
estas funções vão ser chamadas por um modelo interpretando linguagem ambígua.
"""
from __future__ import annotations

import pytest

from usp_mcp.moodle import politica

pytestmark = pytest.mark.politica

# §2.2 do SPEC1, na íntegra. Cada nome aqui tem um motivo escrito lá.
BLOQUEIO_PERMANENTE = [
    # o bypass: anula qualquer filtro por nome de função
    "tool_mobile_call_external_functions",
    # queimam tentativa de prova real
    "mod_quiz_start_attempt", "mod_quiz_save_attempt", "mod_quiz_process_attempt",
    # mintam ou vazam credencial
    "tool_mobile_get_autologin_key", "tool_mobile_get_tokens_for_qr_login",
    "tiny_premium_get_api_key", "mod_lti_get_tool_launch_data",
    # entregam em nome do usuário
    "mod_assign_save_submission", "mod_assign_submit_for_grading",
    "mod_assign_start_submission", "mod_assign_remove_submission",
    # mesmo raciocínio das tentativas de quiz
    "mod_lesson_launch_attempt", "mod_lesson_process_page", "mod_lesson_finish_attempt",
    "mod_workshop_add_submission", "mod_workshop_update_submission",
    "mod_workshop_delete_submission",
    # falam com terceiros em nome do usuário — note os DOIS caminhos de mensagem
    "core_message_send_instant_messages",
    "core_message_send_messages_to_conversation",
    "mod_forum_add_discussion", "mod_forum_add_discussion_post",
    "mod_forum_update_discussion_post", "mod_forum_delete_post",
    "enrol_self_enrol_user",
]


@pytest.mark.parametrize("funcao", BLOQUEIO_PERMANENTE)
def test_bloqueio_permanente_e_negado(funcao):
    """T1 — cada nome do §2.2 é negado."""
    assert not politica.decidir(funcao).permitida


@pytest.mark.parametrize("funcao", BLOQUEIO_PERMANENTE)
def test_bloqueio_permanente_ignora_a_flag_de_escrita(funcao):
    """T2 — USP_MCP_ALLOW_WRITES=1 NÃO libera o §2.2.

    A flag do Invariante 1 governa escrita comum. A lista de bloqueio permanente
    é outra coisa: "sem flag que libere", nas palavras do §2.2.
    """
    assert not politica.decidir(funcao, permitir_escrita=True).permitida


def test_o_bypass_e_negado_mesmo_que_tudo_mais_falhe():
    """T3 — se um só nome tiver de estar bloqueado, é este.

    `service_function_exists` é o único portão dela no fonte do Moodle 5.0, e o
    serviço deste token contém as 447 funções. Qualquer função passa por dentro.
    """
    d = politica.decidir("tool_mobile_call_external_functions")
    assert not d.permitida
    assert "tool_mobile_call_external_functions" not in politica.ALLOWLIST


def test_funcao_desconhecida_e_negada_por_omissao():
    """T4 — allowlist, não denylist: o default é negar."""
    assert not politica.decidir("core_course_get_courses").permitida
    assert not politica.decidir("funcao_que_nao_existe_no_moodle").permitida


def test_funcao_que_se_declara_read_e_grava_e_negada():
    """T5 — o campo `type` do Moodle não é fronteira de segurança.

    `core_course_set_favourite_courses` se declara `read` e grava. Um filtro que
    confie em `type` deixa ela passar.
    """
    assert not politica.decidir("core_course_set_favourite_courses").permitida


def test_nao_ha_regra_de_prefixo():
    """T6 — glob não é blindagem.

    `mod_forum_add_discussion*` casa com add_discussion e add_discussion_post, e
    deixa passar update_discussion_post e delete_post. Um nome só é permitido por
    igualdade exata, nunca por prefixo.
    """
    for quase in (
        "mod_forum_add_discussion_post",
        "mod_forum_update_discussion_post",
        "mod_forum_delete_post",
        "core_calendar_get_action_events_by_timesort_extra",
        "core_calendar_get_action_events_by_course",
    ):
        assert not politica.decidir(quase).permitida, quase


def test_superficie_da_fatia_e_exatamente_uma_funcao():
    """T7 — trava crescimento acidental da superfície.

    A fatia vertical é `o_que_vence`. Se um dia a allowlist crescer, que seja por
    decisão registrada no §9, não por alguém precisando de "só mais uma".
    """
    assert politica.ALLOWLIST == frozenset(
        {"core_calendar_get_action_events_by_timesort"}
    )


def test_a_permitida_e_permitida():
    """T8 — a política não é um `return False` disfarçado."""
    assert politica.decidir("core_calendar_get_action_events_by_timesort").permitida


def test_negacao_produz_motivo_legivel():
    """T9 — Invariante 6 aplicado à própria política.

    Negar em silêncio, ou com `False` pelado, produz o erro mais difícil de
    diagnosticar que existe. O motivo nomeia a função e diz por que.
    """
    d = politica.decidir("mod_assign_submit_for_grading")
    assert not d.permitida
    assert "mod_assign_submit_for_grading" in d.motivo
    assert len(d.motivo) > 20


def test_as_duas_listas_nao_se_cruzam():
    """T10 — coerência interna: nada permitido pode estar bloqueado."""
    assert not (politica.ALLOWLIST & politica.BLOQUEIO_PERMANENTE)
