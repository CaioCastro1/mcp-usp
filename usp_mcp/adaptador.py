"""Ponte entre o `inputSchema` declarado e a assinatura que o SDK do MCP lê.

Existe por causa de um achado de 31/08/2026, encontrado quando o handshake stdio
finalmente passou a ser testado: **o SDK não usa o `inputSchema` que
`listar_ferramentas()` declara.** Ele deriva o schema que o modelo vê da
ASSINATURA da função registrada em `main()`. Consequência medida nos três
servidores: nenhuma descrição de parâmetro e nenhum `enum` chegava ao modelo —
ele recebia `{"title": "Dia", "type": "string"}` no lugar de "'hoje', 'amanhã' ou
uma data como 26/08/2026", e não sabia que só existem quatro RUs.

Duas coisas este módulo faz, e uma que ele deliberadamente não faz:

**Faz:** tira a descrição de cada parâmetro do schema declarado e a prende à
anotação, para que o texto tenha um dono só. Repetir a descrição na assinatura
seria criar a segunda cópia que envelhece calada — que é o problema original com
outro nome.

**Faz:** resolve a anotação como OBJETO. Os servidores usam
`from __future__ import annotations`, o que transforma toda anotação em string; o
SDK precisa do objeto para derivar `enum` e descrição. Atribuir `__annotations__`
depois de definir a função é o que dá as duas coisas ao mesmo tempo.

**Não faz:** converter JSON Schema em tipo Python. O tipo (inclusive `Literal`
para enum) fica na assinatura do adaptador, onde se lê junto com o resto. Quem
garante que os dois não divirjam é o teste de handshake H6-H8, que compara o
declarado com o que sai no fio — verificação, não geração.
"""
from __future__ import annotations


def anotar(funcao, schema: dict, tipos: dict) -> None:
    """Prende `Annotated[tipo, Field(description=…)]` a cada parâmetro.

    `schema` é o `inputSchema` declarado em `listar_ferramentas()`; `tipos` é o
    tipo Python de cada parâmetro, incluindo `Literal[...]` onde houver enum.
    Modifica `funcao.__annotations__` no lugar — é ela que o SDK inspeciona.

    Um parâmetro em `tipos` que não exista no schema é erro, não silêncio: os
    dois lados descrevem a mesma ferramenta, e divergir aqui é a origem do
    problema que este módulo existe para não repetir.
    """
    from typing import Annotated

    from pydantic import Field

    propriedades = schema.get("properties", {})
    faltando = set(tipos) - set(propriedades)
    if faltando:
        raise ValueError(
            f"parâmetros sem declaração no inputSchema: {sorted(faltando)}. "
            "O schema declarado é a fonte da descrição que o modelo lê."
        )

    anotacoes = {}
    for nome, tipo in tipos.items():
        descricao = propriedades[nome].get("description")
        anotacoes[nome] = (
            Annotated[tipo, Field(description=descricao)] if descricao else tipo
        )
    anotacoes["return"] = str
    funcao.__annotations__ = anotacoes
