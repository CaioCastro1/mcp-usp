"""Insumos das três camadas.

A fixture higienizada é obrigatória, não opcional: se ela sumir, os testes têm de
FALHAR, nunca dar skip. Um skip aqui produziria verde sem ter testado nada — o
falso "não tem nada" que o Invariante 6 proíbe, aplicado à própria suíte.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FIXTURE_EVENTOS = RAIZ / "fixtures" / "moodle" / "action_events.json"


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
