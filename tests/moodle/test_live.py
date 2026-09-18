"""Camada 3 — canário. Fala com a USP de verdade, e só quando mandam.

Existe por um motivo que o resto da suíte não cobre: a fixture é de 28/08/2026 e
congela. Sem esta camada, a USP pode mudar a API por baixo e a suíte continua
verde enquanto o servidor real quebra.

Regra de Ouro (§3.1): UMA função, escolhida à mão, uma chamada por execução.
Nada aqui itera sobre lista de funções — um sweep sobre as 447 passa por
`start_attempt` e `submit_for_grading` com a credencial do dono.
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tests.moodle.conftest import ARQUIVO_ENV
from usp_mcp.moodle.cliente import ClienteMoodle

pytestmark = [pytest.mark.live, pytest.mark.contrato]


@pytest.fixture(scope="module")
def cliente_real():
    token = os.environ.get("MOODLE_TOKEN")
    if not token:
        # Duas causas distintas, duas curas distintas (Invariante 6). A versão
        # anterior desta mensagem mandava copiar o .env.example para quem já
        # tinha o .env preenchido — o conftest é que não carregava o arquivo.
        if ARQUIVO_ENV is None:
            pytest.fail(
                "USP_MCP_LIVE=1 mas MOODLE_TOKEN está vazio, e nenhum .env foi "
                "encontrado (nem na raiz da suíte, nem no checkout principal). "
                "Copie .env.example para .env (§8 do SPEC1)."
            )
        pytest.fail(
            f"USP_MCP_LIVE=1 mas MOODLE_TOKEN está vazio. O .env FOI encontrado "
            f"em {ARQUIVO_ENV} e carregado — então a chave está ausente ou vazia "
            "lá dentro. Não é o arquivo que falta (§8 do SPEC1)."
        )
    return ClienteMoodle(
        token=token,
        url=os.environ.get("MOODLE_URL", "https://edisciplinas.usp.br"),
    )


def test_a_forma_da_resposta_real_ainda_bate_com_a_fixture(cliente_real, eventos_brutos):
    """T50 — o canário. Uma chamada, e compara só a FORMA.

    Não compara conteúdo de propósito: os eventos mudam todo dia, e um teste que
    falha por isso é ruído que ninguém lê depois da terceira vez.
    """
    vivo = cliente_real.chamar(
        "core_calendar_get_action_events_by_timesort", limitnum=5
    )
    assert set(vivo) == set(eventos_brutos)
    if vivo["events"]:
        esperadas = set(eventos_brutos["events"][0])
        obtidas = set(vivo["events"][0])
        faltando = esperadas - obtidas
        assert not faltando, f"campos sumiram da API desde 28/08/2026: {sorted(faltando)}"


# T51 — a guarda da Regra de Ouro (§3.1) mudou de camada: virou P1-P5 em
# `tests/moodle/test_politica.py`. Ela não podia ficar aqui: o `gate.sh` exclui
# a camada live de propósito, então uma asserção neste arquivo não roda em
# commit nenhum. Foi assim que esta apodreceu calada — congelou a `ALLOWLIST`
# em um nome e não reprovou quando ela foi a quatro, em 31/08. Guarda que só
# roda atrás de `USP_MCP_LIVE=1` é guarda que ninguém vê morrer.


def test_o_anexo_da_entrega_ainda_chega_com_os_campos_que_o_acervo_usa(
    cliente_real, entregas_ptc3314
):
    """T120 — o segundo canário, e ele guarda a quinta função da allowlist.

    A fixture de `mod_assign_get_assignments` é de 12/09/2026 e congela. O que
    importa não é o conteúdo — o professor troca o enunciado, e um teste que
    falhe por isso vira ruído — mas os cinco campos que `_item_de` lê do anexo:
    sem `fileurl` o arquivo some do acervo, e sem `filesize` o download perde a
    conferência de tamanho que detecta corte no meio.

    UMA chamada, com escopo de UMA disciplina (§3.1). Sem `courseids` esta
    função devolve as 74 matrículas, 1 MB (§9, 28/08).
    """
    vivo = cliente_real.chamar(
        "mod_assign_get_assignments", **{"courseids[0]": 142036}
    )

    assert set(vivo) == set(entregas_ptc3314)
    anexos = [
        anexo
        for curso in vivo.get("courses") or ()
        for entrega in curso.get("assignments") or ()
        for anexo in entrega.get("introattachments") or ()
    ]
    assert anexos, (
        "PTC3314 não tem mais nenhum anexo de entrega. Se o professor tirou os "
        "enunciados, troque a disciplina deste canário; se a API mudou de campo, "
        "é o acervo que quebrou."
    )
    faltando = {"filename", "filesize", "mimetype", "timemodified", "fileurl"} - set(
        anexos[0]
    )
    assert not faltando, f"campos sumiram da API desde 12/09/2026: {sorted(faltando)}"


# --------------------------------------------------------------------------
# E13 — o plano de uma atividade REAL bate com o que o site diz, SEM ESCREVER.
#
# **Escrita ao vivo não entra nesta suíte, em circunstância nenhuma.** Um teste
# que entregue atividade de verdade é o próprio acidente que o desenho da
# confirmação existe para evitar, e o token é a credencial pessoal do dono. Por
# isso este teste exercita só a metade de leitura: as duas chamadas que montam o
# plano já estavam na allowlist antes desta trilha, e o plano é função pura
# delas.
#
# As duas chamadas são literais e feitas AQUI, e não escondidas dentro de uma
# função do módulo, de propósito: é assim que as guardas da camada 1 (P1 e P3)
# enxergam o que esta camada alcança. Nenhum nome de função de escrita aparece
# neste arquivo, e P2 reprova se aparecer.
# --------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("USP_MCP_ENTREGA") != "1",
    reason=(
        "E13 é o canário da trilha de entrega e só roda com USP_MCP_ENTREGA=1 "
        "além de USP_MCP_LIVE=1. Ele NÃO escreve nada — as duas chamadas são de "
        "leitura e já existiam na allowlist —, e exigir a flag mesmo assim é "
        "deliberado: quem liga a flag é quem decidiu que esta trilha está em uso."
    ),
)
def test_e13_o_plano_de_uma_entrega_real_bate_com_o_site_sem_escrever(cliente_real):
    from usp_mcp.moodle import entrega as ent

    atividades_cruas = cliente_real.chamar(
        "mod_assign_get_assignments", **{"courseids[0]": 142036}
    )
    atividades = ent.projetar_atividades(atividades_cruas)
    assert atividades, "PTC3314 não tem mais nenhuma entrega"

    alvo = atividades[0]
    status_cru = cliente_real.chamar(
        "mod_assign_get_submission_status", assignid=alvo.assignid
    )
    plano = ent.montar_plano(status_cru, alvo, "PTC3314")

    # Cada campo do plano contra o lugar de onde ele veio. Comparar o plano com
    # ele mesmo provaria só que o dataclass guarda o que recebeu; o que importa
    # é que a LEITURA de cada campo bate com a resposta viva, porque é a leitura
    # que decide se a escrita seria recusada ou liberada.
    ultima = status_cru["lastattempt"]
    submissao = ultima.get("submission") or {}

    assert plano.status == (submissao.get("status") or "")
    assert plano.travada == bool(ultima["locked"])
    assert plano.pode_enviar == bool(ultima["cansubmit"])
    assert plano.pode_editar == bool(ultima["canedit"])
    assert plano.em_grupo == (bool(ultima["teamsubmission"]) or alvo.em_grupo)
    assert plano.tempo_limite == (ultima.get("timelimit") or 0)

    arquivos_vivos = [
        arquivo["filename"]
        for plugin in submissao.get("plugins") or ()
        for area in plugin.get("fileareas") or ()
        for arquivo in area.get("files") or ()
        if arquivo.get("filename")
    ]
    assert [a.nome for a in plano.arquivos] == arquivos_vivos

    # O código é estável sobre a MESMA leitura: se ele variasse, a segunda
    # chamada seria impossível contra o site de verdade, e isso é coisa que só
    # o dado vivo mostra.
    assert ent.codigo_do_plano(plano, verbo="entrega") == ent.codigo_do_plano(
        ent.montar_plano(status_cru, alvo, "PTC3314"), verbo="entrega"
    )

    # E a saída não vaza endereço de arquivo com credencial colada atrás.
    texto = ent.texto_do_plano(
        plano,
        verbo="entrega",
        agora=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    assert "pluginfile.php" not in texto


# --------------------------------------------------------------------------
# QO28 — a hipótese principal do spec de 17/09 virada canário.
#
# `questionarios` nasceu ANTES da captura, e o desenho lê `attempts`, `timeopen`
# e `timeclose` de `mod_quiz_get_quizzes_by_courses` como HIPÓTESE sobre o que
# uma conta de aluno recebe. O código degrada declaradamente se não vierem
# (QO12, QO14); este teste é o que diz, no dia em que rodar, se a degradação é
# a exceção ou o caminho normal.
#
# UMA chamada, com escopo de UMA disciplina, nome literal (§3.1). Só a primeira
# das duas funções: a segunda exige um `quizid` que sairia desta resposta, e
# encadear as duas aqui seria a camada live começando a montar a ferramenta —
# quem monta é o módulo, e o módulo já tem vinte testes offline.
# --------------------------------------------------------------------------


def test_qo28_a_conta_de_aluno_recebe_os_campos_que_questionarios_le(cliente_real):
    from usp_mcp.moodle.questionarios import CAMPOS_LIDOS_DO_QUESTIONARIO

    vivo = cliente_real.chamar(
        "mod_quiz_get_quizzes_by_courses", **{"courseids[0]": 142036}
    )

    assert "quizzes" in vivo, f"a resposta não tem `quizzes`: {sorted(vivo)}"
    if not vivo["quizzes"]:
        pytest.fail(
            "PTC3314 não tem mais questionário nenhum no e-Disciplinas. Troque a "
            "disciplina deste canário — o boletim de 15/09 tinha treze."
        )
    faltando = set(CAMPOS_LIDOS_DO_QUESTIONARIO) - set(vivo["quizzes"][0])
    assert not faltando, (
        f"a conta de aluno NÃO recebe {sorted(faltando)} em "
        "`mod_quiz_get_quizzes_by_courses`. A hipótese do spec de 17/09 caiu: a "
        "degradação de QO12/QO14 é o caminho normal, e isso vai para o §9."
    )
