"""D1-D2: o README leva um clone limpo até o gate verde na ordem em que se lê.

Estes testes não olham código: olham a **ordem** das instruções. Existem porque
o primeiro comando que alguém novo roda neste repositório reprovava, e por um
motivo que a mensagem de erro não nomeava — o `./scripts/gate.sh` estava na
seção de instalação e o `cp .env.example .env` só aparecia na *Configuração*,
depois. Essa seção mudou de nome duas vezes em 14/09/2026: *Rodando* virou
*Instalando*, e depois o README foi reordenado para quem NÃO é técnico. Hoje
`## Instalando` é o caminho de quem só quer usar (dois comandos, sem clone e sem
gate), e o fluxo que estes testes descrevem mora em `## Mexer no código`. É lá
que eles olham.
Quem lê de cima para baixo levava um `FAILED` sobre `RUCARD_HASH` e nenhuma
pista de que faltava um passo que ainda nem tinha lido.

Documento também envelhece calado (é a lição do §9 de 31/08 sobre estado em
`CLAUDE.md`/`README.md`): a diferença aqui é que a ordem errada volta a doer em
toda pessoa nova, e não só na próxima sessão de IA.

Sem marcador: não são allowlist (`politica`) nem forma contra fixture
(`contrato`). São offline, puros e custam um `read_text` — entram no gate junto
com o resto.
"""
from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"

# O comando exato, como se digita. Comparar a string que a pessoa copia — e não
# uma paráfrase tipo "menciona o .env" — é o que impede este teste de passar com
# um README que fala do assunto sem dar o comando.
CURA = "cp .env.example .env"


def bloco(titulo: str) -> str:
    """O corpo de uma seção `## <titulo>` do README, até a próxima `## `."""
    texto = README.read_text(encoding="utf-8")
    marca = f"\n## {titulo}\n"
    inicio = texto.find(marca)
    assert inicio != -1, (
        f"o README não tem mais a seção {titulo!r}. Se ela foi renomeada, este "
        "teste precisa saber: caso contrário ele passaria a medir o vazio."
    )
    inicio += len(marca)
    fim = texto.find("\n## ", inicio)
    return texto[inicio : fim if fim != -1 else len(texto)]


def test_d1_o_readme_manda_criar_o_env_antes_do_gate():
    contribuir = bloco("Mexer no código")
    i_cura = contribuir.find(CURA)
    i_gate = contribuir.find("scripts/gate.sh")

    # As duas presenças são asserção própria, e não pressuposto: `find` devolve
    # -1 quando não acha, e -1 é menor que qualquer índice. Sem estas duas
    # linhas, um README que perdesse o `cp` passaria neste teste — o falso-verde
    # que o Invariante 6 proíbe, aqui na forma "comparei ausência com presença".
    assert i_cura != -1, (
        f"a seção Mexer no código não traz {CURA!r}. Num clone limpo não existe `.env`, "
        "e sem ele o gate reprova falando de RUCARD_HASH — que não é o passo "
        "que faltou."
    )
    assert i_gate != -1, (
        "a seção Mexer no código não chama mais o `scripts/gate.sh`. Se o gate saiu "
        "daqui, este teste está medindo outra coisa."
    )
    assert i_cura < i_gate, (
        "a seção Mexer no código manda rodar o gate antes de criar o `.env`. Quem lê de "
        "cima para baixo reprova na primeira tentativa; a ordem no papel é a "
        "ordem em que os comandos são executados."
    )


def test_d2_o_readme_nao_manda_preencher_o_token_para_o_gate():
    contribuir = bloco("Mexer no código")

    # Invariante 4: o token do Moodle é credencial pessoal. Um caminho de
    # "primeiros passos" que peça credencial para o commit passar transforma
    # colar segredo em pré-requisito de contribuir — e o gate é offline, não
    # precisa de token nenhum. O `.env.example` traz `MOODLE_TOKEN` vazio de
    # propósito, e D5 prova que vazio basta.
    assert "MOODLE_TOKEN" not in contribuir, (
        "a seção Mexer no código pede o MOODLE_TOKEN. O gate roda offline e não toca a "
        "USP: exigir credencial pessoal aqui contraria o Invariante 4."
    )

    # E o token não pode simplesmente ter sumido do README para o teste acima
    # passar: ele continua sendo necessário para USAR o servidor do Moodle, e
    # esse lugar é a seção Configuração.
    assert "MOODLE_TOKEN" in bloco("Configuração"), (
        "o README parou de nomear a variável `MOODLE_TOKEN` na Configuração. "
        "Quem for de fato usar o Moodle precisa saber o nome dela."
    )
