"""T92, T95, T96 — o depósito: caminho seguro, nome legível, reuso.

`filename` vem do Moodle e é entrada não confiável. Na amostra de PSI3323 nenhum
tem separador de caminho, mas amostra não prova ausência — este repo já registrou
esse erro três vezes.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from usp_mcp.moodle import deposito


def _caminho(tmp_path, **troca):
    base = dict(
        courseid=142033,
        fileid="9599792",
        timemodified=1753400000,
        filename="Prova-PSI3323.pdf",
        raiz=tmp_path,
    )
    base.update(troca)
    return deposito.caminho_para(**base)


def test_T92_filename_com_travessia_nao_escapa_do_deposito(tmp_path):
    for veneno in ("../../etc/passwd", "..", ".", "/etc/passwd", "a/b/c.pdf"):
        caminho = _caminho(tmp_path, filename=veneno)
        assert caminho.resolve().is_relative_to(tmp_path.resolve()), veneno
        assert ".." not in caminho.parts


def test_T92b_o_nome_legivel_do_arquivo_e_preservado(tmp_path):
    caminho = _caminho(tmp_path, filename="Roteiro Exp2 - Fonte Linear.pdf")
    # Espaço e hífen viram sublinhado/hífen, mas o nome continua reconhecível
    # e a extensão sobrevive — é o que o agente vê quando abre o arquivo.
    assert caminho.name.endswith(".pdf")
    assert "Roteiro" in caminho.name
    assert "Exp2" in caminho.name


def test_T92c_nome_absurdamente_longo_e_truncado(tmp_path):
    caminho = _caminho(tmp_path, filename="x" * 500 + ".pdf")
    assert len(caminho.name) <= 128


def test_T92d_filename_vazio_ainda_produz_um_nome(tmp_path):
    caminho = _caminho(tmp_path, filename="")
    assert caminho.name


def test_T95_arquivo_ja_gravado_e_reconhecido(tmp_path):
    caminho = _caminho(tmp_path)
    assert deposito.ja_baixado(caminho) is False

    deposito.gravar(caminho, b"%PDF-1.4")

    assert deposito.ja_baixado(caminho) is True
    assert caminho.read_bytes() == b"%PDF-1.4"


def test_T95b_arquivo_gravado_vazio_nao_conta_como_baixado(tmp_path):
    """Zero byte em disco é resto de gravação interrompida, não cache válido."""
    caminho = _caminho(tmp_path)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"")

    assert deposito.ja_baixado(caminho) is False


def test_T96_timemodified_diferente_produz_caminho_diferente(tmp_path):
    antigo = _caminho(tmp_path, timemodified=1753400000)
    novo = _caminho(tmp_path, timemodified=1753499999)

    assert antigo != novo
    assert antigo.parent != novo.parent


def test_T96b_fileid_diferente_produz_caminho_diferente(tmp_path):
    """A colisão real de PSI3323: mesmo filename, dois ids."""
    um = _caminho(tmp_path, fileid="9599793", filename="Dicas para a Prova.pdf")
    outro = _caminho(tmp_path, fileid="9599833", filename="Dicas para a Prova.pdf")

    assert um != outro


def test_T96c_timemodified_ausente_vira_zero_e_nao_quebra(tmp_path):
    caminho = _caminho(tmp_path, timemodified=0)
    assert caminho.resolve().is_relative_to(tmp_path.resolve())


def test_a_raiz_padrao_fica_fora_do_repositorio():
    """Num `pip install` não existe repositório; e material do professor não
    deve ficar na árvore de trabalho protegido só pelo .gitignore."""
    assert deposito.RAIZ_PADRAO.is_absolute()
    assert "usp-mcp" in str(deposito.RAIZ_PADRAO)
    assert Path.cwd() not in deposito.RAIZ_PADRAO.parents
