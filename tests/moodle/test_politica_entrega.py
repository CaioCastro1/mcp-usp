"""E1-E6: as duas condições que governam a escrita, e o que elas NÃO abriram.

Camada 1, offline, sem rede e sem SDK. É tabela de nomes contra uma decisão —
a mesma natureza do `test_politica.py`, e num arquivo separado porque o assunto
é outro: lá a pergunta é "o que este projeto lê", aqui é "o que ele escreve, e
sob quais condições".

O desenho inteiro está em
`docs/superpowers/specs/2026-09-15-entrega-com-confirmacao-design.md`. As três
coisas que estes seis testes travam:

1. **Duas condições independentes.** A flag é do ambiente e vale para o processo
   inteiro; a confirmação é por chamada. Nenhuma das duas sozinha abre nada, e
   E1/E2 são as duas metades dessa frase.
2. **A flag é nova.** `USP_MCP_ALLOW_WRITES` continua sendo a que não abre nada,
   nos três servidores, e nada aqui a consulta.
3. **O que ficou.** As três de questionário não saíram, e as outras duas de
   `mod_assign` também não. E4 e E5 são o alarme para o dia em que alguém
   resolver "só mais uma".
"""
from __future__ import annotations

import pytest

from usp_mcp.moodle import politica

pytestmark = pytest.mark.politica

# As duas que saíram do bloqueio permanente em 15/09/2026, escritas à mão.
# Derivar do módulo faria estes testes concordarem com o conjunto que
# encontrassem — inclusive um que tivesse ganho `mod_quiz_start_attempt`.
AS_DUAS = ("mod_assign_save_submission", "mod_assign_submit_for_grading")

# As três que NÃO saíram, e a razão está no spec: para entrega de atividade
# existe estado anterior legível e rascunho que se sobrescreve, então dá para
# mostrar um plano fiel; para tentativa de questionário não existe rascunho,
# `start_attempt` já é irreversível, e o plano honesto seria "vou abrir uma
# tentativa e não sei dizer o que acontece depois".
AS_TRES_DE_QUESTIONARIO = (
    "mod_quiz_start_attempt",
    "mod_quiz_save_attempt",
    "mod_quiz_process_attempt",
)

# E as duas de `mod_assign` sobre as quais o spec ficou CALADO. Ele fala das
# quatro-menos-duas e nunca nomeia estas; silêncio em spec de política se
# resolve pelo padrão do projeto, que é negar. Estão aqui para que a decisão
# seja uma linha de teste e não uma lacuna que a próxima sessão preenche
# sozinha.
AS_DUAS_QUE_O_SPEC_NAO_CITOU = (
    "mod_assign_start_submission",
    "mod_assign_remove_submission",
)


@pytest.fixture
def com_a_flag(monkeypatch):
    monkeypatch.setenv(politica.NOME_DA_FLAG, "1")


@pytest.fixture(autouse=True)
def sem_a_flag_por_padrao(monkeypatch):
    """O default de TODO teste deste arquivo é a flag desligada.

    Autouse e não opcional: a suíte inteira tem de ficar verde com a flag ligada
    no ambiente, e um teste que dependesse do ambiente herdado afirmaria uma
    coisa diferente conforme quem o rodou. Quem quer a flag pede `com_a_flag`, e
    aí a asserção é sobre um estado escrito, nunca sobre o estado de quem passou.
    """
    monkeypatch.delenv(politica.NOME_DA_FLAG, raising=False)


# ------------------------------------------------------------------ E1 a E3


@pytest.mark.parametrize("funcao", AS_DUAS)
def test_e1_sem_a_flag_e_recusa_e_o_motivo_cita_a_flag(funcao):
    """E1 — o padrão é negar, e a negativa diz o nome da variável.

    Citar a flag pelo nome é o que separa uma recusa de um beco sem saída: quem
    lê a mensagem descobre que existe um caminho e quem decide sobre ele. Uma
    negativa muda faria alguém procurar o defeito no código.
    """
    decisao = politica.decidir(funcao)

    assert not decisao.permitida
    assert politica.NOME_DA_FLAG in decisao.motivo, (
        f"a recusa de {funcao} não nomeia a variável de ambiente que a governa: "
        f"{decisao.motivo!r}"
    )
    # E nem com a flag de escrita ANTIGA, que continua não abrindo nada.
    assert not politica.decidir(funcao, permitir_escrita=True).permitida
    # Nem declarando confirmação: a confirmação sozinha não abre nada, e é por
    # isso que ela não é a garantia.
    assert not politica.decidir(funcao, confirmada=True).permitida


