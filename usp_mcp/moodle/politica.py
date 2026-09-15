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

# Onze funções, todas de leitura. Crescer isso é decisão de §9, não
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
#
# A sexta entrou em 14/09/2026, e a decisão está no §9: `ja_entreguei` responde
# "eu já entreguei isso?", e nenhuma das cinco acima sabe responder.
# `mod_assign_get_assignments` diz o que EXISTE e quando vence; o que foi feito
# só existe em `mod_assign_get_submission_status`, no campo
# `lastattempt.submission.status` — onde `draft` (rascunho salvo, não enviado) e
# `submitted` (entregue) são uma palavra de distância. Ela é de leitura pura: a
# função que ENTREGA é `mod_assign_submit_for_grading`, e continua bloqueada
# duas vezes, pela omissão da allowlist e pelo §2.2.
#
# A sétima e a oitava entraram em 14/09/2026, com `notas`, e a decisão do §9 é
# sobre serem DUAS: as duas visões de nota do e-Disciplinas não competem, se
# complementam (catálogo §3.7). `gradereport_overview_get_course_grades` dá a
# nota final de cada matrícula; `gradereport_user_get_grade_items` dá item a
# item de UM curso, com peso e máximo. Nenhuma das duas responde o que a outra
# responde, e a ferramenta escolhe UMA por invocação — nunca as duas.
#
# As duas são leitura. A família tem escrita (`gradereport_*_view_grade_report`,
# que dispara evento de log) e tem leitura de nota DE TERCEIROS
# (`gradereport_grader_get_users_in_report`): nenhuma das três entra, e os
# prefixos declarados em P5 são estreitos o bastante para não as arrastar.
#
# A nona e a décima entraram em 14/09/2026, com `avisos`, e a decisão do §9 é
# sobre a SEGUNDA delas ter o nome que tem. O comparável `loyaniu/moodle-mcp`
# chama `mod_forum_get_discussions`, que **não existe** no Moodle 5.0 da USP —
# medido em 14/09. A função é `mod_forum_get_forum_discussions`, e a diferença
# entre as duas é a diferença entre a ferramenta responder e dar erro na
# primeira pergunta real. A primeira, `mod_forum_get_forums_by_courses`, existe
# porque a segunda exige um `forumid` que nem o `courseid` nem o `cmid` são.
#
# A família `mod_forum_` é a mais perigosa da allowlist até aqui: quatorze das
# dezoito funções escrevem, e quatro delas estão no §2.2 (`add_discussion`,
# `add_discussion_post`) ou deveriam estar pelo mesmo motivo
# (`update_discussion_post` edita post público, `delete_post` apaga a discussão
# inteira quando o post é o tópico). Nenhuma começa por `mod_forum_get_`, que é
# o prefixo estreito declarado em P5 — o do plugin, `mod_forum_`, casaria com
# todas as quatorze.
#
# A décima primeira entrou em 14/09/2026, com `o_que_mudou`, e é a primeira que
# NÃO precisou de prefixo novo: `core_course_get_updates_since` casa com
# `core_course_get_`, declarado desde 31/08 por causa de `get_contents`. A
# decisão do §9 dela é outra — a janela é por DIAS e não por carimbo —, e o que
# vale registrar aqui é que a família `core_course_` tem escrita
# (`core_course_set_favourite_courses`, que o T5 usa justamente porque ela se
# declara `read` e grava, e `core_course_view_course`), e nenhuma das duas casa
# com o prefixo do verbo.
ALLOWLIST: frozenset[str] = frozenset(
    {
        "core_calendar_get_action_events_by_timesort",
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "core_course_get_contents",
        "mod_assign_get_assignments",
        "mod_assign_get_submission_status",
        "gradereport_overview_get_course_grades",
        "gradereport_user_get_grade_items",
        "mod_forum_get_forums_by_courses",
        "mod_forum_get_forum_discussions",
        "core_course_get_updates_since",
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
        # --- acrescentados em 14/09/2026, por auditoria (§9) -----------------
        # As 57 funções do site que casam com verbo de escrita foram
        # classificadas contra as categorias que este bloco já usa. Estas 15
        # caem dentro delas e estavam de fora — a allowlist as negava por
        # omissão, que é a primeira linha, mas o §2.2 é a SEGUNDA, para o dia
        # em que alguém acrescentar algo à allowlist por engano.
        #
        # respondem/entregam em nome do usuário — mesma classe de
        # `mod_assign_submit_for_grading`, em atividades que não são entrega
        "mod_choice_submit_choice_response",
        "mod_choicegroup_submit_choicegroup_response",
        "mod_feedback_process_page",
        "mod_questionnaire_submit_questionnaire_response",
        # queimam tentativa — mesmo raciocínio de `mod_lesson_launch_attempt`
        "mod_feedback_launch_feedback",
        "mod_scorm_launch_sco",
        # publicam conteúdo assinado pelo usuário, visível a terceiros
        "mod_data_add_entry",
        "mod_glossary_add_entry",
        "core_blog_add_entry",
        # falam com terceiros em nome do usuário — mesma classe dos dois
        # caminhos de mensagem e dos posts de fórum acima
        "core_comment_add_comments",
        "core_rating_add_rating",
        "core_notes_create_notes",
        "core_message_create_contact_request",
        # afirmam progresso que o usuário não fez. `mark_course_self_completed`
        # declara um curso inteiro concluído; a outra marca atividade a
        # atividade. Nenhuma das duas tem desfazer pela API.
        "core_completion_mark_course_self_completed",
        "core_completion_update_activity_completion_status_manually",
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
                f"{funcao} está no bloqueio permanente — negada mesmo com "
                "permitir_escrita=True, pois não há configuração que libere."
            ),
        )

    if funcao in ALLOWLIST:
        return Decisao(permitida=True, motivo=f"{funcao} está na allowlist.")

    return Decisao(
        permitida=False,
        motivo=(
            f"{funcao} não é uma das funções que esta ferramenta chama no Moodle "
            "(a lista é fechada; o padrão é negar)."
        ),
    )
