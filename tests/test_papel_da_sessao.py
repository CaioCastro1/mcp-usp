"""PS1-PS5: o repositório diz, a quem o abre, se a sessão é de uso ou de manutenção.

Estes testes não olham código: olham o que os documentos **supõem** sobre quem
está do outro lado. Existem por um defeito observado em uso real — um amigo do
dono clonou o repositório, abriu o assistente, e o assistente se comportou como
mantenedor: tratou o projeto como dele, propôs mexer no código, propôs abrir PR,
propôs rever decisão. A pessoa queria saber o que tem no bandejão.

O assistente não inventou nada. Ele leu um `CLAUDE.md` que abria dizendo ser "o
cérebro compartilhado de todas as sessões de IA" e que "toda comunicação com o
Caio é em português", escrito quando só existiam duas pessoas no projeto, as duas
mantenedoras. Em 17/09/2026 o repositório ficou público e essa suposição deixou
de valer para a maioria de quem chega.

O desenho está em
`docs/superpowers/specs/2026-09-17-usuario-nao-e-mantenedor-design.md`, e o que
ele descobriu e estes testes guardam é que **nenhum sinal de disco distingue os
dois papéis**: `.env` preenchido e `origin` apontando para o repositório do dono
são o que todo clone tem, e worktree/branch/`fixtures/moodle/raw/` só sabem
confirmar manutenção, nunca negá-la. Por isso o padrão é assumido e não detectado.

PS5 é a que mais importa, e é a única que reprova se esta mudança virar cerca: o
README convida a contribuir, e esse convite não pode ter sido fechado por um
documento que existe para proteger quem só quer usar.

Sem marcador: não são allowlist (`politica`) nem forma contra fixture
(`contrato`). São offline, puros, custam um `read_text` por arquivo — entram no
gate junto com o resto, pelo mesmo desenho do `tests/test_documentacao.py`.
"""
from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]

CLAUDE = RAIZ / "CLAUDE.md"
PAPEL = RAIZ / "docs" / "agents" / "PAPEL-DA-SESSAO.md"
CONVENTIONS = RAIZ / "docs" / "agents" / "CONVENTIONS.md"
CONTRIBUTING = RAIZ / ".github" / "CONTRIBUTING.md"
README = RAIZ / "README.md"

# O caminho como se escreve num ponteiro. Comparar a string que alguém digitaria
# — e não uma paráfrase tipo "o CLAUDE.md fala de papel" — é o que impede este
# arquivo de passar com um documento que trata do assunto sem levar a lugar nenhum.
PONTEIRO = "docs/agents/PAPEL-DA-SESSAO.md"


def test_ps1_o_claude_md_declara_o_papel_antes_do_produto():
    """PS1 — a ordem no papel é a ordem em que se lê.

    A seção de papel muda o sentido de tudo que vem depois: o §5 descreve branch
    → PR → merge, e sem o §0 esse fluxo lê-se como o destino natural de toda
    sessão. Declarar o papel no fim do arquivo seria declarar tarde.
    """
    texto = CLAUDE.read_text(encoding="utf-8")

    i_papel = texto.find("\n## 0. Quem abriu esta pasta\n")
    i_produto = texto.find("\n## 1. O produto")

    assert i_papel != -1, (
        "o `CLAUDE.md` não tem mais a seção `## 0. Quem abriu esta pasta`. Sem "
        "ela, todo assistente que abre a pasta conclui que está numa sessão de "
        "manutenção — que foi o defeito observado em 17/09/2026."
    )
    assert i_produto != -1, (
        "o `CLAUDE.md` não tem mais a seção `## 1. O produto`; este teste "
        "passaria a medir o vazio em vez de medir ordem."
    )
    assert i_papel < i_produto, (
        "o `CLAUDE.md` fala do produto antes de dizer para quem está falando. "
        "Quem lê de cima para baixo já escolheu o papel errado quando chega ao §0."
    )


def test_ps2_o_claude_md_aponta_para_o_detalhe_e_o_detalhe_existe():
    """PS2 — ponteiro morto é pior que ausência.

    O `CLAUDE.md` é curto e sem estado por regra que já custou dois dias de
    sessão com o mapa errado, então o detalhe desce um nível. Isso só funciona se
    o nível de baixo existir.
    """
    assert PONTEIRO in CLAUDE.read_text(encoding="utf-8"), (
        f"o `CLAUDE.md` não cita mais {PONTEIRO!r}. O §0 é o padrão e o gatilho; "
        "o detalhe (que sinal serve, o que fazer de cada lado) mora no arquivo "
        "apontado, e sem o ponteiro ninguém o encontra."
    )
    assert PAPEL.is_file(), (
        f"{PONTEIRO} sumiu. Se mudou de lugar, mova o ponteiro do `CLAUDE.md` e "
        "este teste junto: um ponteiro que não resolve é pior que nenhum, "
        "porque promete uma resposta que não existe."
    )


