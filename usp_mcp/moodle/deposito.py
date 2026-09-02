"""Onde o arquivo baixado mora, e por que o caminho tem essa forma.

Fica **fora do repositório**, em `~/.cache/usp-mcp/moodle/`, por dois motivos:
numa instalação via `pip` não existe repositório nenhum (o §6 decide que cada
pessoa roda o servidor na própria máquina, com o próprio token), e material do
professor não deve ficar dentro da árvore de trabalho protegido só pelo
`.gitignore`.

A forma do caminho é

    <raiz>/<courseid>/<fileid>-<timemodified>/<slug>.<ext>

e cada segmento resolve um problema medido:

- **`fileid`** resolve uma colisão real: em PSI3323, `Dicas para a Prova.pdf`
  existe duas vezes, com ids diferentes (9599793 na seção *Geral*, 9599833 na
  *AULA 6*). Só o nome não distingue.
- **`timemodified`** faz o Invariante 5 valer de graça: arquivo já baixado e não
  modificado não é rebaixado, porque o diretório já existe. Arquivo alterado no
  Moodle ganha diretório novo, sem invalidação explícita nenhuma.
- **`slug`** preserva o nome legível para quem abre o arquivo, mas nunca é o
  `filename` cru: ele vem do Moodle e é entrada não confiável.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ_PADRAO = Path.home() / ".cache" / "usp-mcp" / "moodle"

# Teto do nome em disco. Nomes de arquivo de disciplina passam de 60 chars com
# facilidade; 128 preserva o reconhecível e não estoura limite de filesystem.
_MAX_NOME = 128

_PROIBIDOS = re.compile(r"[^A-Za-z0-9._-]")


def _slug(filename: str) -> str:
    """`filename` cru → nome seguro, ainda legível.

    Três passos, e o terceiro é o que importa: `..` sobrevive à whitelist,
    porque `.` está nela. Um nome que seja só pontos viraria travessia de
    diretório se alguém compusesse caminho com ele — então pontos iniciais caem.
    """
    bruto = (filename or "").strip().replace("\\", "/").split("/")[-1]
    limpo = _PROIBIDOS.sub("_", bruto).lstrip(".")
    limpo = limpo[:_MAX_NOME]
    return limpo or "arquivo"


def caminho_para(
    *,
    courseid: int,
    fileid: str,
    timemodified: int,
    filename: str,
    raiz: Path | None = None,
) -> Path:
    """O caminho deste arquivo, sem tocar o disco.

    `raiz` é injetável para que o teste não escreva no cache de verdade da
    máquina de quem roda a suíte.
    """
    base = Path(raiz) if raiz is not None else RAIZ_PADRAO
    caminho = (
        base
        / str(int(courseid))
        / f"{_slug(str(fileid))}-{int(timemodified or 0)}"
        / _slug(filename)
    )
    # Cinto e suspensório: se algum dia um segmento escapar da sanitização, é
    # aqui que o erro aparece, em vez de num arquivo escrito fora do depósito.
    if not caminho.resolve().is_relative_to(base.resolve()):
        raise ValueError(
            f"caminho calculado sairia do depósito: {caminho}. "
            "Isto é bug de sanitização, não entrada inesperada."
        )
    return caminho


def ja_baixado(caminho: Path) -> bool:
    """Existe e não está vazio.

    Zero byte em disco é resto de gravação interrompida, não cache válido —
    tratá-lo como pronto entregaria um arquivo vazio com cara de sucesso.
    """
    return caminho.is_file() and caminho.stat().st_size > 0


def gravar(caminho: Path, dados: bytes) -> Path:
    """Grava, criando o diretório. Devolve o caminho para encadear."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(dados)
    return caminho
