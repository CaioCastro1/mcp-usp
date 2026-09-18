"""D1-D2: o README leva um clone limpo até o gate verde na ordem em que se lê.

Estes testes não olham código: olham a **ordem** das instruções. Existem porque
o primeiro comando que alguém novo roda neste repositório reprovava, e por um
motivo que a mensagem de erro não nomeava — o `./scripts/gate.sh` estava na
seção de instalação e o `cp .env.example .env` só aparecia na *Configuração*,
depois. Essa seção mudou de nome duas vezes em 14/09/2026: *Rodando* virou
*Instalando*, e depois o README foi reordenado para quem NÃO é técnico. Hoje
`## Instalando` é o caminho de quem só quer usar, e o fluxo que D1 e D2
descrevem mora em `## Rodando a partir do código`, que é a seção de quem mexe
no código e onde o gate vive.
Quem lê de cima para baixo levava um `FAILED` sobre `RUCARD_HASH` e nenhuma
pista de que faltava um passo que ainda nem tinha lido.

D3 é de 16/09/2026 e guarda o outro caminho, o de quem só usa. Até essa data o
caminho manual de `## Instalando` mandava `pip install git+...` num venv solto,
e isso põe o pacote em `site-packages`, onde `usp_mcp.env.achar_env` não acha
`.env` nenhum: o bandejão caía em `HashAusente` mandando copiar um
`.env.example` que a pessoa não tinha, e o token gravado pelo `token.sh` ficava
num clone que o servidor instalado nunca lia. D1 e D2 passavam verdes porque só
olham a outra seção. A cura foi o caminho manual clonar, criar o venv DENTRO do
clone e instalar editável, que é o layout que `env.py`, o `.mcp.json` e o
`servidor.sh` já suportam; D3 afirma os três passos pela string que se digita.

D4 é de 18/09/2026 e guarda o caminho rápido, que é a mensagem que a pessoa
cola no assistente. Até essa data era UMA mensagem, escrita num Mac para um Mac,
e ela quebrava em quatro lugares no Windows, três deles invisíveis para quem
cola: mandava rodar o `scripts/gate.sh`, que procura `.venv/bin/python`, caía no
`python3` da Microsoft Store e reprovava 58 testes (o dono do projeto viu o
assistente gastar sete minutos tentando entender se a quebra era real); apontava
para `.venv/bin/`, que no Windows é `.venv\Scripts\` com `.exe`; mandava rodar
`./scripts/token.sh` sem dizer que ali precisa do Git Bash; e terminava chamando
`diagnostico`, que exige a chave e toca a USP, no exato momento em que a chave é
o que falta. O gate, além disso, é ferramenta de pré-commit, e não tem o que
fazer num roteiro de instalação em sistema nenhum. A cura foi uma mensagem por
sistema, e a conferência virou o `--auto-verificar`, que é offline e não precisa
de chave. D4 afirma isso pelo texto: três blocos, cada um com o endereço do
repositório e o `--auto-verificar`, nenhum com gate, suíte ou `diagnostico`, e
os caminhos do sistema certo em cada um.

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
    contribuir = bloco("Rodando a partir do código")
    i_cura = contribuir.find(CURA)
    i_gate = contribuir.find("scripts/gate.sh")

    # As duas presenças são asserção própria, e não pressuposto: `find` devolve
    # -1 quando não acha, e -1 é menor que qualquer índice. Sem estas duas
    # linhas, um README que perdesse o `cp` passaria neste teste — o falso-verde
    # que o Invariante 6 proíbe, aqui na forma "comparei ausência com presença".
    assert i_cura != -1, (
        f"a seção Rodando a partir do código não traz {CURA!r}. Num clone limpo não existe `.env`, "
        "e sem ele o gate reprova falando de RUCARD_HASH — que não é o passo "
        "que faltou."
    )
    assert i_gate != -1, (
        "a seção Rodando a partir do código não chama mais o `scripts/gate.sh`. Se o gate saiu "
        "daqui, este teste está medindo outra coisa."
    )
    assert i_cura < i_gate, (
        "a seção Rodando a partir do código manda rodar o gate antes de criar o `.env`. Quem lê de "
        "cima para baixo reprova na primeira tentativa; a ordem no papel é a "
        "ordem em que os comandos são executados."
    )


def test_d2_o_readme_nao_manda_preencher_o_token_para_o_gate():
    contribuir = bloco("Rodando a partir do código")

    # Invariante 4: o token do Moodle é credencial pessoal. Um caminho de
    # "primeiros passos" que peça credencial para o commit passar transforma
    # colar segredo em pré-requisito de contribuir — e o gate é offline, não
    # precisa de token nenhum. O `.env.example` traz `MOODLE_TOKEN` vazio de
    # propósito, e D5 prova que vazio basta.
    assert "MOODLE_TOKEN" not in contribuir, (
        "a seção Rodando a partir do código pede o MOODLE_TOKEN. O gate roda offline e não toca a "
        "USP: exigir credencial pessoal aqui contraria o Invariante 4."
    )

    # E o token não pode simplesmente ter sumido do README para o teste acima
    # passar: ele continua sendo necessário para USAR o servidor do Moodle, e
    # esse lugar é a seção Configuração.
    assert "MOODLE_TOKEN" in bloco("Configuração"), (
        "o README parou de nomear a variável `MOODLE_TOKEN` na Configuração. "
        "Quem for de fato usar o Moodle precisa saber o nome dela."
    )


# Os comandos exatos do caminho manual, como se digitam. A ordem importa tanto
# quanto em D1: o `cp` tem de vir antes de o README dizer "Pronto".
CLONE = "git clone https://github.com/CaioCastro1/usp-mcp.git ~/usp-mcp"
INSTALACAO_EDITAVEL = "pip install -e ~/usp-mcp"
CURA_MANUAL = "cp ~/usp-mcp/.env.example ~/usp-mcp/.env"


def test_d3_o_caminho_manual_instala_dentro_do_clone_e_cria_o_env():
    instalando = bloco("Instalando")

    for passo in (CLONE, INSTALACAO_EDITAVEL, CURA_MANUAL):
        assert passo in instalando, (
            f"a seção Instalando não traz {passo!r}. O comando instalado só acha o "
            "`.env` se o pacote for instalado de dentro do clone (editável) e o "
            "`.env` for criado nesse clone; sem um dos três passos o bandejão cai "
            "em HashAusente e o token do `token.sh` nunca chega ao servidor."
        )

    # O layout que não funciona não pode voltar por engano: pacote em
    # `site-packages` não tem `.env` ao lado, e `achar_env` não procura em
    # mais lugar nenhum (decisão registrada no docstring de `usp_mcp/env.py`).
    assert "install git+" not in instalando, (
        "a seção Instalando voltou a instalar o pacote direto da URL do "
        "repositório, fora de um clone. Medido em 16/09/2026: nesse layout "
        "`achar_env()` devolve None e o bandejão não responde."
    )

    i_cura = instalando.find(CURA_MANUAL)
    i_pronto = instalando.find("Pronto:")
    assert i_pronto != -1, "a seção Instalando não diz mais 'Pronto:'; o teste mediria o vazio"
    assert i_cura < i_pronto, (
        "o README diz 'Pronto' antes de mandar criar o `.env`. Quem lê de cima "
        "para baixo abre o assistente sem a hash do bandejão."
    )


# A conferência que funciona sem chave e sem rede, nos três servidores, como se
# digita. É por `python -m` de propósito: o comando instalado (`usp-mcp-rucard`)
# ignora o argumento e sai com 0 sem imprimir nada, medido em 18/09/2026.
VERIFICACAO = "--auto-verificar"
REPOSITORIO = "https://github.com/CaioCastro1/usp-mcp"
# O que foi aprendido com uso e não pode sair da mensagem.
UM_PASSO = "UM PASSO POR MENSAGEM"
# Ferramenta de quem mantém, e a chamada que exige a chave: nenhuma entra no
# roteiro de instalação. `pytest` cobre "rode a suíte" em qualquer forma.
PROIBIDOS = ("gate.sh", "pytest", "diagnostico")


def prompts_do_caminho_rapido() -> dict[str, str]:
    """Os blocos ```text da subseção *O caminho rápido*, por sistema."""
    instalando = bloco("Instalando")
    inicio = instalando.find("### O caminho rápido")
    fim = instalando.find("### O caminho manual")
    assert inicio != -1 and fim != -1 and inicio < fim, (
        "a seção Instalando perdeu *O caminho rápido* ou *O caminho manual*, ou "
        "trocou a ordem. Se a estrutura mudou, este teste precisa saber."
    )
    rapido = instalando[inicio:fim]

    prompts: dict[str, str] = {}
    for sistema in ("Mac", "Windows", "Linux"):
        marca = f"#### No {sistema}\n"
        i = rapido.find(marca)
        assert i != -1, (
            f"o caminho rápido não tem mais a subseção `#### No {sistema}`. Uma "
            "mensagem só, com 'se você estiver no Windows faça assim', é o que "
            "quebrava: o assistente escolhia errado e a pessoa não percebia."
        )
        i_abre = rapido.find("```text\n", i)
        i_fecha = rapido.find("\n```\n", i_abre + 1)
        assert i_abre != -1 and i_fecha != -1, f"a subseção {sistema} não tem um bloco ```text"
        prompts[sistema] = rapido[i_abre + len("```text\n") : i_fecha]
    return prompts


