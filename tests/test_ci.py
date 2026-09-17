"""C1-C9: o CI roda a camada offline, e só ela, sem credencial nenhuma.

O `scripts/gate.sh` já checa tudo o que precisa ser checado antes de um commit.
O defeito nunca foi o que ele checa — é que ele só roda quando alguém lembra.
Uma action fecha essa porta, e abre três outras que estes testes trancam:

1. **Ligar a camada `live` no CI.** Ela fala com a USP de verdade, com o token
   pessoal do dono, e cada chamada fica no log da conta. Um CI que depende de a
   USP estar de pé reprova uma PR por motivo que não é da PR — e o dado da
   `live` não é do CI para gastar. Por isso ela fica atrás de uma variável de
   ambiente, e por isso C3 reprova qualquer workflow que ligue essa variável.
2. **Levar credencial para dentro do runner.** Credencial pessoal não sai da
   máquina do dono, nem "só pra testar", nem guardada no cofre do GitHub. C4
   reprova o NOME do token do Moodle, o cofre de segredos do próprio GitHub e
   qualquer valor com forma de chave — e reprova no arquivo inteiro, comentário
   incluído: um segredo citado "só para explicar" continua sendo um segredo
   escrito num arquivo rastreado.
3. **Desligar a suíte de dentro do CI.** O `gate.sh` tem uma variável que pula a
   checagem 3, e ela existe por um motivo estreito e só ele: o
   `tests/test_gate.py` roda o gate dentro de um clone deste repositório, e sem
   o pulo a suíte do clone rodaria o teste que clona de novo. Num workflow ela
   não tem uso legítimo nenhum: o CI passaria a rodar um gate que checa `.env` e
   `.gitignore` e chama isso de verde, que é o falso-verde mais caro possível,
   porque é o único que ninguém precisa lembrar de rodar. C9 reprova qualquer
   workflow que a ligue.

C3, C4 e C9 seriam verdes num diretório `.github/` vazio, que é o falso-verde que
este repositório persegue desde o primeiro gate. C1, C2, C5 e C6 são o
contrapeso: existe workflow, ele dispara em push e em pull request, ele de fato
instala o pacote e roda a camada offline, e ele cria o `.env` antes disso. C8
guarda a terceira porta, que só apareceu quando o CI rodou pela primeira vez: o
sistema do runner.

O `.env` de C6 não é detalhe de implementação: sem ele a suíte offline reprova
com `RUCARD_HASH não está no ambiente nem no .env`, que é consequência e não
causa. O `docs/superpowers/specs/2026-09-10-gate-em-clone-limpo-design.md`
mediu isso num clone limpo e a cura cabe numa linha — `cp .env.example .env` —
porque a hash do RUCard é a chave pública embutida no app oficial, não
credencial de ninguém. É o mesmo passo que o README manda dar, e é por isso que
o CI pode rodar o gate inteiro em vez de só o pytest.

Sem marcador, como o `test_documentacao.py`: não são allowlist nem forma contra
fixture. Custam um `read_text` por arquivo e entram no gate junto com o resto.
"""
from __future__ import annotations

import os
import pathlib
import re

import pytest

try:  # o extra `dev` traz; um ambiente sem ele faz C10 pular DIZENDO isso.
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

RAIZ = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = RAIZ / ".github" / "workflows"

# A variável que liga a camada que fala com a USP. Escrita à mão aqui, e não
# importada de `usp_mcp`, porque é justamente o nome que não pode aparecer ligado
# no YAML: derivar do código faria o teste concordar com uma renomeação em vez de
# reprovar por ela.
VARIAVEL_LIVE = "USP_MCP_LIVE"

# A variável que faz o `gate.sh` PULAR a suíte. Mesma razão de estar escrita à
# mão: é o nome que não pode aparecer ligado num workflow.
VARIAVEL_SEM_SUITE = "USP_MCP_GATE_SEM_SUITE"

# Valores que NÃO ligam a camada: vazio (a forma que o próprio gate usa para
# limpar a variável antes do pytest) e zero.
_DESLIGADO = ("", '""', "''", "0", '"0"', "'0'")

# Nome de credencial e forma de credencial, nesta ordem. `secrets.` pega o cofre
# do GitHub inteiro, inclusive o `GITHUB_TOKEN` automático: este CI lê código
# público e roda teste offline, e não tem o que fazer com nenhum deles.
PALAVRAS_DE_SEGREDO = ("MOODLE_TOKEN", "wstoken", "secrets.")

