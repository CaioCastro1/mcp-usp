"""Cliente do bean público do JupiterWeb.

Três coisas que este módulo existe para garantir, e que nenhuma outra camada
garante:

**O corpo da requisição é contrato.** O DWR responde HTTP 200 para corpo
malformado. Um erro de serialização não vira falha — vira campo vazio, com cara
de resposta. Por isso a montagem do corpo é testada byte a byte contra o §4.2
do recon.

**Nada de credencial.** O `ControlePublicoDWR` é público e stateless: sem
cookie, sem handshake, sem sessão (verificado na Fase 1 com `scriptSessionId`
inventado). O §6 do SPEC1 põe o Jupiter num servidor hospedado justamente por
isso. Este cliente não lê variável de ambiente com segredo e não manda cabeçalho
de identificação — e há teste de política que falha se alguém acrescentar.

**Gentileza com a USP** (Invariante 5). Cache com TTL colado na taxa de mudança
do dado — ementa muda por semestre, não por pergunta — e uma requisição por vez.
O rate limit do Jupiter continua sem evidência: 26 requisições sem 429 na Fase 1
**não provam** que não exista.
"""
from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request

from usp_mcp.jupiter import dwr, politica
from usp_mcp.jupiter.erros import ConsultaNegada, JupiterIndisponivel, RespostaInvalida
from usp_mcp.jupiter.politica import CONSULTAS_PERMITIDAS

__all__ = ["ClienteJupiter", "transporte_http", "ConsultaNegada", "CONSULTAS_PERMITIDAS",
           "URL_BASE", "AGENTE", "TTL_PADRAO"]

URL_BASE = "https://uspdigital.usp.br/jupiterweb/dwr/call/plaincall"

# Identificável e com contato, como o §9 do recon recomenda: quem administra o
# JupiterWeb tem que conseguir saber quem está batendo, e falar com alguém.
AGENTE = "usp-mcp/0.1 (nao-oficial; +https://github.com/CaioCastro1/mcp-usp)"

# Um semestre. O dado desta fatia é ementa, crédito e pré-requisito — muda entre
# semestres, e nunca por causa de uma pergunta repetida.
TTL_PADRAO = 60 * 60 * 24 * 120

_TEMPO_LIMITE = 20


def transporte_http(url: str, corpo: str, cabecalhos: dict[str, str]) -> tuple[int, str]:
    """Transporte real. Injetável: nos testes entra um dublê que grava a chamada."""
    pedido = urllib.request.Request(
        url, data=corpo.encode("utf-8"), headers=cabecalhos, method="POST"
    )
    try:
        with urllib.request.urlopen(pedido, timeout=_TEMPO_LIMITE) as resposta:
            bruto = resposta.read()
            charset = resposta.headers.get_content_charset() or "ISO-8859-1"
            return resposta.status, bruto.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:  # 4xx/5xx ainda têm corpo
        return e.code, e.read().decode("ISO-8859-1", errors="replace")
    except (urllib.error.URLError, TimeoutError) as e:
        raise JupiterIndisponivel(
            f"o JupiterWeb não respondeu ({e}). Se você está num sandbox, a rede "
            "da USP não é alcançável de lá — ver §1.1 do SPEC1."
        ) from e


class ClienteJupiter:
    """Chamador do `ControlePublicoDWR`, com política, cache e serialização.

    `transporte` recebe `(url, corpo, cabecalhos)` e devolve `(status, texto)`.
    `relogio` é injetável para que o teste de TTL verifique a REGRA, não o valor
    da constante.
    """

    def __init__(self, transporte, *, agente: str = AGENTE, relogio=time.monotonic,
                 ttl: int = TTL_PADRAO, permitir_escrita: bool = False):
        self._transporte = transporte
        self._agente = agente
        self._relogio = relogio
        self._ttl = ttl
        self._permitir_escrita = permitir_escrita
        self._cache: dict[tuple, tuple[float, object]] = {}
        # Uma requisição por vez. Não é thread-safety por acaso: é o Invariante 5.
        self._porta = threading.Lock()

    def _chamar(self, *, metodo: str, consulta: str, params: dict):
        decisao = politica.decidir(metodo, consulta, self._permitir_escrita)
        if not decisao.permitida:
            raise ConsultaNegada(decisao.motivo)

        chave = (metodo, consulta, tuple(sorted(params.items())))
        with self._porta:
            guardado = self._cache.get(chave)
            if guardado is not None and self._relogio() - guardado[0] < self._ttl:
                return guardado[1]

            corpo = dwr.serializar(metodo=metodo, consulta=consulta, params=params)
            status, texto = self._transporte(
                f"{URL_BASE}/ControlePublicoDWR.{metodo}.dwr",
                corpo,
                {"Content-Type": "text/plain", "User-Agent": self._agente},
            )
            if status != 200:
                raise RespostaInvalida(
                    f"o JupiterWeb respondeu HTTP {status}. Atenção: o erro NORMAL "
                    "dele vem com 200 e mensagem no corpo, então um status diferente "
                    "aqui é outra coisa — indisponibilidade ou rota errada."
                )

            valor = dwr.decodificar(texto)
            self._cache[chave] = (self._relogio(), valor)
            return valor

    def obter_disciplina(self, sigla: str) -> dict:
        """Ficha da disciplina. `verdis=0` é o que a aplicação oficial manda; o
        retorno vem com a versão corrente (§8 do recon: o significado exato de
        `verdis` não foi verificado, e não se assume)."""
        return self._chamar(
            metodo="obter",
            consulta="pubObterDisciplina",
            params={"coddis": sigla, "verdis": 0},
        )

    def listar_requisito(self, *, coddis: str, codcur: str, codhab: str) -> list:
        """Pré-requisitos da disciplina **naquele curso**. Os três parâmetros são
        obrigatórios porque a resposta é condicional ao curso (§5.2 do recon)."""
        return self._chamar(
            metodo="listar",
            consulta="pubListarRequisitoDisciplina",
            params={"codcur": codcur, "codhab": codhab, "coddis": coddis},
        )
