"""Cliente do RUCard.

Quatro coisas que este módulo existe para garantir, e que nenhuma outra camada
garante:

**O método é POST.** Medido em 27/08 e de novo em 31/08/2026: a mesma rota por
verbo de leitura devolve HTTP 500 com 3.240 B de HTML do Tomcat. `urllib` manda
o verbo de leitura quando não há corpo, então o `method="POST"` é explícito e há
teste que falha se alguém o tirar.

**O HTML do Tomcat morre aqui.** 3.240 B de página de erro não respondem nada; a
mensagem curta responde. É o mesmo raciocínio do stack trace do Jupiter (§9 de
31/08): repassar o cru é a resposta errada, não a resposta honesta.

**Nada de credencial pessoal.** A hash do RUCard é compartilhada, embutida no app
oficial, e não identifica ninguém — é por isso que o §6 do SPEC1 põe este sistema
como candidato a servidor hospedado. Este cliente não lê variável de ambiente com
segredo de usuário, não manda cookie e não guarda sessão; há teste de política
que varre o fonte e falha se alguém acrescentar.

**Gentileza com a USP** (Invariante 5), com DUAS regras de cache, não uma:

- *TTL* protege a USP. Três horas para o cardápio, uma semana para o catálogo —
  colado na taxa de mudança do dado, e não na frequência da pergunta. O catálogo
  veio byte-idêntico em duas capturas separadas por quatro dias.
- *Validação por data* protege a resposta. A rota não aceita parâmetro de data:
  devolve sempre a semana corrente. Na segunda 31/08, às 19:22, a semana já era a
  nova — um cache de horas antes ainda teria a anterior, e devolvê-lo seria
  responder o cardápio da semana passada com cara de resposta certa. Quando o dia
  pedido é posterior à semana que está em cache, o cliente revalida **uma vez** por
  janela de TTL: o suficiente para pegar a virada, e pouco o bastante para uma
  pergunta sobre Natal não virar uma requisição por pergunta.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

from . import politica
from .erros import (
    ConsultaNegada,
    HashAusente,
    RespostaInvalida,
    RucardIndisponivel,
)

__all__ = [
    "ClienteRucard", "transporte_http", "URL_BASE", "AGENTE",
    "TTL_MENU", "TTL_CATALOGO",
]

URL_BASE = "https://uspdigital.usp.br/rucard/servicos"

# Identificável e com contato, como no Jupiter: quem administra o RUCard tem que
# conseguir saber quem está batendo, e falar com alguém.
AGENTE = "usp-mcp/0.1 (nao-oficial; +https://github.com/CaioCastro1/mcp-usp)"

# O cardápio muda uma vez por semana, mas a virada não tem hora conhecida — por
# isso um TTL curto o bastante para não atravessar a segunda-feira dormindo, com
# a validação por data cobrindo o resto.
TTL_MENU = 60 * 60 * 3
# Byte-idêntico em 27/08 e 31/08. Endereço e horário de RU não mudam por semana.
TTL_CATALOGO = 60 * 60 * 24 * 7

_TEMPO_LIMITE = 20


def transporte_http(url: str, corpo: str, cabecalhos: dict[str, str]) -> tuple[int, str]:
    """Transporte real. Injetável: nos testes entra um dublê que grava a chamada.

    Erro de rede NÃO é traduzido aqui: sobe como `OSError` (de que `URLError` e
    `TimeoutError` são subclasses) para o cliente traduzir. Um lugar só de
    tradução, e ela vale para qualquer transporte injetado — não só para este.
    """
    pedido = urllib.request.Request(
        url, data=corpo.encode("utf-8"), headers=cabecalhos, method="POST"
    )
    try:
        with urllib.request.urlopen(pedido, timeout=_TEMPO_LIMITE) as resposta:
            bruto = resposta.read()
            charset = resposta.headers.get_content_charset() or "utf-8"
            return resposta.status, bruto.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:  # 4xx/5xx ainda têm corpo, e ele é HTML
        return e.code, e.read().decode("utf-8", errors="replace")


def _data_do_dia(bruto_do_dia: dict) -> date | None:
    try:
        return datetime.strptime(bruto_do_dia.get("date", ""), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def semana_de(payload: dict) -> tuple[date | None, date | None]:
    """Primeiro e último dia que o payload cobre, ou (None, None).

    Público de propósito: quem formata a resposta precisa dizer QUAL semana está
    publicada quando o dia pedido não está nela (Invariante 7), e derivar isso
    duas vezes seria duas chances de divergir.
    """
    datas = [d for d in (_data_do_dia(x) for x in payload.get("meals") or []) if d]
    return (min(datas), max(datas)) if datas else (None, None)


class _Entrada:
    """Item do cache: quando entrou, o quê, e se já foi revalidado nesta janela."""

    __slots__ = ("t", "valor", "revalidada")

    def __init__(self, t: float, valor, revalidada: bool = False):
        self.t = t
        self.valor = valor
        self.revalidada = revalidada


class ClienteRucard:
    """Chamador das duas rotas públicas do RUCard, com política e cache.

    `transporte` recebe `(url, corpo, cabecalhos)` e devolve `(status, texto)`.
    `relogio` é injetável para que o teste de TTL verifique a REGRA, e não o
    valor da constante.
    """

    def __init__(self, transporte, *, hash_rucard: str | None = None, relogio=None,
                 ttl_menu: int = TTL_MENU, ttl_catalogo: int = TTL_CATALOGO,
                 permitir_escrita: bool = False):
        chave = hash_rucard if hash_rucard is not None else os.environ.get("RUCARD_HASH", "")
        if not chave:
            # Falhar cedo (Invariante 6): hash vazia nunca deveria chegar a uma
            # requisição, e a instrução de correção vai junto do fato.
            raise HashAusente(
                "RUCARD_HASH ausente ou vazia — copie o .env.example para .env. "
                "O valor é público: a hash é compartilhada e embutida no app "
                "oficial, não é credencial de ninguém."
            )
        self._chave = chave
        self._transporte = transporte
        self._relogio = relogio if relogio is not None else time.monotonic
        self._ttl_menu = ttl_menu
        self._ttl_catalogo = ttl_catalogo
        self._permitir_escrita = permitir_escrita
        self._cache: dict[str, _Entrada] = {}
        # Uma requisição por vez. Não é thread-safety por acaso: é o Invariante 5.
        # Quatro RUs em paralelo seriam quatro requisições simultâneas na mesma rota.
        self._porta = threading.Lock()

    # ------------------------------------------------------------------ rotas

    def menu(self, ru: str, dia: date | None = None) -> dict:
        """Cardápio da semana corrente de um RU.

        `dia` não vai para a API (ela não aceita data): serve para decidir se o
        que está em cache ainda responde à pergunta.
        """
        return self._buscar(
            rota="menu", ru=str(ru), chave_cache=f"menu/{ru}",
            ttl=self._ttl_menu, dia=dia,
        )

    def restaurantes(self) -> list:
        """Catálogo dos RUs. Cru: quem projeta é `catalogo.projetar`."""
        return self._buscar(
            rota="restaurants", ru=None, chave_cache="restaurants",
            ttl=self._ttl_catalogo, dia=None,
        )

    # ------------------------------------------------------------------ miolo

    def _buscar(self, *, rota: str, ru: str | None, chave_cache: str, ttl: int,
                dia: date | None):
        decisao = politica.decidir(rota, ru, self._permitir_escrita)
        if not decisao.permitida:
            # Antes de qualquer I/O: um RU negado não chega a tocar a rede.
            raise ConsultaNegada(decisao.motivo)

        with self._porta:
            entrada = self._cache.get(chave_cache)
            if entrada is not None and self._relogio() - entrada.t < ttl:
                if not self._precisa_revalidar(entrada, dia):
                    return entrada.valor

            valor = self._pedir(chave_cache)
            self._cache[chave_cache] = _Entrada(
                self._relogio(), valor, revalidada=entrada is not None
            )
            return valor

    @staticmethod
    def _precisa_revalidar(entrada: _Entrada, dia: date | None) -> bool:
        """Se o cache ainda dentro do TTL deixou de responder à pergunta.

        Só quando o dia pedido é POSTERIOR à semana guardada — é o sintoma da
        virada. Dia anterior não adianta rebuscar: a API não serve passado.
        E só uma vez por janela de TTL, senão uma pergunta sobre uma data que a
        API nunca vai cobrir vira uma requisição por pergunta.
        """
        if dia is None or entrada.revalidada:
            return False
        _, fim = semana_de(entrada.valor if isinstance(entrada.valor, dict) else {})
        return fim is not None and dia > fim

    def _pedir(self, rota_completa: str):
        try:
            status, texto = self._transporte(
                f"{URL_BASE}/{rota_completa}",
                urllib.parse.urlencode({"hash": self._chave}),
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": AGENTE,
                },
            )
        except OSError as exc:
            # TimeoutError, ConnectionError e urllib.error.URLError são todas
            # subclasses de OSError: um except cobre timeout e conexão recusada.
            raise RucardIndisponivel(
                f"o RUCard não respondeu em {rota_completa} (timeout ou conexão "
                "recusada). Tente de novo mais tarde."
            ) from exc

        if status != 200:
            # O corpo aqui é HTML do Tomcat. Ele NÃO entra na mensagem: são
            # 3.240 B que não respondem nada (Invariante 6 pede legível, não cru).
            raise RespostaInvalida(
                f"o RUCard respondeu HTTP {status} em {rota_completa}. A resposta "
                "de erro dele é uma página HTML do servidor de aplicação, não "
                "JSON, e foi descartada por não conter informação útil."
            )

        try:
            valor = json.loads(texto)
        except ValueError as exc:
            raise RespostaInvalida(
                f"a resposta do RUCard em {rota_completa} não é um JSON válido "
                "(provável página de manutenção ou erro em HTML com HTTP 200)."
            ) from exc

        # Em /menu, `message.error` é booleano DE VERDADE — ao contrário de
        # /restaurants, onde todo valor é string. As duas rotas não seguem a
        # mesma regra (§1.2), e é por isso que a checagem é por rota.
        if isinstance(valor, dict):
            mensagem = valor.get("message") or {}
            if mensagem.get("error"):
                raise RespostaInvalida(
                    f"o RUCard recusou {rota_completa}: "
                    f"{mensagem.get('message') or 'sem detalhe'}."
                )

        return valor