# Trinta e dois hexadecimais seguidos: a forma do token do web service e a da
# hash do RUCard. Pega valor colado no YAML mesmo com nome de variável inventado
# na hora, que é o vazamento que uma lista de nomes nunca alcança.
FORMA_DE_CHAVE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])")

# Comentário de YAML: `#` no começo da linha ou depois de espaço, até o fim.
_COMENTARIO = re.compile(r"(?:^|(?<=\s))#.*$")

# O comando que cria o `.env`, idêntico ao que o README manda dar e ao que a
# mensagem de falha do gate cita. Três cópias da mesma string em três lugares é
# de propósito: é ela que amarra o CI ao passo do README.
CURA = "cp .env.example .env"

# Como se roda a camada offline. Qualquer um dos dois serve para C5/C6: o teste
# tranca que ela ROLE, não por qual porta.
COMANDOS_OFFLINE = ("scripts/gate.sh", "pytest")


def workflows() -> list[pathlib.Path]:
    """Todo arquivo de workflow, nas duas extensões que o GitHub aceita."""
    if not WORKFLOWS.is_dir():
        return []
    return sorted(p for p in WORKFLOWS.iterdir() if p.suffix in (".yml", ".yaml"))


def sem_comentarios(texto: str) -> str:
    """O YAML sem os comentários — o que a action de fato executa.

    C3 olha por aqui porque comentário que EXPLICA a variável da camada live é o
    que se quer no arquivo, e não o que se quer proibir. C4 olha o texto cru, e
    a diferença é deliberada: explicar não é vazar, mas um segredo citado em
    comentário está tão escrito quanto um em `env:`.
    """
    return "\n".join(_COMENTARIO.sub("", linha) for linha in texto.splitlines())


def liga_a_variavel(texto: str, variavel: str) -> list[tuple[int, str]]:
    """(linha, trecho) de cada atribuição que LIGA `variavel` no YAML.

    Uma varredura só para as duas variáveis proibidas, e não duas cópias: as
    formas que ela precisa pegar são as mesmas (`VAR: 1` no bloco `env:` e
    `VAR=1` na linha de comando), e duas implementações da mesma pergunta é o
    preço que este repositório já pagou três vezes (§9, 12/09/2026).
    """
    achados = []
    padrao = re.compile(rf"{variavel}\s*[:=]\s*(\S*)")
    for numero, linha in enumerate(sem_comentarios(texto).splitlines(), 1):
        for valor in padrao.findall(linha):
            if valor not in _DESLIGADO:
                achados.append((numero, linha.strip()))
    return achados


def liga_a_camada_live(texto: str) -> list[tuple[int, str]]:
    """(linha, trecho) de cada atribuição que LIGA a camada live."""
    return liga_a_variavel(texto, VARIAVEL_LIVE)


def desliga_a_suite(texto: str) -> list[tuple[int, str]]:
    """(linha, trecho) de cada atribuição que faz o gate PULAR a suíte."""
    return liga_a_variavel(texto, VARIAVEL_SEM_SUITE)


def segredos_em(texto: str) -> list[tuple[int, str]]:
    """(linha, o que apareceu) de cada segredo — por nome ou por forma."""
    achados = []
    for numero, linha in enumerate(texto.splitlines(), 1):
        for palavra in PALAVRAS_DE_SEGREDO:
            if palavra in linha:
                achados.append((numero, palavra))
        if FORMA_DE_CHAVE.search(linha):
            achados.append((numero, "valor com forma de chave (32 hex)"))
    return achados


def _indice(texto: str, agulha: str) -> int:
    """Posição da primeira ocorrência, ou -1. Ordem, como o D1/D3 fazem."""
    return texto.find(agulha)


def test_c1_existe_workflow_de_ci():
    """C1 — o item de roadmap é "não tem CI"; começa por aqui."""
    assert workflows(), (
        "não há workflow nenhum em .github/workflows/. O gate é melhor que o CI "
        "dos comparáveis e mesmo assim só roda quando alguém lembra — crie um "
        "arquivo .yml lá que rode a camada offline em push e em pull request."
    )


@pytest.mark.parametrize("arquivo", [p.name for p in workflows()])
def test_c2_o_ci_dispara_em_push_e_em_pull_request(arquivo):
    """C2 — um workflow que só roda à mão tem o mesmo defeito do gate."""
    texto = sem_comentarios((WORKFLOWS / arquivo).read_text(encoding="utf-8"))
    cabeca = texto.split("jobs:")[0]
    faltando = [g for g in ("push:", "pull_request:") if g not in cabeca]
    assert not faltando, (
        f"{arquivo} não dispara em {', '.join(faltando)}. Declare os dois no "
        "bloco `on:`: rodar só em push deixa a PR de um fork sem checagem, e "
        "rodar só em pull request deixa a branch principal sem nenhuma."
    )


