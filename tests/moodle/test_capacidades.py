"""C1-C8: o texto que conta ao assistente o que está desligado.

Camada 1, offline, sem rede e sem SDK: é texto contra uma decisão, como o
`test_politica_entrega.py` é tabela de nomes contra uma decisão.

O desenho está em
`docs/superpowers/specs/2026-09-17-assistente-sabe-o-que-esta-desligado-design.md`.
O defeito que ele conserta é de 17/09/2026 e veio de uso real: o assistente não
sabia que existe uma capacidade de escrita, porque com a flag desligada as duas
ferramentas não entram no `tools/list` e o `tools/list` era o único canal pelo
qual o servidor contava de si.

O que estes testes travam, e cada um é uma metade de uma frase que não pode se
partir:

1. **Saber.** O texto existe, diz que a capacidade existe, nomeia a variável e
   declara o custo (entregar não tem desfazer) — C1, C2.
2. **Sem insistir.** Ele não é convite, não manda ligar, e não entrega a receita
   de chamada nenhuma: nenhum nome de função do Moodle sai daqui — C4, C5.
3. **Sem envelhecer calado.** A versão curta do diagnóstico é literalmente o
   começo da inteira, os nomes de ferramenta batem com os que o servidor
   anuncia, e o texto tem teto de tamanho porque viaja em toda conexão — C3,
   C6, C7.
"""
from __future__ import annotations

import pytest

from usp_mcp.moodle import capacidades, politica

pytestmark = pytest.mark.politica


@pytest.fixture
def desligada(monkeypatch):
    # `delenv` e não `setenv("0")`: o estado que interessa é "a pessoa não
    # ligou", e ele inclui a variável ausente. Sem isto o teste dependeria de
    # quem rodou a suíte — o `.env` do dono declara a flag.
    monkeypatch.delenv(politica.NOME_DA_FLAG, raising=False)


@pytest.fixture
def ligada(monkeypatch):
    monkeypatch.setenv(politica.NOME_DA_FLAG, "1")


def test_c1_desligada_o_texto_conta_que_existe_o_que_custa_e_quem_liga(desligada):
    texto = capacidades.estado_da_escrita()

    assert "DESLIGADA" in texto, "o estado tem de sair em letra que não se perde"
    assert politica.NOME_DA_FLAG in texto, (
        "sem o nome da variável o texto informa que existe um caminho e esconde "
        "qual é — que é a metade inútil da informação"
    )
    assert ".env" in texto, "não disse ONDE a variável mora"
    assert "NÃO tem desfazer" in texto, (
        "o custo é metade do que faz a pessoa decidir, e é o que não volta"
    )
    assert "dona do token" in texto, "não disse de QUEM é a decisão"


def test_c2_ligada_o_texto_muda_e_nao_diz_que_esta_desligada(ligada):
    """C2 — o texto que só falasse do estado desligado envelheceria calado no
    servidor de quem ligou, e "o assistente sabe o que está ligado" é a mesma
    pergunta lida do outro lado."""
    texto = capacidades.estado_da_escrita()

    assert "LIGADA" in texto
    assert "DESLIGADA" not in texto, f"diz as duas coisas ao mesmo tempo:\n{texto}"
    assert capacidades.NOME_RASCUNHO in texto and capacidades.NOME_ENTREGAR in texto, (
        "com a escrita ligada as duas estão no `tools/list`, e nomeá-las aqui é "
        "o contrário de anunciar o que não existe"
    )
    assert "NÃO tem desfazer" in texto


@pytest.mark.parametrize("estado", ["desligada", "ligada"])
def test_c3_a_versao_curta_e_o_comeco_exato_da_inteira(estado, request):
    """C3 — anti-drift entre os dois lugares que dizem a mesma coisa.

    O diagnóstico usa a curta e o `initialize` usa a inteira. Se fossem dois
    textos parecidos, o dia em que um mudasse seria o dia em que o servidor
    passaria a dizer duas coisas sobre si mesmo — e a segunda cópia é sempre a
    que envelhece calada.
    """
    request.getfixturevalue(estado)

    curta = capacidades.estado_da_escrita(curto=True)
    inteira = capacidades.estado_da_escrita()

    assert inteira.startswith(curta), (
        "a versão curta deixou de ser um pedaço da inteira:\n"
        f"curta: {curta!r}\ninteira: {inteira!r}"
    )
    assert len(inteira) > len(curta), "a inteira virou a curta — some um dos dois usos"


