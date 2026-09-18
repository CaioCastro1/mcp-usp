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

`ESCRITA_CONFIRMADA` é o terceiro conjunto, e o mais novo (15/09/2026). Ele
existe porque o §2.2 foi REABERTO por decisão do dono, com a condição dele —
confirmação humana explícita —, e o desenho inteiro está em
`docs/superpowers/specs/2026-09-15-entrega-com-confirmacao-design.md`. Duas das
cinco funções que aquela lista recusava por escrito saíram dela e vieram para
cá: `mod_assign_save_submission` e `mod_assign_submit_for_grading`. As três de
questionário ficaram, e a razão é de desenho e não de conforto — para entrega de
atividade existe estado anterior legível e rascunho que se sobrescreve, então dá
para mostrar um plano fiel antes de escrever; para tentativa de questionário não
existe rascunho e `start_attempt` já é irreversível.

Um nome deste conjunto passa por DUAS condições, e nenhuma das duas é a
allowlist: a variável de ambiente `USP_MCP_ENTREGA` ligada, e o call site
declarando que passou pela confirmação. A flag é nova de propósito.
`USP_MCP_ALLOW_WRITES` está documentada nos três servidores como a flag que
**não** abre nada, e os testes de cada um afirmam isso; reaproveitá-la mudaria
em silêncio o significado de uma linha que existe em três arquivos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Treze funções, todas de leitura. Crescer isso é decisão de §9, não
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
# item de UM curso, com a nota e o peso de cada um — o máximo do item não vem
# nesta resposta, e a medida que fechou isso está no cabeçalho de `notas.py`
# (captura de 15/09/2026). Nenhuma das duas responde o que a outra
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
#
# A décima segunda e a décima terceira entraram em 17/09/2026, com
# `questionarios`, e o desenho está em
# `docs/superpowers/specs/2026-09-17-questionario-como-objeto-design.md`.
# Questionário é OUTRO objeto do Moodle: `mod_assign_*` não o vê, e até então
# `ja_entreguei` o recusava por escrito e mandava para `o_que_vence`, que só
# sabe a data. `mod_quiz_get_quizzes_by_courses` diz que o questionário existe,
# quando abre e fecha e quantas tentativas permite; `mod_quiz_get_user_attempts`
# diz quantas o aluno FINALIZOU. São duas e não três: `get_user_best_grade`
# ficou de fora porque a nota do questionário já sai em `notas`, e um segundo
# número por outro caminho é o problema, não a solução.
#
# Esta é a família mais delicada da allowlist até aqui: as três escritas de
# tentativa que o §2.2 recusa estão a um prefixo de distância, e duas LEITURAS
# da família entraram no bloqueio permanente na mesma data (ver lá). Igualdade
# exata de nome é o que libera; o prefixo `mod_quiz_get_` de P5 é teto e casa
# com cinco funções que este projeto recusa.
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
        "mod_quiz_get_quizzes_by_courses",
        "mod_quiz_get_user_attempts",
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
        # entregam em nome do usuário. Eram QUATRO até 15/09/2026; as duas que
        # saíram (`save_submission` e `submit_for_grading`) estão em
        # `ESCRITA_CONFIRMADA`, com as duas condições que as governam. Estas
        # duas ficam: `start_submission` abre tentativa nova sem plano possível
        # (o estado anterior é justamente o que ela destrói), e
        # `remove_submission` apaga o que já foi enviado.
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
        # --- acrescentados em 17/09/2026, com `questionarios` (spec do dia) ----
        # As PRIMEIRAS funções de LEITURA desta lista, e a mudança de caráter
        # fica escrita: até aqui o §2.2 dizia "não escreve em nome do aluno";
        # passa a dizer também "não lê o que não pode estar no contexto de um
        # modelo". `get_attempt_data` devolve o enunciado das questões de uma
        # tentativa EM ANDAMENTO; `get_attempt_summary` é a mesma tentativa,
        # por questão, antes do envio (catálogo §3.8 e §6.10). Nenhuma escreve,
        # e mesmo assim são a última coisa que se quer dentro do contexto de um
        # modelo durante uma prova. A allowlist já as nega por omissão; esta é
        # a segunda camada, e ela passou a ser necessária justamente porque o
        # prefixo `mod_quiz_get_` entrou no teto de P5 e casa com as duas.
        "mod_quiz_get_attempt_data",
        "mod_quiz_get_attempt_summary",
    }
)


