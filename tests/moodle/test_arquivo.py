"""T84–T90, T95c — a terceira ferramenta do Moodle, no singular.

Tudo offline: nenhum teste deste arquivo toca a rede. O `raiz` do depósito é
sempre `tmp_path`, para não escrever no cache real de quem roda a suíte.
"""
from __future__ import annotations

import pytest

from usp_mcp.moodle import arquivo as arq
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.erros import ErroMoodle

from .conftest import ClienteFalso


@pytest.fixture(autouse=True)
def _cache_limpo():
    """Cache de processo compartilhado entre casos produz verde que nunca chamou
    nada — o mesmo motivo pelo qual `limpar_cache` existe."""
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(conteudo_bruto, disciplinas_brutas, **extra):
    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_bruto,
        },
        **extra,
    )


@pytest.mark.contrato
def test_T84_sigla_que_nao_resolve_nao_gasta_chamada_de_conteudo(disciplinas_brutas):
    """Consultar o Moodle para descobrir que a pergunta estava errada é gastar
    chamada da conta do dono à toa."""
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
        }
    )

    with pytest.raises(ErroMoodle):
        arq.baixar_arquivo(cliente, "XYZ9999", "prova")

    chamadas = [nome for nome, _ in cliente.chamadas]
    assert "core_course_get_contents" not in chamadas
    assert cliente.downloads == []


@pytest.mark.contrato
def test_T85_nenhum_casamento_diz_o_total_da_disciplina(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """'nada com esse nome' e 'disciplina vazia' têm curas diferentes."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "zzz-nao-existe", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == []
    assert "29" in r.texto  # o total de itens de PSI3323


@pytest.mark.contrato
def test_T86_um_casamento_baixa_grava_e_devolve_o_caminho(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert len(r.baixados) == 1
    baixado = r.baixados[0]
    assert baixado.nome == "Prova-PSI3323-2026-Grupos.pdf"
    assert baixado.caminho.is_file()
    assert baixado.caminho.read_bytes().startswith(b"%PDF")
    assert str(baixado.caminho) in r.texto
    assert len(cliente.downloads) == 1


@pytest.mark.contrato
def test_T86b_a_resposta_diz_que_quem_abre_o_arquivo_e_quem_chamou(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Sem isso, um cliente que não saiba ler arquivo local recebe um caminho e
    não entende o que fazer com ele (Invariante 6)."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert "disco" in r.texto.lower()
    assert "abra" in r.texto.lower() or "abrir" in r.texto.lower()


@pytest.mark.contrato
def test_T87_ambiguidade_recusa_e_lista_secao_e_modulo(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """A colisão REAL de PSI3323: 'Dicas para a Prova.pdf' existe duas vezes,
    com ids 9599793 (seção Geral) e 9599833 (seção AULA 6). O nome sozinho não
    distingue — por isso o desempate mostra seção e módulo, não o id."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == [], "recusou e mesmo assim baixou"
    assert len(r.candidatos) == 2
    assert "Geral" in r.texto and "AULA 6" in r.texto
    assert "todos" in r.texto.lower()


@pytest.mark.contrato
def test_T89_casamento_ignora_acento(conteudo_bruto, disciplinas_brutas, tmp_path):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "formulario", raiz=tmp_path)

    assert len(r.baixados) == 1
    assert r.baixados[0].nome.startswith("Formul")


@pytest.mark.politica
def test_T90_link_externo_nao_e_baixado(conteudo_bruto, disciplinas_brutas, tmp_path):
    """Os 7 `url` de PSI3323 apontam para fora (YouTube, Google Docs). Baixá-los
    mandaria o token para outro host — e a allowlist do cliente recusaria."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Planilha de Notas", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == []
    assert len(r.links) == 1
    assert r.links[0].url.startswith("http")
    assert "link" in r.texto.lower()


@pytest.mark.contrato
def test_T95c_segunda_chamada_reusa_o_disco_sem_baixar_de_novo(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Invariante 5: TTL colado na taxa de mudança do dado. Aqui o 'TTL' é o
    `timemodified` no caminho — arquivo não modificado não é rebaixado."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    primeira = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)
    assert len(cliente.downloads) == 1

    segunda = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert len(cliente.downloads) == 1, "baixou de novo o que já estava em disco"
    assert segunda.baixados[0].caminho == primeira.baixados[0].caminho
    assert segunda.baixados[0].reusado is True
    assert primeira.baixados[0].reusado is False


@pytest.mark.politica
def test_T99c_nenhuma_url_interna_aparece_no_texto_da_resposta(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """A ferramenta que BAIXA também não emite a URL — o caminho local é a
    entrega, e a URL continua sendo o que não sai (Invariante 3)."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert "pluginfile.php" not in r.texto
    assert "/webservice/" not in r.texto
