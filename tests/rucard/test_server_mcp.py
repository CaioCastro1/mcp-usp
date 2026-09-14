"""R38-R41: a fronteira MCP.

Fina de propósito, como as duas irmãs: o valor está na política, na projeção e
na ferramenta. O que só esta camada pode errar é a descrição que o modelo lê —
é ela que decide se "o que tem no bandejão hoje?" chega aqui ou vira busca na
web — o erro de nome desconhecido, e não arrastar o SDK para dentro da suíte.

R41 é o teste que a fronteira do Moodle não consegue ter: sem credencial
pessoal, a fronteira inteira roda ponta a ponta offline.
"""
import ast
import datetime
import pathlib

import pytest

from tests.rucard.conftest import HASH_DE_TESTE
from usp_mcp.rucard import erros, server
from usp_mcp.rucard.cliente import ClienteRucard

SEGUNDA = datetime.date(2026, 8, 24)


@pytest.mark.politica
def test_r38_descricao_fala_a_lingua_de_quem_pergunta():
    (ferramenta,) = server.listar_ferramentas()
    descricao = ferramenta["description"]

    for vazamento in ("/menu", "restaurants", "hash", "workinghours", "RUCard servicos"):
        assert vazamento not in descricao, (
            f"{vazamento!r} na descrição: o modelo escolhe a ferramenta lendo "
            "isto, e ninguém pergunta em nome de rota."
        )
    for vocabulario in ("bandejão", "almoço", "jantar", "hoje", "prefeitura", "sexta", "semana"):
        assert vocabulario in descricao.lower()

    # Invariante 7 na própria descrição: o que a ferramenta NÃO tem evita que o
    # modelo prometa histórico, café da manhã ou saldo do cartão.
    baixo = descricao.lower()
    assert "café" in baixo and "semana" in baixo
    assert "saldo" in baixo or "cartão" in baixo


@pytest.mark.politica
def test_r38b_o_schema_declara_os_quatro_rus_e_nao_convida_a_inventar_id():
    (ferramenta,) = server.listar_ferramentas()
    propriedades = ferramenta["inputSchema"]["properties"]

    assert ferramenta["inputSchema"]["required"] == []
    assert ferramenta["inputSchema"]["additionalProperties"] is False
    # "hoje, almoço, os quatro" é o caso mais comum: ele tem que ser o default.
    assert propriedades["dia"].get("default") == "hoje"

    enumerado = propriedades["restaurantes"]["items"]["enum"]
    assert enumerado == ["central", "prefeitura", "fisica", "quimicas"], (
        "o schema é onde o modelo aprende que só existem quatro RUs aqui, e "
        "pelo NOME que a pessoa fala — id numérico é detalhe da API. Sem enum, "
        "ele inventa e recebe negativa da allowlist: erro certo pela via mais cara."
    )
    descricao_do_dia = propriedades["dia"]["description"].lower()
    assert "sexta" in descricao_do_dia and "semana" in descricao_do_dia
    assert set(propriedades["refeicao"]["enum"]) == {
        "almoco", "jantar", "cafe", "todas"
    }


@pytest.mark.politica
def test_r39_nome_desconhecido_levanta_erro_legivel():
    with pytest.raises(erros.ErroRucard) as exc:
        server.chamar_ferramenta("saldo_do_cartao", {})
    assert "saldo_do_cartao" in str(exc.value)
    assert "bandejao" in str(exc.value)


@pytest.mark.politica
def test_r40_importar_o_servidor_nao_exige_o_sdk():
    arvore = ast.parse(pathlib.Path(server.__file__).read_text(encoding="utf-8"))
    for no in arvore.body:  # só o nível de módulo
        if isinstance(no, ast.Import):
            nomes = [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom):
            nomes = [no.module or ""]
        else:
            continue
        for nome in nomes:
            assert not nome.startswith("mcp"), (
                f"import de topo de {nome!r}: a suíte roda sem o SDK, e isso "
                "quebraria a coleta por uma dependência que as funções puras "
                "nem usam."
            )


@pytest.mark.contrato
def test_r41_fronteira_ponta_a_ponta_offline(gravador, respostas_da_fatia):
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    texto = server.chamar_ferramenta(
        "bandejao", {"dia": "24/08/2026", "refeicao": "almoco"}, cliente=cliente
    )

    assert "24/08/2026" in texto and "seg" in texto
    assert "CENTRAL" in texto and "QUÍMICAS" in texto
    assert "Iscas de tilápia empanadas" in texto, "o cardápio não chegou ao texto"
    assert "1065" in texto, "calorias fora do texto: é parte do 'vale a pena'"
    assert "R$ 2,00" in texto
    # O 7 não serve jantar; pedindo só almoço, isso não deve poluir a saída.
    assert "jantar" not in texto.lower()


@pytest.mark.contrato
def test_r41b_o_texto_declara_o_que_nao_sabe(gravador, respostas_da_fatia):
    cliente = ClienteRucard(gravador(respostas_da_fatia), hash_rucard=HASH_DE_TESTE)
    texto = server.chamar_ferramenta(
        "bandejao", {"dia": "25/12/2026"}, cliente=cliente
    )
    assert "⚠" in texto, "o aviso do Invariante 7 sumiu na formatação"
    assert "24/08/2026" in texto
