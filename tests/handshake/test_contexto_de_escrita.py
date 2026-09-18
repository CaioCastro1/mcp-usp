"""G1-G4: o servidor CONTA que existe escrita desligada, e não a torna chamável.

As duas metades importam juntas, e é por isso que cada teste aqui assere as
duas sobre o MESMO processo:

- **Passa a saber.** O `initialize` devolve `instructions` que nomeiam a
  variável, dizem que a capacidade existe, que está desligada e o que ela custa.
  Antes de 17/09/2026 esse campo não existia e o servidor não contava nada de
  si além da lista de ferramentas.
- **Não passa a insistir.** No mesmo processo, o `tools/list` continua com dez
  ferramentas, nenhuma delas destrutiva. O canal que mudou é o de INFORMAÇÃO; a
  superfície de AÇÃO é byte por byte a de antes. Não há item novo para escolher,
  logo não há chamada gasta, recusa lida nem contorno procurado.

Pelo fio de um processo de verdade, e não por introspecção do módulo, pelo mesmo
motivo do E14: `instructions` é um argumento do `MCPServer`, e um argumento que o
SDK ignorasse deixaria a função pura verde e o cliente sem nada. Já custou caro
neste repositório acreditar no declarado.

**Os processos sobem com o ambiente escrito à mão**, um com a flag em "1" e
outro em "0", para que estas asserções não dependam de quem rodou a suíte.
"""
from __future__ import annotations

import pytest

from tests.handshake.conftest import (
    MOTIVO_SEM_SDK,
    ClienteStdio,
    _tem_sdk,
)
from usp_mcp.moodle import politica

pytestmark = pytest.mark.handshake

SERVIDOR = "usp_mcp.moodle.server"
FLAG = politica.NOME_DA_FLAG
AS_DUAS = {"salvar_rascunho", "entregar"}


def _abrir(valor_da_flag: str):
    """Sobe o servidor com a flag neste valor e devolve (instructions, tools)."""
    if not _tem_sdk():
        pytest.skip(MOTIVO_SEM_SDK)
    with ClienteStdio(SERVIDOR, env={FLAG: valor_da_flag}) as cliente:
        info = cliente.apertar_mao()
        return info.get("instructions") or "", cliente.pedir("tools/list")["tools"]


def test_g1_sem_a_flag_o_initialize_conta_que_a_escrita_existe_e_esta_desligada():
    instrucoes, _ = _abrir("0")

    assert instrucoes, (
        "o servidor não mandou `instructions` no initialize. Sem esse campo o "
        "assistente só sabe o que está no `tools/list`, e o que está desligado "
        "não está lá — que é exatamente o defeito relatado."
    )
    assert "DESLIGADA" in instrucoes
    assert FLAG in instrucoes, "não disse QUAL variável liga"
    assert "NÃO tem desfazer" in instrucoes, "não declarou o custo"


def test_g2_e_no_mesmo_processo_nada_novo_ficou_chamavel():
    """G2 — a metade que impede a cura de virar o defeito que a antiga evitava.

    Contar em prosa e acrescentar um item ao `tools/list` seriam duas curas
    diferentes; só a primeira foi feita, e este teste é o que segura isso.
    """
    _, ferramentas = _abrir("0")
    nomes = {f["name"] for f in ferramentas}

    assert not (nomes & AS_DUAS), (
        f"com {FLAG} desligada o servidor anuncia {sorted(nomes & AS_DUAS)}. "
        "Contar que a capacidade existe é informação; pôr um item chamável que "
        "sempre recusa é ensinar o modelo a procurar o jeito de passar."
    )
    # O que este teste protege é "a flag acrescenta EXATAMENTE as duas, e nada
    # mais". Fixar o total em 10 dizia isso por tabela e amarrava a asserção a um
    # número que não é assunto dela: a ferramenta `questionarios`, de leitura,
    # entrou no mesmo dia e derrubou o teste sem que nada tivesse quebrado.
    # Comparar os dois estados do fio diz o mesmo e não envelhece.
    _, com_a_flag = _abrir("1")
    a_mais = {f["name"] for f in com_a_flag} - nomes
    assert a_mais == AS_DUAS, (
        f"ligar {FLAG} acrescentou {sorted(a_mais)}, e deveria acrescentar "
        f"exatamente {sorted(AS_DUAS)}. Ferramenta que aparece junto com a "
        "escrita, sem ser de escrita, é efeito colateral de configuração."
    )
    destrutivas = [
        f["name"]
        for f in ferramentas
        if (f.get("annotations") or {}).get("destructiveHint") is True
    ]
    assert not destrutivas, f"sem a flag há ferramenta destrutiva no fio: {destrutivas}"


def test_g3_com_a_flag_o_texto_muda_e_fala_das_duas_que_apareceram():
    """G3 — sem esta metade, G1 ficaria verde num servidor que diz "desligada"
    para sempre, inclusive na máquina de quem ligou."""
    instrucoes, ferramentas = _abrir("1")
    nomes = {f["name"] for f in ferramentas}

    assert "LIGADA" in instrucoes and "DESLIGADA" not in instrucoes, (
        f"com {FLAG}=1 as instruções ainda dizem que a escrita está desligada:\n"
        f"{instrucoes}"
    )
    for ferramenta in sorted(AS_DUAS):
        assert ferramenta in instrucoes, (
            f"as instruções não citam {ferramenta!r}, que está no `tools/list` "
            "deste mesmo processo"
        )
    assert AS_DUAS <= nomes, f"as duas não apareceram: {sorted(nomes)}"


@pytest.mark.parametrize("valor_da_flag", ["0", "1"])
def test_g4_as_instrucoes_nao_nomeiam_funcao_do_moodle(valor_da_flag):
    """G4 — informar não é entregar a receita, e aqui pelo fio.

    Mesma regra do diagnóstico, que conta as funções bloqueadas e não as nomeia:
    o nome de que a pessoa precisa é o da variável, e ele está lá.
    """
    instrucoes, _ = _abrir(valor_da_flag)

    nomeadas = sorted(
        f
        for f in (
            set(politica.ESCRITA_CONFIRMADA)
            | set(politica.BLOQUEIO_PERMANENTE)
            | set(politica.ALLOWLIST)
        )
        if f in instrucoes
    )
    assert not nomeadas, f"as instruções no fio nomeiam funções do Moodle: {nomeadas}"


@pytest.mark.parametrize("valor_da_flag", ["0", "1"])
def test_g5_as_instrucoes_no_fio_dizem_onde_esta_o_env_deste_processo(valor_da_flag):
    """G5 (18/09/2026) — o caminho do `.env`, pelo fio.

    Uso real de 17/09: o assistente respondeu que não sabia onde ficava o `.env`.
    O servidor sabe (`usp_mcp.env.achar_env()`), e o processo filho sobe da
    mesma árvore que este teste, então os dois têm de apontar para o mesmo
    arquivo — ou os dois têm de dizer que não há nenhum. Pelo fio, e não pela
    função pura, porque é no `initialize` que o assistente lê isso.
    """
    from usp_mcp.env import achar_env

    instrucoes, _ = _abrir(valor_da_flag)
    caminho = achar_env()

    if caminho is None:
        assert "não achou arquivo .env nenhum" in instrucoes
    else:
        assert str(caminho) in instrucoes, (
            f"as instruções no fio não trazem {caminho}, que é o .env que o "
            "processo lê"
        )
