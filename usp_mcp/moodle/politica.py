"""Allowlist e bloqueio permanente (Invariante 2, §2.2).

A superfície é allowlist, nunca denylist: o default é negar, e uma função só
passa por igualdade exata de nome com `ALLOWLIST`. Isso importa porque quem
escolhe qual função chamar é um modelo interpretando linguagem ambígua — o
custo de errar pro lado permissivo (um sweep, uma escrita indevida) é maior
que o custo de negar uma função legítima que ainda não entrou na lista.

`BLOQUEIO_PERMANENTE` é uma segunda camada, independente da allowlist: nomes
que nunca devem ser chamados por este projeto, mesmo com `permitir_escrita`
ligada (§2.2 — "sem flag que libere"). Ela existe porque a allowlist já nega
essas funções por omissão; o bloqueio permanente documenta *por quê*, e
garante que um erro futuro na allowlist (uma função entrando nela por engano)
ainda não libere um destes nomes.
"""
from __future__ import annotations

from dataclasses import dataclass

# Cinco funções, todas de leitura. Crescer isso é decisão de §9, não
# conveniência — a passagem de 1 para 4 está registrada lá (31/08), e as três
# então novas existem porque `material` precisa traduzir sigla em `courseid`:
# site_info dá o userid a partir do token, users_courses dá a lista, e
# get_contents é a resposta.
#
# A quinta entrou em 12/09/2026, e a medição que a justifica está no §9: os 4
# módulos `assign` de PTC3314 chegam em `core_course_get_contents` com
# `contents` VAZIO, e o `description` deles não tem link nenhum. O enunciado do
# EC-1 — um PDF de 218 kB — só existe em `mod_assign_get_assignments`, como
# `introattachments`. Sem ela, `material` lista 53 itens e jura que é o acervo
# inteiro, que é o falso "não tem nada" do Invariante 7.
#
# Note a vizinhança de nome: `mod_assign_save_submission`,
# `mod_assign_submit_for_grading`, `mod_assign_start_submission` e
# `mod_assign_remove_submission` seguem no bloqueio permanente do §2.2. É
# igualdade exata de nome que libera, nunca prefixo — por isso a proximidade
# não as arrasta junto.
ALLOWLIST: frozenset[str] = frozenset(
    {
        "core_calendar_get_action_events_by_timesort",
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "core_course_get_contents",
        "mod_assign_get_assignments",
    }
)

# §2.2 do SPEC1, na íntegra — cada nome tem um motivo escrito lá.
BLOQUEIO_PERMANENTE: frozenset[str] = frozenset(
    {
        # o bypass: anula qualquer filtro por nome de função
        "tool_mobile_call_external_functions",
        # queimam tentativa de prova real
        "mod_quiz_start_attempt",
        "mod_quiz_save_attempt",
        "mod_quiz_process_attempt",
        # mintam ou vazam credencial
        "tool_mobile_get_autologin_key",
        "tool_mobile_get_tokens_for_qr_login",
        "tiny_premium_get_api_key",
        "mod_lti_get_tool_launch_data",
        # entregam em nome do usuário
        "mod_assign_save_submission",
        "mod_assign_submit_for_grading",
        "mod_assign_start_submission",
        "mod_assign_remove_submission",
        # mesmo raciocínio das tentativas de quiz
        "mod_lesson_launch_attempt",
        "mod_lesson_process_page",
        "mod_lesson_finish_attempt",
        "mod_workshop_add_submission",
        "mod_workshop_update_submission",
        "mod_workshop_delete_submission",
        # falam com terceiros em nome do usuário — note os DOIS caminhos de mensagem
        "core_message_send_instant_messages",
        "core_message_send_messages_to_conversation",
        "mod_forum_add_discussion",
        "mod_forum_add_discussion_post",
        "mod_forum_update_discussion_post",
        "mod_forum_delete_post",
        "enrol_self_enrol_user",
    }
)


@dataclass(frozen=True)
class Decisao:
    """Resultado de `decidir`. `motivo` existe para o Invariante 6: erro legível
    vence silêncio, e um `False` pelado não diz o que fazer com o resultado."""

    permitida: bool
    motivo: str


def decidir(funcao: str, permitir_escrita: bool = False) -> Decisao:
    """Decide se `funcao` pode ser chamada.

    `permitir_escrita` é a flag do Invariante 1 (USP_MCP_ALLOW_WRITES) — ela
    não é usada aqui para *liberar* nada: o bloqueio permanente ignora essa
    flag por definição (§2.2), e a allowlist atual não contém função de
    escrita para ela liberar. O parâmetro existe para deixar essa ausência de
    efeito explícita no call site, em vez de a política simplesmente não
    aceitar a flag.
    """
    if funcao in BLOQUEIO_PERMANENTE:
        return Decisao(
            permitida=False,
            motivo=(
                f"{funcao} está no bloqueio permanente do §2.2 — negada mesmo "
                "com permitir_escrita=True, pois não há flag que libere."
            ),
        )

    if funcao in ALLOWLIST:
        return Decisao(permitida=True, motivo=f"{funcao} está na allowlist.")

    return Decisao(
        permitida=False,
        motivo=(
            f"{funcao} não está na allowlist — default é negar (Invariante 2, "
            "allowlist e não denylist)."
        ),
    )
