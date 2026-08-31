"""Projeção: 528 kB de transporte viram ~7 kB de resposta.

ESQUELETO — Fase 2 não começou. Ver tests/moodle/ para o contrato.
"""
from __future__ import annotations

_PENDENTE = (
    "Fase 2 não implementada. Este módulo é definido pela suíte em tests/moodle/; "
    "rode `pytest` para ver o contrato que falta cumprir."
)


def __getattr__(nome: str):
    # Dunder tem de continuar sendo AttributeError: interceptar __path__ quebra
    # o import de submódulo e transforma um vermelho legível em erro de coleta.
    if nome.startswith("__") and nome.endswith("__"):
        raise AttributeError(nome)
    raise NotImplementedError(f"{nome}: {_PENDENTE}")