@pytest.mark.parametrize("arquivo", [p.name for p in workflows()])
def test_c3_nenhum_workflow_liga_a_camada_live(arquivo):
    """C3 — o erro que o item de roadmap nomeia, travado."""
    achados = liga_a_camada_live((WORKFLOWS / arquivo).read_text(encoding="utf-8"))
    assert not achados, (
        f"{arquivo} liga a camada que fala com a USP de verdade:\n  "
        + "\n  ".join(f"linha {l}: {t}" for l, t in achados)
        + f"\nTire a atribuição de {VARIAVEL_LIVE} do workflow. Essa camada "
        "precisa de rede da USP e do token pessoal do dono, e cada chamada fica "
        "no log da conta dele: no CI ela reprovaria a PR por um motivo que não "
        "é da PR. O canário da live se roda à mão, na máquina do dono."
    )


@pytest.mark.parametrize("arquivo", [p.name for p in workflows()])
def test_c4_nenhum_workflow_menciona_segredo(arquivo):
    """C4 — nem o nome, nem o cofre do GitHub, nem um valor com forma de chave."""
    achados = segredos_em((WORKFLOWS / arquivo).read_text(encoding="utf-8"))
    assert not achados, (
        f"{arquivo} traz credencial para dentro do runner:\n  "
        + "\n  ".join(f"linha {l}: {t}" for l, t in achados)
        + "\nTire do arquivo. Este CI roda a camada offline, que não autentica "
        "em nada: não precisa de cofre, de token do Moodle nem de chave "
        "colada. Credencial pessoal não sai da máquina do dono, e o que o "
        "workflow precisa do ambiente sai do `.env.example`, que é público e "
        "já está no repositório."
    )


@pytest.mark.parametrize("arquivo", [p.name for p in workflows()])
def test_c9_nenhum_workflow_desliga_a_suite_do_gate(arquivo):
    """C9: a porta de escape do `gate.sh` não pode ser aberta pelo CI.

    C5 garante que o workflow CHAMA o gate. Sem C9, chamar o gate com esta
    variável ligada satisfaria C5 e devolveria verde tendo checado o `.env` e o
    `.gitignore`, e nada do código que a PR mudou. O gate imprime PULADA e sai
    com código próprio, mas a linha some no meio do log de um runner, e o único
    leitor que sobra é o `&&` implícito entre os passos.
    """
    achados = desliga_a_suite((WORKFLOWS / arquivo).read_text(encoding="utf-8"))
    assert not achados, (
        f"{arquivo} desliga a suíte do gate:\n  "
        + "\n  ".join(f"linha {l}: {t}" for l, t in achados)
        + f"\nTire a atribuição de {VARIAVEL_SEM_SUITE} do workflow. Ela existe "
        "por um motivo só: o `tests/test_gate.py` roda o gate dentro de um "
        "clone deste repositório, e sem ela a suíte do clone recorreria sobre "
        "si mesma. Num runner não há recursão nenhuma a evitar: o que ela faz "
        "é transformar o CI num carimbo que não leu o código."
    )


def test_c5_o_ci_de_fato_instala_e_roda_a_camada_offline():
    """C5 — anti-vácuo: C3 e C4 passariam num workflow que não roda nada.

    É a mesma trava do U2: uma varredura que não acha nada fica verde sem ter
    verificado nada, e aqui o "nada" seria um CI decorativo.
    """
    textos = {p.name: sem_comentarios(p.read_text(encoding="utf-8")) for p in workflows()}

    rodam = {
        nome: [c for c in COMANDOS_OFFLINE if c in texto] for nome, texto in textos.items()
    }
    assert any(rodam.values()), (
        "nenhum workflow roda a camada offline. Achei "
        f"{list(textos) or 'nenhum arquivo'} e em nenhum deles aparece "
        f"{' nem '.join(COMANDOS_OFFLINE)}. Um CI que não roda a suíte é "
        "decoração: ele fica verde sem ter checado nada."
    )

    instalam = [nome for nome, texto in textos.items() if "pip install -e" in texto]
    assert instalam, (
        "nenhum workflow instala o pacote com `pip install -e \".[dev]\"`. Sem "
        "a instalação editável não existem os três comandos em .venv/bin/ que "
        "o tests/test_pacote.py exige, e ele passa a PULAR — o CI ficaria verde "
        "justamente sobre o que o pacote promete."
    )


