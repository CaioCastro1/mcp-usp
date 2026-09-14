"""Camada 1 — Invariante 2: a superfície é allowlist, e o bloqueio é permanente.

Nenhum destes toca em rede, fixture ou SDK. São tabela de nomes contra uma
decisão. É a camada mais barata e a que protege o risco mais caro do projeto:
estas funções vão ser chamadas por um modelo interpretando linguagem ambígua.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

from usp_mcp.moodle import politica

pytestmark = pytest.mark.politica

# A camada `live` é o fonte que estes testes leem — não importam. Ler o arquivo
# em vez de importá-lo é de propósito: importar `tests.moodle.test_live` traria
# junto o módulo inteiro (e a fixture que exige `MOODLE_TOKEN`), e a propriedade
# que a Regra de Ouro afirma é sobre o TEXTO — "nome literal, escolhido à mão".
FONTE_LIVE = Path(__file__).resolve().parent / "test_live.py"

# Toda chamada ao Moodle da camada live passa por `cliente_real.chamar("<nome>"`.
# `\s*` entre os pedaços porque a chamada real quebra linha depois do parêntese,
# e um regex de uma linha só não a veria — falso verde é pior que falso vermelho
# numa guarda de segurança.
CHAMADA_LIVE = re.compile(r"""cliente_real\s*\.\s*chamar\s*\(\s*["']([^"']+)["']""")

# Os prefixos de leitura da allowlist de hoje (§9, 31/08 e 14/09). Prefixo aqui
# NÃO é a regra de autorização — o T6 continua provando que a política casa por
# igualdade exata, e glob não é blindagem. Isto é outra coisa: um teto sobre o
# que a allowlist pode ganhar sem passar pelo §9. `_save_`, `_submit_`, `_add_`
# e `_send_` não casam com nenhum destes, então entram vermelhos.
PREFIXOS_DE_LEITURA = (
    "core_calendar_get_",
    "core_webservice_get_",
    "core_enrol_get_",
    "core_course_get_",
    # 12/09/2026: a família `mod_assign_` tem leitura E escrita, e é a primeira
    # da allowlist em que isso acontece. O prefixo inclui o `get_` justamente
    # por isso — `mod_assign_` sozinho abriria a porta para `save_submission` e
    # `submit_for_grading`, que são as quatro vizinhas no bloqueio do §2.2.
    "mod_assign_get_",
    # 14/09/2026, com a ferramenta `notas`. A família `gradereport_` é a
    # primeira em que o prefixo do PLUGIN não serve de teto: ela tem duas
    # funções de escrita (`gradereport_overview_view_grade_report` e
    # `gradereport_user_view_grade_report`, que disparam evento de log) e uma
    # leitura que entrega nota DE TERCEIROS
    # (`gradereport_grader_get_users_in_report`). Por isso são dois prefixos
    # estreitos e não um `gradereport_`: o relatório, o verbo `get_`, e nada
    # de `grader`.
    "gradereport_overview_get_",
    "gradereport_user_get_",
)

# P4 vigia estes três nomes. Escrito à mão, e não derivado do módulo, porque
# apagar um teste da guarda tem de reprovar — uma lista derivada encolheria
# junto e daria verde.
GUARDAS_DA_REGRA_DE_OURO = (
    "test_p1_a_camada_live_so_chama_funcao_da_allowlist",
    "test_p2_nenhum_nome_bloqueado_aparece_na_camada_live",
    "test_p3_a_camada_live_nao_faz_sweep",
)


def _fonte_live() -> str:
    """O fonte da camada live, ou vermelho dizendo o que sumiu.

    Ausência do arquivo não pode virar verde (nem skip): P1-P3 afirmam algo
    SOBRE ele, e sem ele não afirmam nada. É a mesma regra que o `conftest`
    aplica à fixture higienizada — skip aqui é verde que não testou nada.
    """
    if not FONTE_LIVE.exists():
        pytest.fail(
            f"{FONTE_LIVE} não existe. Se a camada live mudou de lugar, mova "
            "esta guarda junto — ela é a única coisa que checa a Regra de Ouro "
            "(§3.1) num teste que o gate roda."
        )
    return FONTE_LIVE.read_text(encoding="utf-8")


def _marcas(alvo) -> set[str]:
    """Nomes das marcas de um módulo ou função de teste.

    `pytestmark` de módulo é um `MarkDecorator` solto quando há uma marca só, e
    lista quando há várias; em função é sempre lista. Os dois expõem `.name`.
    """
    marcas = getattr(alvo, "pytestmark", [])
    if not isinstance(marcas, (list, tuple)):
        marcas = [marcas]
    return {m.name for m in marcas}


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

    Cresceu de 1 para 4 em 31/08, por decisão registrada no §9: `material`
    precisa traduzir sigla em `courseid`, e isso custa duas funções além da que
    responde. E de 4 para 5 em 12/09, também no §9: o enunciado do EC-1 é um PDF
    que `core_course_get_contents` não devolve — os módulos `assign` chegam lá
    com `contents` vazio, e o arquivo só existe em `mod_assign_get_assignments`.

    E de 5 para 6 em 14/09, no §9: `ja_entreguei` responde "eu já entreguei
    isso?", e a única função que sabe a diferença entre rascunho salvo e entrega
    enviada é `mod_assign_get_submission_status`. `get_assignments`, que já
    estava aqui, diz o que EXISTE e o prazo — nunca o que foi feito.

    E de 6 para 8 no mesmo dia, com `notas`: as duas visões de nota do
    e-Disciplinas não competem, se complementam (catálogo §3.7), e a ferramenta
    escolhe UMA por invocação conforme a pergunta tenha ou não disciplina.

    O teste segue travando o conjunto INTEIRO — é o que impede a próxima sessão
    de acrescentar "só mais uma" sem passar pelo §9.
    """
    assert politica.ALLOWLIST == frozenset(
        {
            "core_calendar_get_action_events_by_timesort",
            "core_webservice_get_site_info",
            "core_enrol_get_users_courses",
            "core_course_get_contents",
            "mod_assign_get_assignments",
            "mod_assign_get_submission_status",
            "gradereport_overview_get_course_grades",
            "gradereport_user_get_grade_items",
        }
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


# --------------------------------------------------------------------------
# P1-P5 — a guarda da Regra de Ouro (§3.1), aqui e não em `test_live.py`.
#
# Ela morava lá, atrás de `USP_MCP_LIVE=1`, e o `scripts/gate.sh` exclui a
# camada live de propósito (um gate que depende da USP estar de pé reprova
# commit por motivo errado). Consequência medida: a asserção não rodou em
# nenhum commit desde 31/08 e apodreceu calada — ela congelava a `ALLOWLIST`
# em um nome, e a passagem de 1 para 4 está registrada no §9 do mesmo dia.
# Mesmo modo de falha que este backlog já registrou três vezes para o `main()`.
#
# O que muda: em vez de congelar um VALOR (que cresce por decisão prevista),
# estas cinco checam a PROPRIEDADE que o §3.1 afirma — "uma função, escolhida
# à mão, uma chamada por execução", isto é, nome literal no fonte, dentro da
# allowlist, sem sweep. O §3.1 continua sendo a autoridade; muda quem verifica
# e quando. Offline: nenhuma toca a rede da USP nem pede credencial.
# --------------------------------------------------------------------------


def test_p1_a_camada_live_so_chama_funcao_da_allowlist():
    """P1 — todo nome que a camada live chama está na `ALLOWLIST`.

    A propriedade, não o valor: a allowlist pode crescer pelo §9 sem derrubar
    este teste, mas a live não pode alcançar nada de fora dela.
    """
    chamadas = CHAMADA_LIVE.findall(_fonte_live())
    assert chamadas, (
        "nenhuma chamada `cliente_real.chamar(\"...\")` encontrada em "
        f"{FONTE_LIVE.name}. Ou a camada live perdeu o canário, ou a forma da "
        "chamada mudou e este regex ficou cego — nos dois casos a guarda parou "
        "de guardar, e vermelho é a resposta certa."
    )
    intrusas = sorted(set(chamadas) - politica.ALLOWLIST)
    assert not intrusas, (
        f"a camada live chama {intrusas}, fora da allowlist. Ou o nome está "
        "errado, ou a allowlist precisa de uma decisão no §9 — nunca do teste "
        "afrouxado (Invariante 2: o default é negar)."
    )


def test_p2_nenhum_nome_bloqueado_aparece_na_camada_live():
    """P2 — nenhum nome do §2.2 aparece no fonte da camada live.

    Substring, e não só chamada: um nome do bloqueio permanente escrito em
    qualquer lugar de um teste que roda com a credencial do dono já é um nome
    a uma linha de distância de ser chamado. P1 cobre o que É chamado; esta
    cobre o que está ao alcance da mão.
    """
    fonte = _fonte_live()
    presentes = sorted(n for n in politica.BLOQUEIO_PERMANENTE if n in fonte)
    assert not presentes, (
        f"nomes do bloqueio permanente (§2.2) no fonte de {FONTE_LIVE.name}: "
        f"{presentes}. Esta camada roda com o token pessoal do dono e cada "
        "chamada fica no log da conta."
    )


def test_p3_a_camada_live_nao_faz_sweep():
    """P3 — a camada live não itera sobre a `ALLOWLIST`.

    "Escolhida à mão" (§3.1) quer dizer nome literal no fonte. Um `for f in
    politica.ALLOWLIST: cliente.chamar(f)` passaria por P1 e P2 inteiro e
    ainda assim seria um laço sobre a lista — que é exatamente o que a Regra
    de Ouro proíbe, e o que uma allowlist futura maior torna barato de fazer.

    Lê a árvore em vez de casar texto porque `for` quebra linha, e olha o nó
    INTEIRO (iterável e corpo): um laço que indexe a lista no corpo varre
    igual, e nesta guarda o erro tem de ser pro lado de negar.
    """
    arvore = ast.parse(_fonte_live(), filename=str(FONTE_LIVE))
    lacos = []
    for no in ast.walk(arvore):
        if not isinstance(
            no,
            (ast.For, ast.AsyncFor, ast.ListComp, ast.SetComp, ast.DictComp,
             ast.GeneratorExp),
        ):
            continue
        for filho in ast.walk(no):
            achou = (
                isinstance(filho, ast.Attribute) and filho.attr == "ALLOWLIST"
            ) or (isinstance(filho, ast.Name) and filho.id == "ALLOWLIST")
            if achou:
                lacos.append(no.lineno)
                break
    assert not lacos, (
        f"`ALLOWLIST` dentro de for/comprehension em {FONTE_LIVE.name}, "
        f"linha(s) {lacos}. Um sweep sobre as 447 funções deste token passa "
        "por `start_attempt` e `submit_for_grading` (§3.1)."
    )


def test_p4_a_guarda_da_regra_de_ouro_roda_offline():
    """P4 — P1-P3 não carregam a marca `live`.

    Este é o teste que impede a repetição do bug: a guarda anterior era
    correta em intenção e inalcançável na prática, porque morava atrás de
    `USP_MCP_LIVE=1` e o `gate.sh` não roda essa camada. Devolvê-las para trás
    da env var — por marca de módulo ou de função — reprova aqui.
    """
    modulo = sys.modules[__name__]
    do_modulo = _marcas(modulo)
    assert "live" not in do_modulo, (
        "este módulo ganhou a marca `live`: o gate deixaria de rodar a guarda "
        "da Regra de Ouro, que é como ela apodreceu da primeira vez."
    )
    assert "politica" in do_modulo, (
        "o módulo perdeu a marca `politica` — a camada 1 é a que o gate roda."
    )
    for nome in GUARDAS_DA_REGRA_DE_OURO:
        guarda = getattr(modulo, nome, None)
        assert guarda is not None, (
            f"{nome} sumiu deste módulo. A guarda da Regra de Ouro não é "
            "opcional; se mudou de nome, atualize GUARDAS_DA_REGRA_DE_OURO."
        )
        assert "live" not in _marcas(guarda), f"{nome} ganhou a marca `live`."


def test_p5_a_allowlist_e_so_de_leitura():
    """P5 — toda função da allowlist casa com um prefixo de leitura conhecido.

    O teto que substitui o congelamento: T7 trava o conjunto exato e obriga a
    passar pelo §9, e esta trava a NATUREZA do que pode entrar. Uma função de
    escrita chegando por engano (`_save_`, `_submit_`, `_add_`, `_send_`) não
    casa com nenhum dos quatro prefixos e reprova aqui — cresce sem apodrecer.
    """
    fora = sorted(f for f in politica.ALLOWLIST if not f.startswith(PREFIXOS_DE_LEITURA))
    assert not fora, (
        f"funções na allowlist fora dos prefixos de leitura conhecidos: {fora}. "
        f"Prefixos: {list(PREFIXOS_DE_LEITURA)}. Se a função é de leitura e o "
        "prefixo é novo, a entrada dela é decisão de §9 — e o prefixo entra "
        "aqui junto, com o motivo. Se é de escrita, o Invariante 1 já a nega."
    )


# --------------------------------------------------------------------------
# T11-T12 — a auditoria de 14/09/2026, virada teste.
#
# O §2.2 nasceu de uma leitura do catálogo; em 14/09 as 447 funções que o
# e-Disciplinas libera ao token foram varridas por verbo de escrita (57
# candidatas) e classificadas contra as categorias que o próprio §2.2 usa.
# Quinze caíam dentro delas e estavam FORA da lista.
#
# A allowlist as negava por omissão — primeira linha, e ela funcionou. O §2.2 é
# a segunda, e o arquivo diz por quê: "garante que um erro futuro na allowlist
# ainda não libere um destes nomes". Uma segunda linha com buraco é uma segunda
# linha que ninguém sabe que não está lá.
#
# As duas listas abaixo são o registro da classificação. A primeira TEM de estar
# bloqueada; a segunda é o que foi olhado e deliberadamente deixado fora, com o
# motivo. Função de escrita nova que apareça no site e não esteja em nenhuma das
# duas é trabalho não feito, não silêncio.
# --------------------------------------------------------------------------

# Medidas vivas no token em 14/09/2026, e dentro das categorias do §2.2.
ESCRITAS_EM_NOME_DO_ALUNO = (
    # respondem/entregam em atividade que não é `assign`
    "mod_choice_submit_choice_response",
    "mod_choicegroup_submit_choicegroup_response",
    "mod_feedback_process_page",
    "mod_questionnaire_submit_questionnaire_response",
    # queimam tentativa
    "mod_feedback_launch_feedback",
    "mod_scorm_launch_sco",
    # publicam conteúdo assinado pelo usuário
    "mod_data_add_entry",
    "mod_glossary_add_entry",
    "core_blog_add_entry",
    # falam com terceiros em nome do usuário
    "core_comment_add_comments",
    "core_rating_add_rating",
    "core_notes_create_notes",
    "core_message_create_contact_request",
    # afirmam progresso que o usuário não fez
    "core_completion_mark_course_self_completed",
    "core_completion_update_activity_completion_status_manually",
)

# Escritas que a auditoria olhou e NÃO bloqueou, com o motivo. Ficar fora é
# decisão registrada, não esquecimento — e escrever isso aqui é o que impede a
# próxima varredura de reabrir as mesmas quinze perguntas.
ESCRITAS_FORA_DE_ESCOPO = {
    # Capacidade de professor/monitor. A conta de aluno não as alcança, e o §2.2
    # trata do uso indevido da conta de quem roda isto. Se um dia o projeto
    # servir conta com permissão de correção, elas entram — é decisão de §9.
    "mod_assign_save_grade": "nota — capacidade de quem corrige",
    "mod_assign_save_grades": "nota — capacidade de quem corrige",
    "mod_assign_submit_grading_form": "nota — capacidade de quem corrige",
    "mod_assign_save_user_extensions": "prazo — capacidade de quem corrige",
    "mod_diary_save_feedback": "nota — capacidade de quem corrige",
    "mod_journal_save_feedback": "nota — capacidade de quem corrige",
    # Escrevem no calendário PESSOAL, sem alcançar entrega nem terceiro.
    "core_calendar_create_calendar_events": "agenda pessoal",
    "core_calendar_submit_create_update_form": "agenda pessoal",
    "core_calendar_update_event_start_day": "agenda pessoal",
    # Conta e dados pessoais do próprio usuário, sem efeito acadêmico.
    "core_user_add_user_device": "registro de dispositivo",
    "core_user_add_user_private_files": "área privada do próprio usuário",
    "tool_dataprivacy_create_data_request": "pedido de dados do próprio usuário",
    # Emissão de certificado é consequência de conclusão, não caminho para ela;
    # a conclusão em si está bloqueada acima.
    "mod_simplecertificate_create_issue": "derivada da conclusão, que está bloqueada",
}


@pytest.mark.parametrize("funcao", ESCRITAS_EM_NOME_DO_ALUNO)
def test_t11_escrita_em_nome_do_aluno_esta_no_bloqueio_permanente(funcao):
    """T11 — a segunda linha cobre o que a auditoria de 14/09 encontrou.

    Reprovava para as quinze antes da correção: elas existem no site, escrevem
    em nome de quem roda isto, e o §2.2 não as nomeava.
    """
    assert funcao in politica.BLOQUEIO_PERMANENTE, (
        f"{funcao} escreve em nome do usuário e não está no §2.2. A allowlist a "
        "nega por omissão, mas o bloqueio permanente é a camada que sobrevive a "
        "um engano na allowlist — e é onde o motivo fica escrito."
    )


def test_t12_a_classificacao_da_auditoria_nao_se_sobrepoe():
    """T12 — nenhum nome está nas duas listas ao mesmo tempo.

    Sobreposição aqui significaria que a mesma função foi classificada como
    "tem de bloquear" e "decidimos não bloquear", e a próxima pessoa não saberia
    qual das duas leituras vale.
    """
    ambos = set(ESCRITAS_EM_NOME_DO_ALUNO) & set(ESCRITAS_FORA_DE_ESCOPO)
    assert not ambos, f"classificadas nos dois lados: {sorted(ambos)}"

    fora_mas_bloqueadas = set(ESCRITAS_FORA_DE_ESCOPO) & politica.BLOQUEIO_PERMANENTE
    assert not fora_mas_bloqueadas, (
        f"{sorted(fora_mas_bloqueadas)} estão no §2.2 mas a auditoria as declara "
        "fora de escopo. Uma das duas leituras mudou e a outra não acompanhou."
    )
