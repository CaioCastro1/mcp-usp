"""Camada 2 — a fronteira MCP, fina de propósito.

Só três testes, e é intencional: o valor da suíte está na projeção e na política,
que não têm nada a ver com protocolo. Aqui checa-se o que o MODELO vê — nome,
descrição e formato de saída. Sem depender do SDK: `server.py` expõe as duas
funções puras e o adaptador stdio é casca por cima.
"""
from __future__ import annotations

import pytest

import json

from tests.moodle.conftest import FIXTURE_DISCIPLINAS, ENTREGAS_PSI3323_SEM_ANEXO
from usp_mcp.moodle import server


def disciplinas_brutos():
    """As 74 matrículas, sem passar pela fixture de sessão: este módulo usa a
    lista dentro de um laço, e pedir a fixture por parâmetro amarraria o caso a
    uma assinatura que os outros testes daqui não têm."""
    return json.loads(FIXTURE_DISCIPLINAS.read_text(encoding="utf-8"))

pytestmark = pytest.mark.contrato


def test_expoe_exatamente_uma_ferramenta():
    """T42 — seis ferramentas. Cada crescimento é decisão registrada no §9:
    `material` em 31/08, `baixar_arquivo` em 01/09, `diagnostico`,
    `ja_entreguei` e `notas` em 14/09.

    A lista é exata, e não um `in`, porque o ponto é obrigar quem acrescenta a
    próxima a passar por aqui — é este teste que transforma "acrescentei uma
    ferramenta" em decisão declarada em vez de efeito colateral.
    """
    fs = server.listar_ferramentas()
    assert [f["name"] for f in fs] == [
        "o_que_vence",
        "material",
        "baixar_arquivo",
        "diagnostico",
        "ja_entreguei",
        "notas",
    ]


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


def test_T107_o_descritor_de_ja_entreguei_declara_o_custo_e_o_encaixe():
    """A descrição é o único lugar onde o modelo lê quanto custa chamar.

    Esta ferramenta é a primeira que faz **uma chamada por entrega**, e o
    catálogo registra o perfil dela: barata em token, cara em latência (§3.5).
    Um modelo que não sabe disso a chama para as dez disciplinas em sequência.
    E ela é a metade de `o_que_vence`: quem pergunta "o que falta" está
    perguntando as duas coisas.
    """
    f = [x for x in server.listar_ferramentas() if x["name"] == "ja_entreguei"][0]

    assert "submission_status" not in f["description"]
    assert "chamada" in f["description"].lower(), "não declarou o custo"
    assert "o_que_vence" in f["description"], "não aponta para a ferramenta do prazo"
    props = f["inputSchema"]["properties"]
    assert set(props) == {"disciplina", "entrega"}
    assert f["inputSchema"]["required"] == ["disciplina"]
    assert all(p.get("description") for p in props.values())


def test_T108_chamar_ferramenta_roteia_ja_entreguei_com_cliente_injetado(
    disciplinas_brutas, entregas_ptc3314
):
    from usp_mcp.moodle import disciplinas as dis

    from .conftest import ClienteFalso, status_de_entrega

    dis.limpar_cache()
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 8214},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "mod_assign_get_assignments": entregas_ptc3314,
            "mod_assign_get_submission_status": lambda p: status_de_entrega(),
        }
    )

    saida = server.chamar_ferramenta(
        "ja_entreguei", {"disciplina": "PTC3314", "entrega": "EC-1"}, cliente=cliente
    )

    dis.limpar_cache()
    assert "EC-1" in saida
    assert "pluginfile.php" not in saida


def test_T109_chamar_ferramenta_roteia_notas_com_e_sem_disciplina():
    """As duas metades do parâmetro opcional atravessam a fronteira.

    É o caminho que nenhum outro teste alcança: T78 registra a ferramenta e T79
    confere o schema, mas o `if` que escolhe entre as duas visões mora em
    `chamar_ferramenta`, e verde nos dois não é verde nele.
    """
    from usp_mcp.moodle import disciplinas as dis

    from .conftest import ClienteFalso, itens_de_nota_falsos, notas_gerais_falsas

    for argumentos, esperado in (
        ({}, "gradereport_overview_get_course_grades"),
        ({"disciplina": "PTC3314"}, "gradereport_user_get_grade_items"),
    ):
        dis.limpar_cache()
        cliente = ClienteFalso(
            {
                "core_webservice_get_site_info": {"userid": 8214},
                "core_enrol_get_users_courses": disciplinas_brutos(),
                "gradereport_overview_get_course_grades": notas_gerais_falsas(
                    [(142036, "8,50")]
                ),
                "gradereport_user_get_grade_items": itens_de_nota_falsos(),
            }
        )

        saida = server.chamar_ferramenta("notas", argumentos, cliente=cliente)

        assert esperado in [f for f, _ in cliente.chamadas], argumentos
        assert "PTC3314" in saida
        # §3.3 atravessando a fronteira inteira, e não só a projeção.
        assert "Gunthen" not in saida
    dis.limpar_cache()


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