@pytest.mark.parametrize("arquivo", [p.name for p in workflows()])
def test_c6_o_ci_cria_o_env_antes_de_rodar_a_suite(arquivo):
    """C6 — o clone limpo do CI é o mesmo clone limpo que o spec mediu.

    O runner clona o repositório do zero, e o `.env` é gitignorado: ele não vem
    junto, exatamente como no clone de quem acabou de chegar. Sem ele a suíte
    reprova falando de `RUCARD_HASH`, que é o sintoma registrado no spec de
    10/09/2026. A cura é a mesma linha do README, e vem antes.
    """
    texto = sem_comentarios((WORKFLOWS / arquivo).read_text(encoding="utf-8"))

    offline = [_indice(texto, c) for c in COMANDOS_OFFLINE if _indice(texto, c) != -1]
    if not offline:
        pytest.skip(f"{arquivo} não roda a camada offline — C5 cobre o conjunto")

    env = _indice(texto, CURA)
    assert env != -1, (
        f"{arquivo} roda a suíte sem criar o `.env`. O runner clona limpo e o "
        f"`.env` é gitignorado, então acrescente `{CURA}` antes: sem isso a "
        "suíte reprova falando de RUCARD_HASH, que é consequência e não causa. "
        "A hash do RUCard já vem preenchida no exemplo e é pública — o token "
        "pessoal continua vazio, e a camada offline não o usa."
    )
    assert env < min(offline), (
        f"{arquivo} cria o `.env` DEPOIS de rodar a suíte. Mova `{CURA}` para "
        "antes: na ordem atual a suíte roda sem ambiente e reprova sem ter "
        "chegado ao que a PR mudou."
    )


@pytest.mark.parametrize("arquivo", [p.name for p in workflows()])
def test_c8_o_ci_roda_onde_o_projeto_roda(arquivo):
    """C8 — a escolha do sistema do runner não pode envelhecer calada.

    Escrita à mão aqui, como o dono do repositório no U1: se um dia a decisão
    mudar, este teste reprova e obriga a mudança a ser declarada, em vez de
    virar um vermelho misterioso numa PR que não tem nada com isso.
    """
    texto = sem_comentarios((WORKFLOWS / arquivo).read_text(encoding="utf-8"))
    assert re.search(r"runs-on:\s*ubuntu", texto), (
        f"{arquivo} não roda em Linux. A escolha mudou em 16/09/2026 e tem "
        "razão medida: o runner era macOS porque o `test_g3` quebrava em ext4, "
        "e custava 10x o minuto num repositório privado. Hoje o `test_g3` "
        "detecta o sistema de arquivos e pula declarando o motivo, então o "
        "flanco que sobra é conhecido e não silencioso: o BUG-2 só é "
        "exercitado em sistema insensível a normalização, isto é, na máquina "
        "de quem desenvolve, pelo gate local. Se um dia voltar para macOS, que "
        "volte declarado aqui e não por acidente numa PR de outro assunto."
    )


def test_c7_as_varreduras_pegam_o_que_existem_para_pegar(tmp_path):
    """C7: sabotagem controlada das três varreduras.

    Sem isto, um regex quebrado deixaria C3, C4 e C9 verdes em cima de um
    workflow que liga a camada live, carrega o cofre de segredos e desliga a
    suíte junto. São os casos exatos para os quais estes testes foram escritos.
    """
    sujo = (
        "env:\n"
        f"  {VARIAVEL_LIVE}: 1\n"
        f"  TOKEN: ${{{{ secrets.MOODLE_TOKEN }}}}\n"
        # Hexadecimal inventado, e não a hash real do RUCard: o valor real está
        # no `.env`, e a checagem 1 do gate reprova qualquer arquivo rastreado
        # que o contenha — inclusive um teste que o usasse como exemplo.
        "  HASH: 0123456789abcdef0123456789abcdef\n"
        f"# comentário explicando por que {VARIAVEL_LIVE}=1 não entra aqui\n"
        "run: |\n"
        f"  {VARIAVEL_LIVE}=1 pytest -m live\n"
        # Depois das linhas acima, e não no meio delas: as asserções de C7
        # citam número de linha, e inserir no meio faria este teste reprovar
        # por uma edição que não mudou varredura nenhuma.
        f"  {VARIAVEL_SEM_SUITE}=1 ./scripts/gate.sh\n"
    )
    arquivo = tmp_path / "sujo.yml"
    arquivo.write_text(sujo, encoding="utf-8")
    texto = arquivo.read_text(encoding="utf-8")

    ligadas = [linha for linha, _ in liga_a_camada_live(texto)]
    assert ligadas == [2, 7], (
        "a varredura da camada live não pegou as duas formas (`VAR: 1` no bloco "
        f"`env:` e `VAR=1` na linha de comando), ou contou o comentário: {ligadas}"
    )

    desligadas = [linha for linha, _ in desliga_a_suite(texto)]
    assert desligadas == [8], (
        "a varredura do pulo da suíte não pegou a linha que desliga a checagem "
        f"3 do gate: {desligadas}"
    )

    achados = segredos_em(texto)
    assert (3, "MOODLE_TOKEN") in achados, "não pegou o nome do token"
    assert (3, "secrets.") in achados, "não pegou o cofre do GitHub"
    assert (4, "valor com forma de chave (32 hex)") in achados, (
        "não pegou um valor de 32 hexadecimais colado no YAML"
    )

    # E o contrário: um workflow limpo não pode acusar nada, senão a regra vira
    # ruído e a próxima pessoa a desliga em vez de ler.
    limpo = (
        "on:\n  push:\n  pull_request:\n"
        "jobs:\n  offline:\n    steps:\n"
        f"      - run: {CURA}\n"
        '      - run: pip install -e ".[dev]"\n'
        "      - run: ./scripts/gate.sh\n"
        f"# a camada que fala com a USP fica fora: ela exige {VARIAVEL_LIVE} e "
        "credencial pessoal\n"
    )
    assert liga_a_camada_live(limpo) == [], "acusou um comentário que só explica"
    assert segredos_em(limpo) == [], "acusou um workflow que não tem segredo nenhum"
    assert desliga_a_suite(limpo) == [], "acusou um workflow que roda o gate inteiro"