def test_d4_o_caminho_rapido_tem_um_prompt_por_sistema_e_confere_sem_chave():
    prompts = prompts_do_caminho_rapido()

    for sistema, prompt in prompts.items():
        assert REPOSITORIO in prompt, (
            f"o prompt do {sistema} não diz de onde clonar. Sem o endereço o "
            "assistente adivinha, e é o mesmo bug do `Castro1` de 14/09 por outro caminho."
        )
        assert VERIFICACAO in prompt, (
            f"o prompt do {sistema} não confere a instalação com `{VERIFICACAO}`. "
            "É a única conferência que roda sem chave e sem rede nos três sistemas."
        )
        # ` -m usp_mcp.` e não `python -m`: no Windows o interpretador é `python.exe`.
        assert " -m usp_mcp." in prompt, (
            f"o prompt do {sistema} roda o `{VERIFICACAO}` sem `python -m`. Pelo "
            "comando instalado o argumento é ignorado e a saída é 0 sem texto: um "
            "verde que não conferiu nada."
        )
        assert UM_PASSO in prompt, (
            f"o prompt do {sistema} perdeu o '{UM_PASSO}' do passo da chave. Foi "
            "aprendido com uso: a lista inteira de uma vez ninguém lê."
        )
        assert "token.sh" in prompt, f"o prompt do {sistema} não obtém a chave do e-Disciplinas."
        for proibido in PROIBIDOS:
            assert proibido not in prompt, (
                f"o prompt do {sistema} cita `{proibido}`. Gate e suíte são de quem "
                "mantém o projeto, e `diagnostico` exige a chave que a instalação "
                "ainda não tem: nenhum dos três confere uma instalação."
            )

    # Os caminhos são do sistema certo, e não do sistema em que o README foi escrito.
    assert "Scripts" in prompts["Windows"] and ".exe" in prompts["Windows"], (
        "o prompt do Windows não fala de `Scripts` nem de `.exe`: é o venv do Mac "
        "de novo, e lá `.venv/bin/` não existe."
    )
    assert ".venv/bin" not in prompts["Windows"], (
        "o prompt do Windows aponta para `.venv/bin`. No Windows essa pasta não existe."
    )
    assert "Git Bash" in prompts["Windows"], (
        "o prompt do Windows não diz que o `token.sh` roda no Git Bash. No "
        "PowerShell ele não roda, e o assistente não tem como saber sozinho."
    )
    for sistema in ("Mac", "Linux"):
        assert ".venv/bin" in prompts[sistema], f"o prompt do {sistema} não aponta para `.venv/bin`."
        assert "Scripts" not in prompts[sistema], (
            f"o prompt do {sistema} fala de `Scripts`, que é a pasta do Windows."
        )
