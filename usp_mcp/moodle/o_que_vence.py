"""A ferramenta: "o que eu tenho que entregar?" (§5).

ESQUELETO — Fase 2 não começou. Ver tests/moodle/test_o_que_vence.py.
"""
from __future__ import annotations

_PENDENTE = (
    "Fase 2 não implementada. Esta função é definida pela suíte em "
    "tests/moodle/test_o_que_vence.py; rode `pytest` para ver o contrato."
)


def o_que_vence(cliente, dias: int = 14, agora=None, limite: int | None = None):
    """Uma chamada ao Moodle, projeta, e devolve texto curto que diz o que não sabe."""
    raise NotImplementedError(_PENDENTE)
