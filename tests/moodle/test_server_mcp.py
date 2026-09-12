"""Camada 2 — a fronteira MCP, fina de propósito.

Só três testes, e é intencional: o valor da suíte está na projeção e na política,
que não têm nada a ver com protocolo. Aqui checa-se o que o MODELO vê — nome,
descrição e formato de saída. Sem depender do SDK: `server.py` expõe as duas
funções puras e o adaptador stdio é casca por cima.
"""
from __future__ import annotations

import pytest

from tests.moodle.conftest import ENTREGAS_PSI3323_SEM_ANEXO
from usp_mcp.moodle import server

pytestmark = pytest.mark.contrato


def test_expoe_exatamente_uma_ferramenta():
    """T42 — três ferramentas. Cada crescimento é decisão registrada no §9:
    a segunda (`material`) em 31/08, a terceira (`baixar_arquivo`) em 01/09."""
    fs = server.listar_ferramentas()
    assert [f["name"] for f in fs] == ["o_que_vence", "material", "baixar_arquivo"]


def test_o_nome_vem_da_pergunta_nao_da_funcao_do_moodle():
    """T43 — §5: `o_que_vence` é bom nome; `get_action_events_by_timesort` não.

    A descrição é o que faz o modelo escolher a ferramenta certa, então ela tem
    de usar o vocabulário de quem pergunta.
    """
    f = server.listar_ferramentas()[0]
    assert "get_action_events" not in f["description"]
    assert any(p in f["description"].lower() for p in ("entrega", "prazo", "vence"))


def test_ferramenta_desconhecida_da_erro_legivel():
    """T44 — Invariante 6 na fronteira: nome errado não devolve vazio."""
    with pytest.raises(Exception) as e:
        server.chamar_ferramenta("apagar_tudo", {})
    assert "apagar_tudo" in str(e.value)


def test_T100_o_descritor_de_baixar_arquivo_fala_a_lingua_de_quem_pergunta():
    f = [x for x in server.listar_ferramentas() if x["name"] == "baixar_arquivo"][0]

    assert "pluginfile" not in f["description"]
    assert "core_course_get_contents" not in f["description"]
    # A descrição TEM de dizer que devolve um caminho a ser aberto — sem isso o
    # modelo recebe um path e não sabe que o próximo passo é dele.
    assert "caminho" in f["description"].lower()
    props = f["inputSchema"]["properties"]
    assert set(props) == {"disciplina", "nome", "todos"}
    assert f["inputSchema"]["required"] == ["disciplina", "nome"]
    assert all(p.get("description") for p in props.values())


def test_T101_chamar_ferramenta_roteia_baixar_arquivo_com_cliente_injetado(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Sem credencial nenhuma: a injeção de cliente é o que torna a fronteira
    testável offline (§9, 31/08)."""
    from usp_mcp.moodle import disciplinas as dis

    from .conftest import ClienteFalso

    dis.limpar_cache()
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_bruto,
            "mod_assign_get_assignments": ENTREGAS_PSI3323_SEM_ANEXO,
        }
    )

    saida = server.chamar_ferramenta(
        "baixar_arquivo",
        {"disciplina": "PSI3323", "nome": "Grupos", "raiz": str(tmp_path)},
        cliente=cliente,
    )

    dis.limpar_cache()
    assert isinstance(saida, str)
    assert "Prova-PSI3323-2026-Grupos.pdf" in saida
    assert "pluginfile.php" not in saida


def test_T106_descricao_de_material_nao_afirma_premissa_refutada():
    """§9 de 01/09: 'baixá-lo exigiria a credencial do usuário' foi medido
    falso — o corpo do POST autentica sem token na URL. `material` é o
    primeiro passo natural de quem quer um arquivo ('me dá a lista 2 de
    PSI3323'), e a descrição não pode ler como beco sem saída: precisa
    apontar para `baixar_arquivo`."""
    f = [x for x in server.listar_ferramentas() if x["name"] == "material"][0]
    descricao = f["description"]

    assert "exigiria" not in descricao.lower()
    assert "baixar_arquivo" in descricao
