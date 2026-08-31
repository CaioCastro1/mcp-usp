"""R42-R44: canário contra uspdigital.usp.br.

**Duas requisições reais por execução, no máximo**, escolhidas à mão. Nenhum
laço, nenhuma enumeração de id de RU — o Invariante 5 vale aqui como vale para
o Jupiter.

Diferença importante em relação à camada `live` do Moodle: esta **não** usa
credencial pessoal. A hash do RUCard é compartilhada e embutida no app oficial,
e nenhuma chamada daqui vai para o log de uma conta. Ainda assim fica atrás de
`USP_MCP_LIVE=1`, porque um gate que depende da USP estar de pé reprova commit
por motivo errado (§4 do CONVENTIONS.md).

Compara CHAVES, nunca valores: o cardápio muda toda semana sem que nada tenha
quebrado.
"""
import json
import os

import pytest

from tests.rucard.conftest import carregar
from usp_mcp.rucard import cliente as mod_cliente

pytestmark = pytest.mark.live

MOTIVO = (
    "canário ao vivo desligado. Exporte USP_MCP_LIVE=1 para bater em "
    "uspdigital.usp.br. Dado público, sem credencial pessoal — mas continua "
    "sendo requisição à USP, e o gate de commit não depende dela."
)

ao_vivo = pytest.mark.skipif(os.environ.get("USP_MCP_LIVE") != "1", reason=MOTIVO)


def _hash_do_ambiente():
    from usp_mcp.env import carregar_env

    carregar_env()
    valor = os.environ.get("RUCARD_HASH", "")
    if not valor:
        pytest.fail(
            "RUCARD_HASH não está no ambiente nem no .env — copie do "
            ".env.example (o valor é público, §1.2 do SPEC1)."
        )
    return valor


@ao_vivo
def test_r42_forma_da_resposta_real_bate_com_a_fixture():
    status, texto = mod_cliente.transporte_http(
        f"{mod_cliente.URL_BASE}/menu/6",
        f"hash={_hash_do_ambiente()}",
        {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": mod_cliente.AGENTE,
        },
    )
    assert status == 200

    vivo = json.loads(texto)
    esperado = carregar("menu_6")

    assert sorted(vivo) == sorted(esperado), (
        "as chaves de /menu mudaram: ou a fixture está velha, ou a API mudou de "
        "forma. Compare e atualize com decisão registrada no §9."
    )
    assert sorted(vivo["meals"][0]) == sorted(esperado["meals"][0])
    assert len(vivo["meals"]) == 7, "a semana deixou de ter 7 dias"
    assert isinstance(vivo["message"]["error"], bool), (
        "em /menu, message.error é booleano de verdade — se virou string, a "
        "detecção de erro do cliente precisa mudar (§1.2)."
    )
    # A semana devolvida é sempre a corrente: nenhuma data do passado distante.
    assert all("/" in d["date"] for d in vivo["meals"])


@ao_vivo
def test_r43_get_ainda_e_500_com_html():
    # O fato que obriga o POST. Medido em 27/08 e em 31/08; se um dia virar 200,
    # é notícia — e é decisão de §9, não de conveniência de código.
    import urllib.error
    import urllib.request

    pedido = urllib.request.Request(
        f"{mod_cliente.URL_BASE}/menu/6",
        headers={"User-Agent": mod_cliente.AGENTE},
        method="GET",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=20) as resposta:
            pytest.fail(
                f"GET /menu/6 devolveu HTTP {resposta.status}. Ele devolvia 500 "
                "com HTML do Tomcat nas duas medições — mudou."
            )
    except urllib.error.HTTPError as e:
        assert e.code == 500
        assert "html" in (e.headers.get("Content-Type") or "").lower()


def test_r44_skip_diz_o_motivo_por_escrito():
    # A diferença entre "não rodou" e "não rodou, e aqui está por quê" é o
    # Invariante 6 aplicado à própria suíte.
    if os.environ.get("USP_MCP_LIVE") == "1":
        pytest.skip("canário ligado; este teste cobre o caminho desligado")
    assert "USP_MCP_LIVE=1" in MOTIVO
    assert "uspdigital" in MOTIVO
    assert len(MOTIVO) > 80
