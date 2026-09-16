"""D3-D6: a checagem 0 do gate, e o código de saída de quando a suíte não roda.

Arquivo separado do `test_documentacao.py` de propósito, e não por gosto: D1-D2
leem um `.md` e custam um `read_text`; D3-D5 leem e **executam** o
`scripts/gate.sh`, dois deles num clone de verdade. São dois assuntos (o que o
README promete x o que o gate faz) com dois custos (microssegundos x segundos),
e quem for mexer num não quer o outro no caminho.

O que estes três protegem, em uma frase: **o gate tem que descobrir que falta o
`.env` antes de gastar 364 testes para descobrir a mesma coisa** — o cabeçalho
do próprio script já diz que a checagem mais barata que pode reprovar vem antes
— **e tem que dizer o comando que resolve**, em vez de falar de `RUCARD_HASH`,
que é consequência e não causa.

D4/D5/D6 clonam com `git clone --local`: nada de rede, nada de credencial. Sem
`git` no PATH eles pulam declarando o motivo, em vez de passar sem ter rodado.

D6 é de outra família, e está aqui por herdar o mesmo clone caro: ele guarda o
**código de saída** do gate quando a checagem 3 é pulada. Por dois dias o
comentário do `gate.sh` afirmava que o código "NAO vira 0 por causa disto" e o
script saía 0: comentário certo, código errado. `./scripts/gate.sh && git push`
via verde sem a suíte ter rodado, que é exatamente o falso-verde que o §6 do
`CONVENTIONS.md` proíbe.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
GATE = RAIZ / "scripts" / "gate.sh"

# O comando exato que a mensagem de falha tem que citar — o mesmo que o README
# manda dar (D1). Duas cópias da mesma string em dois testes é de propósito: é
# ela que amarra o erro do gate ao passo do README.
CURA = "cp .env.example .env"

MOTIVO_SEM_GIT = (
    "`git` não está no PATH deste ambiente, e D4/D5 precisam de um clone limpo "
    "para exercitar o gate sem `.env`. Este skip NÃO é o caso normal: no "
    "ambiente do dono o git existe e estes testes rodam no gate."
)


def _clone_limpo(destino: pathlib.Path) -> pathlib.Path:
    """Um checkout de verdade, com `.git`, e sem `.env` — que é o ponto.

    `git clone --local` porque as checagens 1 e 2 do gate chamam `git ls-files`
    e `git check-ignore`: um diretório copiado à mão não é um repositório e
    faria as duas mentirem.

    Por cima do clone vai o estado ATUAL da árvore de trabalho, arquivo
    rastreado por arquivo rastreado. O clone traz o último *commit*, e um teste
    que só enxerga o que já foi commitado chega tarde demais para um gate de
    **pré**-commit: ele ficaria verde na branch antiga e vermelho só depois de
    o estrago estar registrado. O `.env` não é rastreado, então continua fora —
    é exatamente a situação de quem acabou de clonar.
    """
    subprocess.run(
        ["git", "clone", "--local", "--quiet", str(RAIZ), str(destino)],
        check=True,
        capture_output=True,
        text=True,
    )
    rastreados = subprocess.run(
        ["git", "-C", str(RAIZ), "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    for nome in rastreados:
        origem = RAIZ / nome
        if not nome or not origem.is_file():
            continue
        alvo = destino / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, alvo)  # copy2: preserva o bit de execução do .sh
    return destino


def _rodar_gate(raiz: pathlib.Path) -> subprocess.CompletedProcess:
    """Roda o gate no clone, com o ambiente limpo das variáveis do `.env`.

    Sem esta limpeza o teste seria teatro: o `conftest` da suíte já carregou o
    `.env` do worktree para `os.environ`, e o processo filho herdaria
    `RUCARD_HASH` de quem o chamou. A checagem 0 olha o ARQUIVO, não o ambiente
    — mas um teste que depende disso continuar verdade não está verificando o
    que promete.
    """
    ambiente = {k: v for k, v in os.environ.items() if k not in ("RUCARD_HASH", "MOODLE_TOKEN")}
    # Sem isto o gate do clone roda a suite DO CLONE — que contem este arquivo,
    # que clona de novo. A recursao ficou latente ate 11/09, quando o merge poz
    # test_gate.py no HEAD que o clone copia, e D5 passou a estourar 300 s.
    # Nenhum teste daqui assere sobre a checagem 3, entao pular nao afrouxa nada;
    # e D5 passa a assertar que o pulo APARECE, para ele nunca virar silencioso.
    ambiente["USP_MCP_GATE_SEM_SUITE"] = "1"
    return subprocess.run(
        ["./scripts/gate.sh"],
        cwd=raiz,
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _linha_da_checagem(saida: str, numero: str) -> str:
    """A linha de relatório de uma checagem (`  0. ...  OK`), uma só."""
    achadas = [l for l in saida.splitlines() if l.strip().startswith(f"{numero}.")]
    assert len(achadas) == 1, (
        f"esperava exatamente uma linha da checagem {numero} no relatório do "
        f"gate, achei {len(achadas)}. Saída:\n{saida}"
    )
    return achadas[0].strip()


def test_d3_o_gate_checa_o_env_antes_da_suite():
    fonte = GATE.read_text(encoding="utf-8")
    i_hash = fonte.find("RUCARD_HASH")
    i_cura = fonte.find(CURA)
    i_suite = fonte.find("-m pytest")

    assert i_hash != -1, (
        "o `gate.sh` não menciona `RUCARD_HASH`: não há checagem 0, e a "
        "ausência do `.env` volta a ser descoberta pela suíte."
    )
    assert i_cura != -1, (
        f"o `gate.sh` não cita {CURA!r} em lugar nenhum. Erro que não nomeia a "
        "cura devolve o leitor para o sintoma (Invariante 6)."
    )
    assert i_suite != -1, (
        "o `gate.sh` não roda mais `-m pytest`. Se a suíte saiu do gate, este "
        "teste está comparando índices de outra coisa."
    )
    assert max(i_hash, i_cura) < i_suite, (
        "a checagem do `.env` aparece DEPOIS da linha que roda a suíte. O "
        "cabeçalho do próprio script diz que a mais barata que pode reprovar vem "
        "antes: um `test -f` não pode custar 364 testes."
    )


@pytest.mark.skipif(shutil.which("git") is None, reason=MOTIVO_SEM_GIT)
def test_d4_o_gate_reprova_sem_env_citando_a_cura(tmp_path):
    clone = _clone_limpo(tmp_path / "clone-limpo")
    assert not (clone / ".env").exists(), (
        "o clone nasceu com `.env`. Ou ele deixou de ser gitignorado (e aí o "
        "problema é bem maior que este teste), ou o clone não é limpo e D4 não "
        "está exercitando nada."
    )

    r = _rodar_gate(clone)

    assert r.returncode != 0, (
        f"o gate PASSOU num clone sem `.env`. Saída:\n{r.stdout}{r.stderr}"
    )
    assert CURA in r.stdout, (
        f"o gate reprovou sem citar {CURA!r} — que é o passo que faltou. Falar "
        "de `RUCARD_HASH` para quem nunca copiou o `.env` é apontar a "
        f"consequência. Saída:\n{r.stdout}{r.stderr}"
    )


@pytest.mark.skipif(shutil.which("git") is None, reason=MOTIVO_SEM_GIT)
def test_d5_o_gate_nao_exige_token_do_moodle(tmp_path):
    clone = _clone_limpo(tmp_path / "clone-com-env")
    shutil.copy2(clone / ".env.example", clone / ".env")

    # A premissa do teste, asseverada em vez de suposta: o exemplo traz o
    # `MOODLE_TOKEN` VAZIO. Se algum dia ele vier preenchido, o vazamento é o
    # achado — e D5 passaria a provar o contrário do que promete.
    texto = (clone / ".env").read_text(encoding="utf-8")
    assert re.search(r"^MOODLE_TOKEN=\s*$", texto, re.M), (
        "o `.env.example` não tem mais `MOODLE_TOKEN` vazio. D5 existe para "
        "provar que a checagem 0 passa SEM credencial pessoal (Invariante 4)."
    )

    r = _rodar_gate(clone)

    linha = _linha_da_checagem(r.stdout, "0")
    assert linha.endswith("OK"), (
        "a checagem 0 reprovou com o `.env` recém-copiado do exemplo. Ela está "
        "exigindo algo além de `RUCARD_HASH` — provavelmente o token do Moodle, "
        "que é credencial pessoal e não entra num gate offline (Invariante 4). "
        f"Saída:\n{r.stdout}{r.stderr}"
    )
    assert CURA not in r.stdout, (
        f"o gate citou {CURA!r} com o `.env` já no lugar. A cura só pode "
        f"aparecer quando é de fato a cura, senão vira ruído. Saída:\n{r.stdout}"
    )
    # O pulo da suíte é o que impede este teste de recorrer sobre si mesmo, e ele
    # precisa ser barulhento: um gate que pula a checagem 3 calado é pior que a
    # recursão, porque devolve verde sem ter verificado código nenhum.
    assert "PULADA" in r.stdout and "SUITE NAO RODOU" in r.stdout, (
        "o gate pulou a suíte sem dizer. Invariante 7: sem limite silencioso — "
        f"quem lê a saída tem de saber que a checagem 3 não rodou. Saída:\n{r.stdout}"
    )


@pytest.mark.skipif(shutil.which("git") is None, reason=MOTIVO_SEM_GIT)
def test_d6_a_suite_pulada_nao_sai_com_zero(tmp_path):
    """D6: pular a checagem 3 não pode devolver sucesso a quem chamou.

    Dizer PULADA na tela e sair 0 protege só quem LÊ a saída. Quem encadeia
    (`./scripts/gate.sh && git push`), quem roda no CI ou quem põe isto num hook
    só enxerga o código de saída, e para esses o gate estava dizendo "passou"
    sobre uma suíte que não rodou.

    O que se assere é `!= 0`, e não um número: o valor exato é detalhe do
    script, e um teste que o fixasse reprovaria por uma renumeração que não
    muda nada. O que não pode mudar é a resposta à pergunta "posso commitar?".
    """
    clone = _clone_limpo(tmp_path / "clone-sem-suite")
    shutil.copy2(clone / ".env.example", clone / ".env")

    r = _rodar_gate(clone)

    # A premissa: este run de fato pulou a suíte. Sem isto, um gate que
    # reprovasse na checagem 0 passaria aqui por acidente, provando outra coisa.
    assert "PULADA" in r.stdout, (
        "este run não chegou a pular a checagem 3, e D6 não está medindo o que "
        f"promete. Saída:\n{r.stdout}{r.stderr}"
    )
    assert r.returncode != 0, (
        "o gate saiu 0 com a suíte PULADA. Quem encadeia `./scripts/gate.sh && "
        "git push` recebe sinal verde sobre código que ninguém testou, e o "
        "comentário do próprio script promete o contrário. Faça o caminho do "
        f"pulo sair com código próprio. Saída:\n{r.stdout}{r.stderr}"
    )