@pytest.mark.parametrize("funcao", AS_DUAS)
def test_e2_com_a_flag_e_sem_confirmacao_ainda_e_recusa(funcao, com_a_flag):
    """E2 — ligar a flag não é autorizar uma escrita, é abrir a possibilidade.

    Este é o teste que impede a degeneração mais provável do desenho: alguém
    liga a flag no `.env` e, dali em diante, toda chamada escreve. As duas
    condições são independentes, e esta é a que sobrevive à flag ligada.
    """
    decisao = politica.decidir(funcao)

    assert not decisao.permitida
    assert "confirma" in decisao.motivo.lower(), (
        f"a recusa de {funcao} com a flag ligada não fala da confirmação: "
        f"{decisao.motivo!r}"
    )


@pytest.mark.parametrize("funcao", AS_DUAS)
def test_e3_com_a_flag_e_com_confirmacao_e_permitida(funcao, com_a_flag):
    """E3 — a política não é um `return False` disfarçado.

    Sem isto, E1 e E2 ficariam verdes para sempre com um caminho de escrita que
    nunca abre — que é a mesma falha do T8, aplicada ao conjunto novo.
    """
    decisao = politica.decidir(funcao, confirmada=True)

    assert decisao.permitida, decisao.motivo
    assert funcao in decisao.motivo


# ---------------------------------------------------------------------- E4


@pytest.mark.parametrize(
    "funcao", AS_TRES_DE_QUESTIONARIO + AS_DUAS_QUE_O_SPEC_NAO_CITOU
)
def test_e4_o_que_ficou_e_recusado_nas_tres_combinacoes(funcao, monkeypatch):
    """E4 — flag desligada, flag ligada, e flag ligada com confirmação.

    As três combinações, e não só a última, porque o modo de falha que importa
    aqui é o descuido de implementação: um `in` trocado por prefixo, um conjunto
    montado com a família inteira, um `or` onde devia haver `and`. Qualquer um
    dos três deixaria estas passar em pelo menos uma das combinações.

    As duas de `mod_assign` que o spec não citou entram na mesma varredura das
    três de questionário de propósito: não há diferença de tratamento entre
    "ficou de fora por decisão escrita" e "ficou de fora porque ninguém falou
    dela". As duas ficam negadas, e negadas do mesmo jeito.
    """
    monkeypatch.delenv(politica.NOME_DA_FLAG, raising=False)
    assert not politica.decidir(funcao).permitida
    assert not politica.decidir(funcao, confirmada=True).permitida

    monkeypatch.setenv(politica.NOME_DA_FLAG, "1")
    assert not politica.decidir(funcao).permitida
    assert not politica.decidir(funcao, confirmada=True).permitida
    assert not politica.decidir(
        funcao, permitir_escrita=True, confirmada=True
    ).permitida

    assert funcao in politica.BLOQUEIO_PERMANENTE, (
        f"{funcao} saiu do bloqueio permanente. Sair de lá é decisão registrada "
        "antes do código, e o conjunto que a recebe tem condições próprias — "
        "não é o mesmo que simplesmente deixar de negar."
    )


# ----------------------------------------------------------------- E5 e E6