@pytest.mark.parametrize("estado", ["desligada", "ligada"])
def test_c4_nenhum_nome_de_funcao_do_moodle_sai_neste_texto(estado, request):
    """C4 — informar não é entregar a receita.

    Este texto chega ao modelo na abertura de toda conexão. Nomear
    `mod_assign_submit_for_grading` ali seria escrever o alvo no mesmo lugar em
    que ele escolhe o que chamar — a mesma razão pela qual o diagnóstico conta
    as funções bloqueadas e não as nomeia. O que a pessoa precisa saber é o nome
    da VARIÁVEL e o custo, e os dois estão lá.
    """
    request.getfixturevalue(estado)
    texto = capacidades.instrucoes()

    nomeadas = sorted(
        f
        for f in (
            set(politica.ESCRITA_CONFIRMADA)
            | set(politica.BLOQUEIO_PERMANENTE)
            | set(politica.ALLOWLIST)
        )
        if f in texto
    )
    assert not nomeadas, f"o texto nomeia funções do Moodle: {nomeadas}"


@pytest.mark.parametrize("estado", ["desligada", "ligada"])
def test_c5_o_texto_nao_manda_ligar(estado, request):
    """C5 — informação neutra, nunca convite.

    A regra é do dono e não muda: o padrão é não escrever, e a pessoa liga de
    propósito ou não liga. Um texto que RECOMENDE ligar reintroduz o defeito
    pelo outro lado — não ensina a insistir numa ferramenta, ensina a insistir
    numa configuração.
    """
    request.getfixturevalue(estado)
    texto = capacidades.instrucoes().lower()

    convites = [p for p in ("ligue", "habilite", "recomendo", "basta ", "é só ") if p in texto]
    assert not convites, f"o texto convida em vez de informar: {convites}\n{texto}"


def test_c6_o_texto_diz_que_ligar_nao_e_passo_do_assistente(desligada):
    """C6 — a única frase que cobre o buraco que o desenho não cobre.

    Quem lê isto tem shell na maior parte dos clientes, e alcança o `.env` tanto
    quanto alcança o código. Não há portão a construir aqui; há uma frase a
    dizer, e ela é sobre de quem é a decisão.
    """
    texto = capacidades.instrucoes()

    assert "Ligar por conta própria não é o caminho" in texto
    assert "insistir" in texto, (
        "o texto precisa dizer, para o próprio modelo, que não há o que tentar "
        "enquanto a variável não estiver lá"
    )


@pytest.mark.parametrize("estado", ["desligada", "ligada"])
def test_c7_as_instrucoes_cabem_no_orcamento_de_toda_conexao(estado, request):
    """C7 — teto declarado, porque isto viaja em TODA conexão.

    O campo é o lugar certo para o que a lista de ferramentas não diz, e o lugar
    errado para o que ela já diz. Sem um teto, ele vira o sétimo README do
    repositório, pago em tokens por conexão. O número é generoso e existe para
    reprovar crescimento, não para brigar por uma frase.
    """
    request.getfixturevalue(estado)
    texto = capacidades.instrucoes()

    assert len(texto) <= 1800, (
        f"as instruções estão com {len(texto)} caracteres. Elas carregam só o "
        "que o `tools/list` não tem como carregar — o que cada ferramenta faz "
        "já viaja na descrição dela."
    )


def test_c8_os_nomes_daqui_sao_os_que_o_servidor_anuncia(ligada):
    """C8 — as duas constantes de texto contra o `tools/list` de verdade.

    `capacidades.py` não importa o `server` (seria ciclo), então os nomes estão
    escritos duas vezes. Este teste é o que impede as duas cópias de divergirem
    — um texto que fale de uma ferramenta com outro nome manda a pessoa procurar
    o que não existe.
    """
    from usp_mcp.moodle import server

    anunciadas = {f["name"] for f in server.listar_ferramentas()}

    assert {capacidades.NOME_RASCUNHO, capacidades.NOME_ENTREGAR} <= anunciadas, (
        "os nomes declarados em capacidades.py não são os que o servidor anuncia "
        f"com a flag ligada: {sorted(anunciadas)}"
    )
