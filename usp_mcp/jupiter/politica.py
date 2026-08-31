"""Allowlist do bean público do JupiterWeb (Invariante 2).

Duas camadas, e a segunda não é redundante.

**Consultas** — `ControlePublicoDWR.obter` e `.listar` recebem o nome da consulta
como PRIMEIRO PARÂMETRO. Isso é RPC genérico com nome em string, e a allowlist
existe porque o default tem que ser negar: quem escolhe a consulta é um modelo
interpretando linguagem ambígua.

**Métodos** — o bean expõe também `executarBatch`, `executar`, `obterArquivo`,
`obterRelatorio`, `obterCsv`, `obterPdf`, `obterZip`, `obterWebdoc` e
`obterProgresso` (§4.1 do recon, lidos na interface DWR servida em produção).
`executarBatch` é o análogo exato de `tool_mobile_call_external_functions`
registrado no §9 de 31/08: um executor genérico **anula qualquer filtro por nome
de consulta**, porque a consulta passa a viajar dentro do lote. Filtrar só
consulta não bloqueia nada se o método for livre.

Por isso o bloqueio de método é permanente e ignora `permitir_escrita`: não há
flag que libere (§2.2). E é o que garante que um erro futuro na lista de
consultas ainda não abra o caminho genérico.
"""
from __future__ import annotations

from dataclasses import dataclass

# Fatia vertical: a pergunta do §5 do SPEC1 ("quantos créditos e qual o
# pré-requisito?"). Crescer isto é decisão registrada no §9, não conveniência.
CONSULTAS_PERMITIDAS: dict[str, str] = {
    "pubObterDisciplina": "obter",
    "pubListarRequisitoDisciplina": "listar",
}

# Os únicos métodos do bean que esta fatia usa.
METODOS_PERMITIDOS: frozenset[str] = frozenset({"obter", "listar"})

# §4.1 do recon: o resto da interface. Negado sempre, com ou sem flag.
BLOQUEIO_PERMANENTE: frozenset[str] = frozenset(
    {
        # o bypass: a consulta viaja dentro do lote e escapa de qualquer filtro
        "executarBatch",
        "executar",
        # exportadores: devolvem arquivo, não dado — custo imprevisível e sem
        # forma verificada na Fase 1
        "obterArquivo",
        "obterRelatorio",
        "obterCsv",
        "obterPdf",
        "obterZip",
        "obterWebdoc",
        "obterProgresso",
        # outro bean, nunca chamado na Fase 1: assinatura lida, não testada
        "recuperarProjetoPedagogico",
    }
)


@dataclass(frozen=True)
class Decisao:
    """Resultado de `decidir`. `motivo` existe para o Invariante 6: um `False`
    pelado não diz o que fazer com o resultado."""

    permitida: bool
    motivo: str


def decidir(metodo: str, consulta: str, permitir_escrita: bool = False) -> Decisao:
    """Decide se a dupla (método, consulta) pode sair para a USP.

    `permitir_escrita` é a flag do Invariante 1 e **não libera nada aqui**: o
    bloqueio de método ignora a flag por definição, e nenhuma consulta da fatia
    escreve. O parâmetro existe para deixar essa ausência de efeito explícita no
    call site, em vez de a política simplesmente não aceitar a flag.
    """
    if metodo in BLOQUEIO_PERMANENTE:
        return Decisao(
            permitida=False,
            motivo=(
                f"método {metodo} está no bloqueio permanente — negado mesmo com "
                "permitir_escrita=True, pois não há flag que libere. Um executor "
                "genérico anula o filtro por nome de consulta."
            ),
        )

    if metodo not in METODOS_PERMITIDOS:
        return Decisao(
            permitida=False,
            motivo=f"método {metodo} não está na allowlist — o default é negar.",
        )

    if consulta not in CONSULTAS_PERMITIDAS:
        return Decisao(
            permitida=False,
            motivo=(
                f"consulta {consulta} não está na allowlist (Invariante 2, "
                "allowlist e não denylist). A fatia atual tem "
                f"{len(CONSULTAS_PERMITIDAS)} consultas."
            ),
        )

    esperado = CONSULTAS_PERMITIDAS[consulta]
    if esperado != metodo:
        return Decisao(
            permitida=False,
            motivo=f"{consulta} é servida por '{esperado}', não por '{metodo}'.",
        )

    return Decisao(permitida=True, motivo=f"{consulta} via {metodo}.")
