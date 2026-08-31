"""Insumos das três camadas.

A fixture higienizada é obrigatória, não opcional: se ela sumir, os testes têm de
FALHAR, nunca dar skip. Um skip aqui produziria verde sem ter testado nada — o
falso "não tem nada" que o Invariante 6 proíbe, aplicado à própria suíte.

O segundo insumo é o `.env`, e ele precisa ser carregado AQUI porque nada no
lado Python fazia isso: só `scripts/ws.sh` sourceia o arquivo (`set -a`). O
efeito era um erro legível apontando para a cura errada — `test_live` dizia
"MOODLE_TOKEN está vazio, copie .env.example para .env" para quem já tinha o
.env preenchido, porque o valor nunca chegava a `os.environ`. E fazia
`test_a_fixture_versionada_nao_contem_segredo_do_env` passar no vácuo: ela
varre a fixture procurando os segredos do ambiente, e o ambiente não tinha
nenhum para procurar.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FIXTURE_EVENTOS = RAIZ / "fixtures" / "moodle" / "action_events.json"


def _achar_env() -> Path | None:
    """O `.env` é gitignorado, então um worktree novo não tem o dele — mesma
    situação do cru. Procura na raiz de onde a suíte roda e, se não achar,
    sobe até o checkout que tem o `.git` de verdade (num worktree o `.git` é
    arquivo, não diretório). Devolve None quando não existe em lugar nenhum,
    porque "não tem .env" e "tem .env sem a chave" pedem mensagens
    diferentes."""
    candidatos = [RAIZ / ".env"]
    for pai in RAIZ.parents:
        if (pai / ".git").is_dir():
            candidatos.append(pai / ".env")
            break
    for c in candidatos:
        if c.is_file():
            return c
    return None


ARQUIVO_ENV = _achar_env()


def _carregar_env() -> None:
    """Põe o `.env` em `os.environ` — o equivalente Python do `set -a && . ./.env`
    da linha 15 do `scripts/ws.sh`.

    Parser de stdlib de propósito: `python-dotenv` seria a primeira dependência
    de runtime do projeto, e o formato aqui é `CHAVE=valor` com comentário —
    não vale uma dependência.

    `setdefault`, e não atribuição: quem já está no ambiente GANHA. É o que
    mantém `USP_MCP_LIVE=1 pytest` valendo mesmo se o `.env` disser o
    contrário, e o que impede este carregador de ligar a camada live por
    baixo de quem não pediu.

    Nenhum valor é impresso, nem em erro (Invariante 3): linha malformada é
    ignorada em silêncio em vez de ecoada.
    """
    if ARQUIVO_ENV is None:
        return
    for linha in ARQUIVO_ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        # `export CHAVE=valor` é válido num arquivo feito para ser sourceado.
        chave = chave.removeprefix("export ").strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        if chave:
            os.environ.setdefault(chave, valor)


_carregar_env()


def _achar_cru() -> Path:
    """O cru é local à máquina do dono (gitignorado, §3.3) e num worktree ele
    não existe. Procura no worktree, depois no checkout principal, depois onde
    USP_MCP_MOODLE_RAW apontar. Só os testes DO HIGIENIZADOR dependem dele —
    a fixture higienizada, essa, é obrigatória e faz falhar se sumir."""
    candidatos = [RAIZ / "fixtures" / "moodle" / "raw"]
    if (env := os.environ.get("USP_MCP_MOODLE_RAW")):
        candidatos.insert(0, Path(env))
    # .claude/worktrees/<nome>/ → sobe até o checkout que tem o .git de verdade
    for pai in RAIZ.parents:
        if (pai / ".git").is_dir():
            candidatos.append(pai / "fixtures" / "moodle" / "raw")
            break
    for c in candidatos:
        if (c / "action_events.json").exists():
            return c / "action_events.json"
    return candidatos[0] / "action_events.json"


CRU_EVENTOS = _achar_cru()


@pytest.fixture(scope="session")
def eventos_brutos() -> dict:
    if not FIXTURE_EVENTOS.exists():
        pytest.fail(
            f"Fixture higienizada ausente: {FIXTURE_EVENTOS}\n"
            "Gere com: python3 scripts/higienizar.py "
            "fixtures/moodle/raw/action_events.json fixtures/moodle/action_events.json\n"
            "Isto FALHA em vez de dar skip de propósito (Invariante 6)."
        )
    return json.loads(FIXTURE_EVENTOS.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def caminho_fixture() -> Path:
    return FIXTURE_EVENTOS


def pytest_runtest_setup(item):
    """Camada live só roda com a env var. O skip DIZ o motivo (Invariante 6)."""
    if "live" in item.keywords and os.environ.get("USP_MCP_LIVE") != "1":
        pytest.skip(
            "camada live desligada: exporte USP_MCP_LIVE=1 para falar com "
            "edisciplinas.usp.br. Do sandbox a rede da USP não é alcançável (§1.1)."
        )
