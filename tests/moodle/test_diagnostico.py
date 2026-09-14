"""D1-D6: a ferramenta que responde "isto funciona no Moodle da minha faculdade?".

Offline inteiro. O `site_info` é o único insumo, e ele vem de dublê — o que esta
suíte prova não é que a USP responde, é que a RESPOSTA é lida certo, inclusive
quando o site não é o esperado. É justamente o caso "site diferente" que a
ferramenta existe para atender, e ele não tem como ser exercitado contra a USP.
"""
from __future__ import annotations

import pytest

from tests.moodle.conftest import ClienteFalso
from usp_mcp.moodle import diagnostico as diag
from usp_mcp.moodle import politica

pytestmark = pytest.mark.contrato

# As funções que o e-Disciplinas expunha em 14/09/2026, reduzidas ao que importa
# aqui: as cinco da allowlist mais duas do bloqueio permanente, para D5 ter o que
# contar. A lista real tem 447 nomes e nenhum deles muda o que estes testes
# afirmam.
_SITE_COMPLETO = {
    "sitename": "Moodle de Alguma Faculdade",
    "release": "5.0.8+ (Build: 20260722)",
    "userid": 999,
    "functions": [
        {"name": n, "version": "2026"}
        for n in sorted(politica.ALLOWLIST)
        + ["mod_quiz_start_attempt", "core_message_send_instant_messages"]
    ],
}


def _cliente(info):
    return ClienteFalso({"core_webservice_get_site_info": info})


def test_d1_site_completo_diz_que_as_ferramentas_funcionam():
    texto = diag.diagnostico(_cliente(_SITE_COMPLETO))

    assert "Moodle de Alguma Faculdade" in texto
    assert "5.0.8+" in texto, "a versão do Moodle é metade da resposta de compatibilidade"
    for ferramenta in diag.FUNCOES_POR_FERRAMENTA:
        assert f"{ferramenta:16} OK" in texto, f"{ferramenta} devia estar OK:\n{texto}"


def test_d2_funcao_ausente_reprova_so_a_ferramenta_que_depende_dela():
    """D2 — o caso que motivou a ferramenta: um site que atende PARTE.

    Dizer "não funciona" porque uma das três não funciona seria mentir sobre as
    outras duas, e é o erro que um diagnóstico binário cometeria.
    """
    parcial = dict(_SITE_COMPLETO)
    parcial["functions"] = [
        f for f in _SITE_COMPLETO["functions"] if f["name"] != "mod_assign_get_assignments"
    ]

    texto = diag.diagnostico(_cliente(parcial))

    assert "o_que_vence      OK" in texto, (
        "o_que_vence não depende de mod_assign_get_assignments e foi reprovada junto:\n"
        + texto
    )
    assert "mod_assign_get_assignments" in texto, "não disse QUAL função falta"
    # Escrito à mão, e não derivado de `FUNCOES_POR_FERRAMENTA`: derivar da
    # tabela que gera o texto faria o teste concordar consigo mesmo. `ja_entreguei`
    # entrou nesta lista em 14/09 — ela pergunta o status de cada `assign` que
    # `get_assignments` lista, então sem a função ela não tem por onde começar.
    reprovadas = sorted(
        l.split()[0] for l in texto.splitlines() if "NÃO — faltam" in l
    )
    assert reprovadas == ["baixar_arquivo", "ja_entreguei", "material"], (
        "reprovou o conjunto errado de ferramentas:\n" + texto
    )


def test_d3_site_sem_lista_de_funcoes_nao_afirma_que_nada_funciona():
    """D3 — Invariante 6: "não consegui ler" ≠ "não tem nada".

    Um site que não devolva `functions` no `site_info` continua podendo
    responder tudo. Tratar ausência de informação como informação seria o falso
    negativo que este projeto persegue desde o §9 de 28/08.
    """
    mudo = {k: v for k, v in _SITE_COMPLETO.items() if k != "functions"}

    texto = diag.diagnostico(_cliente(mudo))

    assert "não devolveu a lista de funções" in texto
    assert "NÃO significa que não funcionam" in texto
    assert "NÃO — faltam" not in texto, (
        "reprovou ferramenta com base numa lista que não conseguiu ler:\n" + texto
    )


def test_d4_a_tabela_por_ferramenta_cobre_a_allowlist_inteira():
    """D4 — a guarda que impede a tabela de envelhecer calada.

    `FUNCOES_POR_FERRAMENTA` é escrita à mão porque a pergunta é por ferramenta.
    O preço disso é drift: uma função nova entrando na allowlist sem entrar aqui
    faria o diagnóstico declarar OK uma ferramenta que perdeu um pré-requisito.
    """
    union = {f for exigidas in diag.FUNCOES_POR_FERRAMENTA.values() for f in exigidas}
    assert union == set(politica.ALLOWLIST), (
        "a tabela e a allowlist divergem — sobrando aqui: "
        f"{sorted(union - set(politica.ALLOWLIST))}; faltando aqui: "
        f"{sorted(set(politica.ALLOWLIST) - union)}"
    )


def test_d5_o_texto_conta_as_bloqueadas_mas_nao_as_nomeia():
    """D5 — não dar ao modelo o vocabulário que a política existe para negar.

    Nomear as funções do §2.2 num texto que o modelo lê é escrever a lista de
    alvos no mesmo lugar onde ele escolhe o que chamar. A contagem entrega o que
    importa — que as duas camadas têm razão de existir — sem entregar os nomes.
    """
    texto = diag.diagnostico(_cliente(_SITE_COMPLETO))

    assert "bloqueio permanente" in texto, "a contagem sumiu do diagnóstico"
    nomeadas = [f for f in politica.BLOQUEIO_PERMANENTE if f in texto]
    assert not nomeadas, f"o diagnóstico nomeou funções bloqueadas: {sorted(nomeadas)}"


def test_d6_custa_exatamente_uma_chamada():
    """D6 — o custo declarado na descrição é o custo real.

    A descrição promete ao modelo "UMA chamada". Uma segunda entrando aqui por
    refactor faria a ferramenta mentir para quem decide se vale chamá-la — e
    cada chamada fica no log da conta do dono (§1.1).
    """
    cliente = _cliente(_SITE_COMPLETO)
    diag.diagnostico(cliente)

    assert len(cliente.chamadas) == 1, f"chamou {len(cliente.chamadas)} vezes"
    assert cliente.chamadas[0][0] == "core_webservice_get_site_info"
