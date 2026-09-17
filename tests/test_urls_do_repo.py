"""U1-U3: a URL que manda baixar este projeto aponta para este projeto.

Existe por um estrago medido em 14/09/2026: um commit trocou o dono do
repositório nas URLs do `README.md`, de `CaioCastro1` para `Castro1`, que é
outra conta. A URL nova não resolve, e quebrou **as três** instruções de
instalação de uma vez: o prompt do caminho rápido, o `pip install git+…` e o
`git clone` da seção do código.

Passou despercebido porque nada aqui olha para URL. Quem seguisse o guia levava
um erro do `git` — que não diz que a culpa é do README — e ia embora.

A regra NÃO é "toda URL do GitHub aponta para nós": o `SPEC1.md` e as `notas/`
citam `loyaniu/moodle-mcp`, `moodle/moodle`, `uspdev/senhaunica-*` e outros, e
proibir isso mataria a comparação com o concorrente e a referência ao core. A
regra é mais estreita e é a que pega o defeito real: **URL que aponta para um
repositório chamado `mcp-usp` tem de ter o dono certo.**

Offline, custa um `read_text` por arquivo, e entra no gate junto com o resto.
"""
from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# O dono, escrito à mão. Se o repositório mudar de dono ou de nome um dia, este
# teste reprova e obriga a decisão a ser declarada aqui — é o mesmo desenho do
# T7 sobre a allowlist. Derivar do `git remote` pareceria mais esperto e seria
# pior: numa cópia clonada de um fork o teste passaria a abençoar a URL errada.
DONO = "CaioCastro1"
REPO = "mcp-usp"

# Casa `github.com/dono/repo` e `github.com:dono/repo` (a forma SSH do clone),
# com ou sem `.git` no fim, e com ou sem caminho depois, como `/issues` e `/blob/...`.
# A barra entrou no olhar-adiante quando o `pyproject.toml` passou a declarar
# `[project.urls]`: sem ela o endereço de issues não casava com nada, e a única
# URL do arquivo que a varredura enxergava era a `Homepage`. Uma regra que não
# alcança metade do que existe para alcançar fica verde sem ter olhado.
ENDERECO = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?=[\s)\"'`/]|$)")

# Onde a instrução de instalação pode morar. Arquivo novo que mande baixar o
# projeto e não esteja aqui é buraco: U3 existe para essa lista não envelhecer.
#
# `pyproject.toml` entrou depois: o `[project.urls]` é a única forma de quem
# instalou por `pipx`/`uvx` achar o repositório (`pip show usp-mcp`), e um dono
# errado ali é ainda mais calado que no README: não quebra comando nenhum, só
# leva a pessoa para uma página que não existe. `CONTRIBUTING.md` entrou pelo
# mesmo motivo: ele manda abrir PR e issue neste repositório. Ele mudou de
# lugar em 17/09/2026, para `.github/`, e o caminho veio junto — o assert de
# existência abaixo é o que obriga essa lista a acompanhar a mudança em vez de
# passar a medir o vazio.
DOCUMENTOS = ("README.md", "CLAUDE.md", "pyproject.toml", ".github/CONTRIBUTING.md")

pytestmark = pytest.mark.politica


def enderecos_de(caminho: pathlib.Path):
    """(linha, dono, repo) de cada endereço de repositório do arquivo."""
    for numero, texto in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        for dono, repo in ENDERECO.findall(texto):
            yield numero, dono, repo


@pytest.mark.parametrize("nome", DOCUMENTOS)
def test_u1_toda_url_deste_projeto_tem_o_dono_certo(nome):
    """U1 — o teste que teria pego o `Castro1`."""
    arquivo = RAIZ / nome
    assert arquivo.is_file(), (
        f"{nome} sumiu. Se mudou de lugar, mova este teste junto: sem o arquivo "
        "ele passaria a medir o vazio."
    )

    erradas = [
        (linha, dono)
        for linha, dono, repo in enderecos_de(arquivo)
        if repo == REPO and dono != DONO
    ]
    assert not erradas, (
        f"{nome} manda baixar `{REPO}` de outro dono:\n  "
        + "\n  ".join(f"linha {l}: github.com/{d}/{REPO}" for l, d in erradas)
        + f"\nO dono é {DONO!r}. URL errada quebra a instalação e o erro que a "
        "pessoa vê é do git, que não sabe apontar para cá."
    )


def test_u2_o_readme_de_fato_manda_baixar_o_projeto():
    """U2 — anti-vácuo: U1 passaria num README que não cita o repositório.

    Ausência de URL deixaria o teste acima verde sem ter verificado nada, que é
    a forma de falso-verde que este projeto persegue desde o §9 de 28/08.
    """
    nossas = [
        (linha, dono)
        for linha, dono, repo in enderecos_de(RAIZ / "README.md")
        if repo == REPO
    ]
    assert len(nossas) >= 3, (
        "o README tem menos de três endereços deste repositório. Eram três em "
        f"14/09/2026 — o prompt do caminho rápido, o `pip install` e o `git "
        f"clone` —, e agora são {len(nossas)}. Se uma instrução saiu de "
        "propósito, baixe este número junto; se sumiu sozinha, é o bug."
    )


def test_u3_a_varredura_enxerga_as_duas_formas_e_o_dono_errado(tmp_path):
    """U3 — sabotagem controlada da própria varredura.

    Sem isto, um regex quebrado deixaria U1 verde sem achar endereço nenhum, e
    o teste que existe para pegar dono errado passaria justamente no caso que
    ele foi escrito para pegar.
    """
    falso = tmp_path / "x.md"
    falso.write_text(
        "clone https://github.com/CaioCastro1/mcp-usp.git aqui\n"
        "e git@github.com:Castro1/mcp-usp.git ali\n"
        "e https://github.com/loyaniu/moodle-mcp que é de outro projeto\n"
        'e Issues = "https://github.com/Castro1/mcp-usp/issues" no metadado\n',
        encoding="utf-8",
    )

    achados = list(enderecos_de(falso))
    assert (1, "CaioCastro1", "mcp-usp") in achados, "não pegou a forma https com .git"
    assert (2, "Castro1", "mcp-usp") in achados, "não pegou a forma ssh"
    assert (3, "loyaniu", "moodle-mcp") in achados, "não pegou repositório de terceiro"
    assert (4, "Castro1", "mcp-usp") in achados, (
        "não pegou o endereço com caminho depois do nome do repositório. É a "
        "forma do `Issues` do `[project.urls]`, e sem ela o dono errado ali "
        "passaria batido"
    )

    erradas = [(l, d) for l, d, r in achados if r == REPO and d != DONO]
    assert erradas == [(2, "Castro1"), (4, "Castro1")], (
        "a regra ou deixou passar o dono errado, ou reclamou de repositório de "
        f"terceiro: {erradas}"
    )
