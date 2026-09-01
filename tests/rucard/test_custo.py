"""R34-R37: custo.

Aqui o RUCard consegue a asserção que o Jupiter não conseguiu ter. Lá o payload
DWR *era* a resposta, e a razão de redução real ficou em ~1,8x. Aqui 6/7 do
payload é semana que ninguém pediu, mais um catálogo de 27,7 kB que é tabela de
apoio: a redução é grande, e é o motivo de existir projeção em vez de repasse.

Os tetos são medidos, com folga declarada, e a trava que não envelhece é a
CATEGÓRICA (R36) — número aperta com o tempo, conjunto de chaves não.
"""
import datetime
import json

import pytest

from tests.rucard.conftest import HASH_DE_TESTE
from usp_mcp.rucard import ferramentas, server
from usp_mcp.rucard.cliente import ClienteRucard

pytestmark = pytest.mark.contrato

SEGUNDA = datetime.date(2026, 8, 24)

# Medido em 31/08/2026 contra as fixtures da Fase 1, no pior caso (4 RUs × 2
# refeições): 3.367 B de estrutura e 1.929 B de texto, em 23 linhas. Um RU só
# com as duas refeições dá 970 B. Teto com ~34% de folga sobre o pior caso,
# porque o cardápio é texto livre e o tamanho varia com o que a USP escreve.
TETO_SAIDA_B = 4_500

# Cru que a resposta substitui: 4 menus mais o catálogo = 39.615 B nas fixtures,
# ~9.900 tokens, para responder sobre UM dia.
CRU_APROXIMADO_B = 39_615


def tamanho(o):
    return len(json.dumps(o, ensure_ascii=False, default=str).encode())


def _resposta(gravador, respostas_da_fatia):
    """Função, e não fixture do pytest: uma fixture que constrói o objeto sob
    teste transforma `FAILED` em `ERROR` (§4 do CONVENTIONS.md)."""
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    return ferramentas.bandejao(cliente=cliente, hoje=SEGUNDA)


def test_r34_teto_absoluto_com_folga_declarada(gravador, respostas_da_fatia):
    resposta = _resposta(gravador, respostas_da_fatia)
    assert tamanho(resposta) <= TETO_SAIDA_B, f"saída: {tamanho(resposta)} B"


def test_r35_razao_de_reducao_medida_no_proprio_teste(gravador, respostas_da_fatia):
    resposta = _resposta(gravador, respostas_da_fatia)
    cru = sum(len(t.encode()) for t in respostas_da_fatia.values())
    assert cru > 30_000, "as fixtures encolheram: refaça a medida do §2 do spec"

    razao = cru / tamanho(resposta)
    assert razao > 10, (
        f"razão de redução {razao:.1f}x — abaixo do que justifica projetar. "
        "Se caiu, alguém passou a devolver a semana inteira ou o catálogo cru."
    )


def test_r35b_a_saida_nao_carrega_a_semana_que_ninguem_pediu(gravador, respostas_da_fatia):
    resposta = _resposta(gravador, respostas_da_fatia)
    despejo = json.dumps(resposta, ensure_ascii=False)
    # Datas dos outros seis dias da semana da Fase 1 não podem aparecer.
    for dia in ("25/08/2026", "26/08/2026", "27/08/2026", "28/08/2026",
                "29/08/2026", "30/08/2026"):
        assert dia not in despejo, (
            f"{dia} na resposta de 24/08: a projeção está devolvendo mais de um "
            "dia, e é 6/7 de payload que ninguém pediu."
        )
    # Nem o resto do catálogo.
    for gordura in ("EACH", "PIRACICABA", "latitude", "photourl", "hasCashier"):
        assert gordura not in despejo


def test_r36_conjunto_de_chaves_e_exatamente_o_declarado(gravador, respostas_da_fatia):
    resposta = _resposta(gravador, respostas_da_fatia)
    # A trava categórica: é assim que campo novo deixa de sobreviver por
    # descuido. R34 e R35 são numéricos e envelhecem; este não.
    assert set(resposta) == set(ferramentas.CAMPOS_SAIDA)

    for ru in resposta["restaurantes"]:
        assert set(ru) <= set(ferramentas.CAMPOS_RESTAURANTE), (
            f"campos fora do declarado no RU {ru.get('id')}: "
            f"{sorted(set(ru) - set(ferramentas.CAMPOS_RESTAURANTE))}"
        )
        for refeicao in ru["refeicoes"].values():
            assert set(refeicao) <= set(ferramentas.CAMPOS_REFEICAO), (
                f"campos fora do declarado numa refeição: "
                f"{sorted(set(refeicao) - set(ferramentas.CAMPOS_REFEICAO))}"
            )


def test_r37_erro_nunca_custa_mais_que_sucesso(gravador, respostas_da_fatia):
    resposta = _resposta(gravador, respostas_da_fatia)
    from tests.rucard.conftest import texto
    from usp_mcp.rucard.erros import ErroRucard

    respostas = dict(respostas_da_fatia)
    respostas["menu/6"] = (500, texto("erro_500"))
    cliente = ClienteRucard(gravador(respostas), hash_rucard=HASH_DE_TESTE)

    try:
        parcial = ferramentas.bandejao(
            cliente=cliente, hoje=SEGUNDA, restaurantes=["6"]
        )
        projetado = tamanho(parcial)
    except ErroRucard as exc:  # pragma: no cover — depende da regra de parcial
        projetado = tamanho({"erro": str(exc)})

    assert projetado < tamanho(resposta), (
        f"erro projetado {projetado} B >= sucesso {tamanho(resposta)} B. O HTML "
        "do Tomcat são 3.240 B que não respondem nada."
    )


def test_r37b_o_texto_para_o_modelo_tambem_tem_teto(gravador, respostas_da_fatia):
    resposta = _resposta(gravador, respostas_da_fatia)
    # A saída estruturada é o meio; o que chega ao modelo é o texto. Um teto só
    # na estrutura deixaria a formatação engordar sem ninguém ver.
    texto_formatado = server.formatar(resposta)
    assert len(texto_formatado.encode()) <= TETO_SAIDA_B
    assert len(texto_formatado.splitlines()) < 60