# ------------------------------- C10: o GitHub consegue ABRIR o arquivo


def test_c10_todo_workflow_e_yaml_que_o_github_consegue_carregar():
    """C10 — os nove testes acima leem o workflow como TEXTO, e texto passa.

    Custou três dias de CI vermelho: o merge de 16/09 deixou dois blocos de
    comentário colados e o `runs-on` com indentação de dois espaços, fora do
    job. O arquivo virou YAML inválido, o GitHub recusou antes de criar job
    nenhum — falha em 0s, sem log —, e a suíte seguiu verde nos nove, porque
    nenhum deles abre o arquivo como o GitHub abre. É o item 11 do `CLAUDE.md`
    na forma mais cara: verde na suíte, vermelho no único lugar que importa.

    Um parser de verdade, e não uma checagem de indentação escrita à mão: a
    pergunta "isto é YAML válido?" já tem implementação, e este repositório já
    pagou três vezes pelo preço de a mesma pergunta ter duas (§9, 12/09/2026).
    """
    if yaml is None:  # pragma: no cover - só num ambiente sem o extra `dev`
        assert not os.environ.get("GITHUB_ACTIONS"), (
            "o `pyyaml` não está instalado NO CI. C10 é o único teste que abre o "
            'workflow como o GitHub abre; sem ele o runner valida a si mesmo '
            'lendo texto. Instale com `pip install -e ".[dev]"`.'
        )
        pytest.skip(
            "sem `pyyaml`: C10 não conferiu se o GitHub consegue CARREGAR os "
            "workflows — e só isso. C1-C9 conferiram o conteúdo, como sempre. "
            'Instale com `.venv/bin/python -m pip install -e ".[dev]"`.'
        )

    for arquivo in workflows():
        try:
            carregado = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
        except yaml.YAMLError as erro:
            raise AssertionError(
                f"{arquivo.name} não é YAML válido, então o GitHub recusa o "
                f"arquivo inteiro: nenhum job roda, a falha vem em 0s e sem log, "
                f"e nada nesta suíte percebe. Erro do parser:\n{erro}"
            ) from None

        jobs = (carregado or {}).get("jobs")
        assert isinstance(jobs, dict) and jobs, (
            f"{arquivo.name} carrega, mas não declara `jobs:` como um mapa de "
            "trabalhos. Um workflow sem job é um arquivo que o GitHub aceita e "
            "que não roda nada — o falso-verde que este repositório persegue."
        )

        for nome, trabalho in jobs.items():
            assert isinstance(trabalho, dict), (
                f"{arquivo.name}: o job `{nome}` não é um mapa. Quase sempre é "
                "indentação: uma chave do job escrita no nível de `jobs:` vira "
                "um job irmão, com nome de chave e sem nada dentro."
            )
            faltando = [c for c in ("runs-on", "steps") if c not in trabalho]
            assert not faltando, (
                f"{arquivo.name}: o job `{nome}` não declara "
                f"{', '.join(f'`{c}`' for c in faltando)}. O GitHub exige os "
                "dois; sem eles o arquivo é recusado na carga, do mesmo jeito "
                "que um YAML quebrado."
            )
