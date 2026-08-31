"""Transporte do web service + política na fronteira.

ESQUELETO — Fase 2 não começou. Ver tests/moodle/test_cliente.py.

A classe existe (a suíte precisa importá-la) mas nada funciona ainda. A política
é aplicada AQUI de propósito: se morasse só na camada de ferramenta, qualquer
código novo que usasse o cliente direto contornaria a allowlist.
"""
from __future__ import annotations

from .erros import ErroMoodle  # noqa: F401  (reexportado por conveniência)

_PENDENTE = (
    "Fase 2 não implementada. Este módulo é definido pela suíte em "
    "tests/moodle/test_cliente.py; rode `pytest` para ver o contrato."
)


class ClienteMoodle:
    """Uma função por invocação, escolhida à mão (Regra de Ouro, §3.1).

    Deliberadamente SEM método que itere sobre funções: um sweep sobre as 447
    passa por `start_attempt` e `submit_for_grading` com o token do dono.
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(_PENDENTE)

    def chamar(self, funcao: str, **params):
        raise NotImplementedError(_PENDENTE)


def __getattr__(nome: str):
    # Dunder tem de continuar sendo AttributeError: interceptar __path__ quebra
    # o import de submódulo e transforma um vermelho legível em erro de coleta.
    if nome.startswith("__") and nome.endswith("__"):
        raise AttributeError(nome)
    raise NotImplementedError(f"{nome}: {_PENDENTE}")