def test_e5_o_bloqueio_permanente_tem_40_nomes_e_nao_tem_as_duas_de_assign():
    """E5 — a conta: 40 até 15/09/2026, 38 depois que duas saíram, e 40 de novo
    em 17/09/2026 quando duas LEITURAS entraram.

    Um número exato num teste é chato de propósito: ele obriga quem mexe na
    lista a dizer quantos nomes entraram ou saíram, e é a única coisa que pega
    uma remoção acidental no meio de uma lista de quarenta linhas. As duas de
    17/09 são `mod_quiz_get_attempt_data` e `mod_quiz_get_attempt_summary` —
    enunciado de prova em curso —, e a razão está no spec
    `2026-09-17-questionario-como-objeto-design.md` (R4) e em `test_politica_
    questionario.py` (QO2). O número voltar a 40 é coincidência de aritmética,
    não de conteúdo: são outros dois nomes.
    """
    assert len(politica.BLOQUEIO_PERMANENTE) == 40, (
        f"o bloqueio permanente tem {len(politica.BLOQUEIO_PERMANENTE)} nomes. "
        "Ele tinha 40 até 15/09/2026, 38 depois que duas saíram por decisão "
        "registrada, e 40 desde 17/09/2026 com duas leituras que entraram. Se "
        "saiu ou entrou mais alguma, a decisão vem antes deste número."
    )
    for funcao in AS_DUAS:
        assert funcao not in politica.BLOQUEIO_PERMANENTE, (
            f"{funcao} está nos dois lugares ao mesmo tempo. O bloqueio "
            "permanente ganha de tudo, então isto não é redundância: é a "
            "escrita confirmada morta e ninguém sabendo."
        )


def test_e6_os_tres_conjuntos_nao_se_cruzam():
    """E6 — coerência interna, e cada cruzamento é um defeito diferente.

    `ESCRITA_CONFIRMADA` cruzando com `ALLOWLIST` seria o pior dos três: um nome
    na allowlist passa por igualdade exata e NADA mais, então a flag e a
    confirmação deixariam de existir para ele sem que nenhuma linha dissesse
    isso. É o oposto exato do que estes conjuntos foram escritos para fazer.
    """
    assert not (politica.ESCRITA_CONFIRMADA & politica.ALLOWLIST), (
        "função de escrita na allowlist: lá ela passaria sem flag e sem "
        f"confirmação — {sorted(politica.ESCRITA_CONFIRMADA & politica.ALLOWLIST)}"
    )
    assert not (politica.ESCRITA_CONFIRMADA & politica.BLOQUEIO_PERMANENTE)
    assert not (politica.ALLOWLIST & politica.BLOQUEIO_PERMANENTE)

    assert set(politica.ESCRITA_CONFIRMADA) == set(AS_DUAS), (
        "o conjunto de escrita confirmada mudou de tamanho. Ele tem duas "
        "funções e crescer é decisão registrada antes do código — o spec que o "
        "criou recusa por escrito as três de questionário, e as duas de "
        f"`mod_assign` que sobraram nunca foram discutidas: "
        f"{sorted(politica.ESCRITA_CONFIRMADA)}"
    )


def test_e6b_a_flag_e_a_nova_e_so_o_valor_1_a_liga(monkeypatch):
    """E6 (segunda metade) — a flag antiga não foi reaproveitada.

    `USP_MCP_ALLOW_WRITES` está documentada nos três servidores como a flag que
    não abre nada, e os testes de cada um afirmam isso. Se ela passasse a abrir
    a escrita de entrega, três arquivos mudariam de significado em silêncio.
    """
    monkeypatch.delenv(politica.NOME_DA_FLAG, raising=False)
    monkeypatch.setenv("USP_MCP_ALLOW_WRITES", "1")

    assert not politica.entrega_habilitada()
    for funcao in AS_DUAS:
        assert not politica.decidir(
            funcao, permitir_escrita=True, confirmada=True
        ).permitida, f"{funcao} abriu com a flag ERRADA"

    # E o valor: uma flag que liga escrita irreversível não adivinha intenção.
    for valor in ("0", "", "true", "sim", "yes", "2"):
        monkeypatch.setenv(politica.NOME_DA_FLAG, valor)
        assert not politica.entrega_habilitada(), f"{valor!r} não devia ligar nada"
    monkeypatch.setenv(politica.NOME_DA_FLAG, "1")
    assert politica.entrega_habilitada()