# A variável de ambiente que liga a escrita de entrega, e só ela. Desligada por
# padrão, e só no Moodle — nem o RUCard nem o Jupiter têm escrita para ligar.
#
# O nome está aqui como constante, e não escrito à mão em cada mensagem, porque
# ele aparece em três lugares que precisam concordar: a leitura do ambiente, o
# motivo da recusa que o modelo lê, e o descritor das duas ferramentas. Um nome
# de variável escrito errado numa mensagem de erro é uma cura que não cura.
NOME_DA_FLAG = "USP_MCP_ENTREGA"

# As duas funções de escrita que saíram do bloqueio permanente em 15/09/2026.
# Elas NÃO estão na `ALLOWLIST` e nunca devem estar: a allowlist é a superfície
# de leitura, e um nome nela passa por igualdade exata sem mais nenhuma
# condição. Aqui as condições são o assunto.
ESCRITA_CONFIRMADA: frozenset[str] = frozenset(
    {
        "mod_assign_save_submission",
        "mod_assign_submit_for_grading",
    }
)


def entrega_habilitada() -> bool:
    """A flag está ligada NESTE processo?

    Lida do ambiente a cada chamada, e não no import: o servidor stdio lê o
    `.env` dentro de `chamar_ferramenta`, depois de o módulo já estar
    importado, e um valor congelado no import responderia sobre o ambiente de
    antes. Igualdade exata com "1" — "true", "sim" e "0" não ligam nada, e uma
    flag que liga escrita irreversível não é lugar para adivinhar intenção.
    """
    return os.environ.get(NOME_DA_FLAG) == "1"


@dataclass(frozen=True)
class Decisao:
    """Resultado de `decidir`. `motivo` existe para o Invariante 6: erro legível
    vence silêncio, e um `False` pelado não diz o que fazer com o resultado."""

    permitida: bool
    motivo: str


def decidir(
    funcao: str, permitir_escrita: bool = False, *, confirmada: bool = False
) -> Decisao:
    """Decide se `funcao` pode ser chamada.

    Três caminhos, nesta ordem, e a ordem é a decisão:

    1. **Bloqueio permanente.** Nega antes de olhar qualquer outra coisa, e
       nega mesmo com as duas flags ligadas (§2.2).
    2. **Escrita confirmada.** Permite só com `USP_MCP_ENTREGA=1` no ambiente
       **e** `confirmada=True` vindo do call site. As duas condições são
       independentes de propósito: a flag é do dono da máquina e vale para o
       processo inteiro; a confirmação é por chamada, e quem a declara é o
       código que acabou de conferir que o plano mostrado ainda é o plano real.
    3. **Allowlist.** Igualdade exata de nome, sem mais nenhuma condição — é a
       superfície de leitura, e ela não ganhou caso novo aqui.

    `permitir_escrita` é a flag do Invariante 1 (USP_MCP_ALLOW_WRITES) e
    continua sem *liberar* nada: o bloqueio permanente a ignora por definição, a
    allowlist não contém função de escrita, e o caminho 2 não a consulta — quem
    o governa é `USP_MCP_ENTREGA`. O parâmetro existe para deixar essa ausência
    de efeito explícita no call site.

    `confirmada` sozinho não abre nada, e é o ponto: um call site que declare
    confirmação com a flag desligada recebe a mesma recusa de quem não declarou.
    """
    if funcao in BLOQUEIO_PERMANENTE:
        return Decisao(
            permitida=False,
            motivo=(
                f"{funcao} está no bloqueio permanente — negada mesmo com "
                "permitir_escrita=True, pois não há configuração que libere."
            ),
        )

    if funcao in ESCRITA_CONFIRMADA:
        if not entrega_habilitada():
            return Decisao(
                permitida=False,
                motivo=(
                    f"{funcao} escreve no e-Disciplinas em seu nome, e a escrita "
                    f"está desligada neste servidor. Quem a liga é a variável de "
                    f"ambiente {NOME_DA_FLAG}=1, e ligá-la é decisão de quem é "
                    "dono do token — não deste processo."
                ),
            )
        if not confirmada:
            return Decisao(
                permitida=False,
                motivo=(
                    f"{funcao} escreve no e-Disciplinas em seu nome e não passou "
                    "pela confirmação. Peça o plano primeiro e repita a chamada "
                    "com o código que ele devolveu."
                ),
            )
        return Decisao(
            permitida=True,
            motivo=(
                f"{funcao} está liberada para esta chamada: a escrita está "
                "ligada neste servidor e a confirmação foi declarada."
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
