"""T41-T44: a fronteira MCP.

Fina de propósito. O valor do projeto está na política, no envelope e na
ferramenta — nada disso tem a ver com protocolo. O que esta camada precisa
garantir é o que só ela pode errar: a descrição que o modelo lê, o erro de
nome desconhecido, e não arrastar o SDK para dentro da suíte.

T44 é o teste que a fronteira irmã do Moodle não consegue ter: sem credencial,
a fronteira do Jupiter roda ponta a ponta offline.
"""
import ast
import pathlib

import pytest

from tests.jupiter.conftest import Gravador
from usp_mcp.jupiter import cliente, erros, server


@pytest.mark.politica
def test_t41_descricao_fala_a_lingua_de_quem_pergunta():
    (ferramenta,) = [
        f for f in server.listar_ferramentas() if f["name"] == "disciplina"
    ]
    descricao = ferramenta["description"]

    # O nome vem da pergunta, não da API (§5 do SPEC1).
    for vazamento in ("pubObterDisciplina", "ControlePublicoDWR", "DWR", "coddis"):
        assert vazamento not in descricao, (
            f"{vazamento!r} na descrição: o modelo escolhe a ferramenta lendo "
            "isto, e ninguém pergunta em nome de consulta."
        )
    for vocabulario in ("crédito", "ementa", "pré-requisito", "sigla"):
        assert vocabulario in descricao.lower()

    # Invariante 7 na própria descrição: dizer o que NÃO faz evita que o modelo
    # prometa horário de aula, que é scraping frágil e ficou fora da fatia.
    assert "horário" in descricao.lower()

    assert ferramenta["inputSchema"]["required"] == ["sigla"]


@pytest.mark.politica
def test_t42_nome_desconhecido_levanta_erro_legivel():
    with pytest.raises(erros.ErroJupiter) as exc:
        server.chamar_ferramenta("horario_da_turma", {"sigla": "PSI3323"})
    # "não existe" e "existe mas não achou nada" têm curas diferentes.
    assert "horario_da_turma" in str(exc.value)
    assert "disciplina" in str(exc.value)


@pytest.mark.politica
def test_t43_importar_o_servidor_nao_exige_o_sdk():
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
def test_t44_fronteira_ponta_a_ponta_offline(psi3323):
    # Sem credencial, a fronteira inteira é exercitável contra fixture — o que
    # a fronteira do Moodle não consegue, porque lá falta um token.
    c = cliente.ClienteJupiter(Gravador([psi3323]))
    texto = server.chamar_ferramenta("disciplina", {"sigla": "psi 3323"}, cliente=c)

    assert texto.startswith("PSI3323 — Laboratório de Eletrônica I")
    assert "45 h" in texto, "carga horária calculada não chegou ao texto"
    assert "3×15 + 0×30" in texto, "a conta fica à vista para ninguém 'corrigir' para cgahoreto"
    assert "⚠" in texto and "curso" in texto, "o aviso do Invariante 7 sumiu na formatação"
    assert "Ementa:" in texto
