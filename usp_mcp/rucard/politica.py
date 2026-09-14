"""Allowlist do RUCard (Invariante 2).

Duas dimensões, e as duas precisam de allowlist por motivos diferentes.

**Rota.** A base `rucard/servicos` serve `/menu/{id}` e `/restaurants`; o que mais
existe atrás dela não foi mapeado na Fase 1. O app oficial do RUCard tem área
autenticada com saldo, extrato e recarga, e nada disso foi verificado. Uma
denylist aqui seria uma lista de rotas que ninguém enumerou — o default tem que
ser negar (§2.2 do SPEC1: `permitir_escrita` não abre nada que não tenha sido
desenhado como escrita).

**Id do RU.** São 18 RUs, e o §1.2 registra a decisão do dono de trabalhar com
quatro. Um modelo interpretando "quero almoçar perto da Poli" escolhe id, e o
default de novo tem que ser negar — com a diferença de que aqui a negativa é
informativa: "esse RU existe e está fora de escopo" e "esse id não existe" têm
curas diferentes, e devolver a mesma frase para os dois apaga a diferença.

A lista dos 14 fora de escopo é a capturada em 27/08/2026 e serve **só** para
essa distinção. Os ids não são contíguos (10, 15, 16, 21 e 22 não aparecem), então
"não está na lista" não prova que não exista — e a mensagem diz isso em vez de
afirmar mais do que a captura sustenta.
"""
from __future__ import annotations

from dataclasses import dataclass

ROTAS_PERMITIDAS: frozenset[str] = frozenset({"menu", "restaurants"})

# §1.2: resolver por id; `name`/`alias` é exibição. O alias fica aqui só para a
# mensagem de erro ser legível — e há teste que o compara com o do catálogo real,
# porque um alias trocado apontaria para outro RU sem ninguém notar.
RUS_PERMITIDOS: dict[str, str] = {
    "6": "CENTRAL",
    "7": "PUSP-CB",
    "8": "FÍSICA",
    "9": "QUÍMICAS",
}

# Os outros 14 da captura de 27/08/2026. Não são "proibidos por serem ruins":
# estão fora do recorte do dono, e crescer é decisão registrada no §9.
RUS_FORA_DE_ESCOPO: dict[str, str] = {
    "1": "PIRACICABA",
    "2": "ÁREA 1 (SC)",
    "3": "ÁREA 2 (SC)",
    "4": "CRHEA (SC)",
    "5": "PIRASSUNUNGA",
    "11": "FAC. DE SAÚDE PÚBLICA",
    "12": "ESCOLA DE ENFERMAGEM",
    "13": "EACH",
    "14": "FACULDADE DE DIREITO",
    "17": "EEL - ÁREA 1",
    "18": "FACULDADE DE MEDICINA",
    "19": "CENTRAL (RP)",
    "20": "BAURU",
    "23": "EEL - ÁREA 2",
}


@dataclass(frozen=True)
class Decisao:
    """Resultado de `decidir`. `motivo` existe para o Invariante 6: um `False`
    pelado não diz a quem lê o que fazer com o resultado."""

    permitida: bool
    motivo: str


def decidir(rota: str, ru: str | None = None, permitir_escrita: bool = False) -> Decisao:
    """Decide se o par (rota, RU) pode sair para a USP.

    `permitir_escrita` é a flag do Invariante 1 e **não libera nada aqui**: a
    Fase 1 não mapeou rota de escrita nenhuma no RUCard, e uma flag não inventa
    fonte. O parâmetro existe para deixar essa ausência de efeito explícita no
    call site, em vez de a política simplesmente não aceitar a flag.
    """
    if rota not in ROTAS_PERMITIDAS:
        return Decisao(
            permitida=False,
            motivo=(
                f"rota {rota!r} não é uma das que esta ferramenta consulta no "
                f"RUCard ({', '.join(sorted(ROTAS_PERMITIDAS))}; a lista é fechada). "
                "Saldo, extrato e recarga do cartão não estão disponíveis por aqui, "
                "e nenhuma configuração os libera."
            ),
        )

    if rota != "menu":
        return Decisao(permitida=True, motivo=f"rota {rota} na allowlist.")

    if ru is None:
        return Decisao(
            permitida=False,
            motivo="a rota menu exige o id do restaurante — sem id não há chamada.",
        )

    if ru in RUS_PERMITIDOS:
        return Decisao(permitida=True, motivo=f"RU {ru} ({RUS_PERMITIDOS[ru]}).")

    if ru in RUS_FORA_DE_ESCOPO:
        return Decisao(
            permitida=False,
            motivo=(
                f"o RU {ru} ({RUS_FORA_DE_ESCOPO[ru]}) existe no RUCard mas está "
                "fora do escopo desta ferramenta, que cobre os quatro da Cidade "
                f"Universitária: {', '.join(f'{i} {n}' for i, n in RUS_PERMITIDOS.items())}. "
                "Incluir outro restaurante é mudança do projeto, não opção de chamada."
            ),
        )

    return Decisao(
        permitida=False,
        motivo=(
            f"id de restaurante {ru!r} não aparece entre os 18 RUs capturados em "
            "27/08/2026. Os ids do RUCard não são contíguos, então isto não prova "
            "que ele não exista — prova que ninguém o verificou."
        ),
    )
