"""ESQUELETO-FASE2 — transporte, allowlist e cache.

Não há implementação: a Fase 2 não começou, e o §4.10 do CLAUDE.md proíbe
começá-la por conveniência. Este arquivo existe por uma razão medida: com o
módulo AUSENTE o pytest aborta a coleta inteira ("Interrupted: N errors during
collection") e os testes verdes nem rodam. Com o esqueleto, o vermelho vira
contável.

Cada símbolo levanta NotImplementedError apontando para os testes que o
definem. A suíte é a especificação: comece por tests/jupiter/.
"""

_TESTES = "tests/jupiter/test_cliente.py (T13-T25)"


def __getattr__(nome):
    # PEP 562. Os dunder precisam escapar: __path__, __all__ e afins são
    # consultados pelo próprio import, e interceptá-los quebra
    # "from usp_mcp.jupiter import <modulo>".
    if nome.startswith("__") and nome.endswith("__"):
        raise AttributeError(nome)
    raise NotImplementedError(
        f"cliente.{nome} ainda não existe. Definido por {_TESTES}; "
        "implementar é a Fase 2."
    )