def test_ps3_o_detalhe_diz_quais_sinais_nao_servem():
    """PS3 — a parte mais fácil de apagar é a que carrega o achado.

    "Como sei se sou mantenedor?" tem três respostas intuitivas e as três estão
    erradas. Uma revisão de estilo que enxugue o arquivo corta justamente esta
    tabela, porque ela é a parte que fala do que NÃO fazer — e o defeito volta
    pelo caminho do meio, trocando "todo mundo é mantenedor" por "quem tem push
    é mantenedor".
    """
    texto = PAPEL.read_text(encoding="utf-8")

    for sinal, porque in (
        (".env", "todo clone que seguiu a Configuração do README tem um, e é o passo de quem USA"),
        ("origin", "é o que `git clone` escreve em todo clone, o do dono e o de quem só usa"),
        ("push", "o papel é da sessão e não da pessoa: o dono também pergunta do bandejão"),
    ):
        assert sinal in texto, (
            f"{PONTEIRO} parou de nomear {sinal!r} entre os sinais que não "
            f"servem. Ele não serve porque {porque}."
        )

    # E o arquivo não pode ter virado uma lista só de negativas: os três sinais
    # que de fato confirmam manutenção continuam nomeados, senão sobra um
    # documento que diz como não decidir e não diz como decidir.
    for sinal in ("worktree", "fixtures/moodle/raw/"):
        assert sinal in texto, (
            f"{PONTEIRO} parou de nomear {sinal!r}, que é um dos sinais que "
            "CONFIRMAM manutenção. Sem eles o arquivo só sabe dizer não."
        )


def test_ps4_o_conventions_declara_para_quem_e():
    """PS4 — o segundo empurrão para o papel errado, depois do `CLAUDE.md`.

    A pasta se chama `agents/`, o que um assistente lê como "isto é para mim", e
    o conteúdo é inteiro de manutenção. O `.github/CONTRIBUTING.md` já registrava
    que o nome engana quem chega; aqui isso vira declaração no próprio arquivo.
    """
    texto = CONVENTIONS.read_text(encoding="utf-8")
    cabecalho = texto[: texto.find("\n## ")]

    assert "MANUTENÇÃO" in cabecalho, (
        "o `CONVENTIONS.md` não diz mais, antes da primeira seção, que é de "
        "sessão de manutenção. Ele fala de gate, commit, merge e sigla de teste: "
        "entregá-lo a uma sessão de uso é entregar o material que produziu o "
        "defeito de 17/09/2026."
    )
    assert PONTEIRO.rsplit("/", 1)[-1] in cabecalho, (
        "o cabeçalho do `CONVENTIONS.md` não manda mais quem só usa para o "
        "`PAPEL-DA-SESSAO.md`. Dizer 'isto não é para você' sem dizer o que é "
        "deixa a pessoa no mesmo lugar."
    )


def test_ps5_a_valvula_existe_e_o_convite_continua_aberto():
    """PS5 — o anti-cerca, e a asserção que reprova se isto virar portão.

    Um padrão que ninguém sabe trocar é uma cerca com outro nome. As três metades
    desta afirmação vivem em três arquivos, de propósito: o assistente lê o
    `CLAUDE.md`, quem vai contribuir lê o `CONTRIBUTING.md`, e quem chega lê o
    README.
    """
    assert "basta pedir" in CLAUDE.read_text(encoding="utf-8"), (
        "o §0 do `CLAUDE.md` não diz mais que basta pedir para a sessão virar de "
        "manutenção. Sem essa frase o §0 deixa de ser um padrão e vira uma "
        "recusa, e o defeito que ele conserta é trocado por outro pior."
    )

    contribuindo = CONTRIBUTING.read_text(encoding="utf-8")
    assert PONTEIRO in contribuindo and "contribuir" in contribuindo, (
        "o `.github/CONTRIBUTING.md` não avisa mais quem veio contribuir de que "
        "o padrão é uso e como trocá-lo. É ele que quem abre PR lê primeiro."
    )

    readme = README.read_text(encoding="utf-8")
    assert "abra uma issue" in readme and "antes da PR" in readme, (
        "o README parou de convidar a abrir issue ou a acertar uma PR. O convite "
        "é anterior a esta mudança e ela não existe para fechá-lo: o §0 diz de "
        "onde a sessão parte, não o que ela pode."
    )
