"""Insumos das três camadas.

A fixture higienizada é obrigatória, não opcional: se ela sumir, os testes têm de
FALHAR, nunca dar skip. Um skip aqui produziria verde sem ter testado nada — o
falso "não tem nada" que o Invariante 6 proíbe, aplicado à própria suíte.

O segundo insumo é o `.env`, carregado por `usp_mcp.env` porque nada no lado
Python fazia isso: só `scripts/ws.sh` sourceia o arquivo (`set -a`). O
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

from usp_mcp.env import carregar_env

RAIZ = Path(__file__).resolve().parents[2]
FIXTURE_EVENTOS = RAIZ / "fixtures" / "moodle" / "action_events.json"
FIXTURE_ERRO = RAIZ / "fixtures" / "moodle" / "erro_invalidtoken.json"
FIXTURE_ERRO_PARAM = RAIZ / "fixtures" / "moodle" / "erro_invalidparameter.json"
FIXTURE_ERRO_LIMITE = RAIZ / "fixtures" / "moodle" / "erro_limite_fora_da_faixa.json"


# O carregador mora em usp_mcp/env.py, não aqui: o entrypoint stdio do Moodle
# precisa do mesmo comportamento (§9, 31/08/2026). `setdefault` lá dentro
# garante que quem já está no ambiente ganha — `USP_MCP_LIVE=1 pytest` continua
# valendo, e este import não liga a camada live por baixo de ninguém.
ARQUIVO_ENV = carregar_env(RAIZ)


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


@pytest.fixture(scope="session")
def erro_invalidtoken() -> dict:
    """A resposta REAL do Moodle para token inválido, capturada em 31/08/2026.

    Capturada com `wstoken=""` — token propositalmente vazio, que não usa
    credencial de ninguém e não toca conta nenhuma. É o que faltava para os
    testes de erro pararem de assegurar só o contrato da camada.

    Obrigatória, não opcional, pelo mesmo motivo da fixture de eventos: um
    skip aqui produziria verde sem ter testado nada.
    """
    if not FIXTURE_ERRO.exists():
        pytest.fail(
            f"Fixture de erro ausente: {FIXTURE_ERRO}\n"
            "Recapture com wstoken vazio contra "
            "https://edisciplinas.usp.br/webservice/rest/server.php\n"
            "Isto FALHA em vez de dar skip de propósito (Invariante 6)."
        )
    return json.loads(FIXTURE_ERRO.read_text(encoding="utf-8"))


def pytest_runtest_setup(item):
    """Camada live só roda com a env var. O skip DIZ o motivo (Invariante 6)."""
    if "live" in item.keywords and os.environ.get("USP_MCP_LIVE") != "1":
        pytest.skip(
            "camada live desligada: exporte USP_MCP_LIVE=1 para falar com "
            "edisciplinas.usp.br. Do sandbox a rede da USP não é alcançável (§1.1)."
        )


def _carregar_fixture_erro(caminho: Path, como_recapturar: str) -> dict:
    if not caminho.exists():
        pytest.fail(
            f"Fixture de erro ausente: {caminho}\n{como_recapturar}\n"
            "Isto FALHA em vez de dar skip de propósito (Invariante 6)."
        )
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def erro_invalidparameter() -> dict:
    """Erro real de parâmetro inválido, capturado em 31/08/2026 na MESMA função
    da allowlist, read-only, com `timesortfrom` textual (Regra de Ouro §3.1)."""
    return _carregar_fixture_erro(
        FIXTURE_ERRO_PARAM,
        "Recapture chamando core_calendar_get_action_events_by_timesort "
        "com timesortfrom='nao-e-numero'.",
    )


@pytest.fixture(scope="session")
def erro_limite_fora_da_faixa() -> dict:
    """O erro que revelou o teto de 50 do `limitnum` — e que `errorcode` nem
    sempre é um código (§9, 31/08/2026)."""
    return _carregar_fixture_erro(
        FIXTURE_ERRO_LIMITE,
        "Recapture chamando core_calendar_get_action_events_by_timesort "
        "com limitnum=-5.",
    )
