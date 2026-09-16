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

**Gentileza com a USP** (Invariante 5), com TRÊS regras de cache, não uma:

- *TTL* protege a USP. Três horas para o cardápio, uma semana para o catálogo —
  colado na taxa de mudança do dado, e não na frequência da pergunta. O catálogo
  veio byte-idêntico em duas capturas separadas por quatro dias.
- *Validação por data* protege a resposta. A rota não aceita parâmetro de data:
  devolve sempre a semana corrente. Na segunda 31/08, às 19:22, a semana já era a
  nova — um cache de horas antes ainda teria a anterior, e devolvê-lo seria
  responder o cardápio da semana passada com cara de resposta certa. Quando o dia
  pedido é posterior à semana que está em cache, o cliente revalida **uma vez** por
  janela de TTL: o suficiente para pegar a virada, e pouco o bastante para uma
  pergunta sobre Natal não virar uma requisição por pergunta. "Uma vez por
  janela" quer dizer uma por janela de TTL: janela nova nasce com a proteção
  armada, e só a refeita POR DATA a gasta.
- *Falha lembrada* protege a USP de novo, do outro lado. Sucesso entrava no
  cache e falha não, então uma pergunta pela semana inteira pedia sete vezes o
  RU que estava fora do ar. A falha fica guardada por alguns minutos — o
  bastante para uma varredura de semana caber numa tentativa só, e pouco o
  bastante para o RU voltar ao ar sozinho assim que a USP voltar.
"""
from __future__ import annotations

import http.client
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
    ErroRucard,
    HashAusente,
    RespostaInvalida,
    RucardIndisponivel,
)

__all__ = [
    "ClienteRucard", "transporte_http", "URL_BASE", "AGENTE",
    "TTL_MENU", "TTL_CATALOGO", "TTL_FALHA",
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

# Quanto tempo uma FALHA é lembrada. Sucesso entrava no cache e falha não, então
# uma pergunta pela semana inteira pedia sete vezes o RU que estava fora do ar
# (medido: 7 chamadas para um RU e 1 para cada um dos outros três). Com o tempo
# limite de 20 s, são até 140 s martelando justamente quem já não está bem — o
# oposto do que o cache existe para fazer.
#
# Curta de propósito, e o número sai de uma conta: a janela só precisa cobrir uma
# varredura de semana inteira, que no pior caso (os quatro RUs fora) gasta
# 4 × 20 s antes de o segundo dia começar. Cinco minutos cobrem isso com folga e
# devolvem o RU ao ar logo depois que a USP voltar. Uma janela do tamanho do
# TTL_MENU transformaria uma falha passageira em três horas de RU calado.
TTL_FALHA = 60 * 5

_TEMPO_LIMITE = 20

# O que pode dar errado no fio, e por que são DUAS famílias e não uma.
#
# `OSError` cobre timeout, conexão recusada e DNS — `URLError` e `TimeoutError`
# são subclasses dele. O que ele **não** cobre é `http.client.HTTPException`:
# `IncompleteRead` (o servidor fecha antes de completar o `Content-Length`) e
# `BadStatusLine` (a primeira linha não é uma linha de status) herdam só de
# `HTTPException`. Medido contra servidor local: as duas subiam cruas até a
# fronteira MCP, onde o SDK as classifica como crash e o modelo recebe a
# genérica de 29 bytes. `RemoteDisconnected` é as duas coisas ao mesmo tempo
# (`ConnectionResetError` e `BadStatusLine`) e já era pega — o que engana.
_FALHAS_DE_TRANSPORTE = (OSError, http.client.HTTPException)

# Limite do detalhe técnico que entra na mensagem. `BadStatusLine` carrega a
# linha inteira que o servidor mandou; é o mesmo raciocínio dos 3.240 B de HTML
# do Tomcat, que também não sobem.
_TETO_DETALHE = 120


def transporte_http(url: str, corpo: str, cabecalhos: dict[str, str]) -> tuple[int, str]:
    """Transporte real. Injetável: nos testes entra um dublê que grava a chamada.

    Erro de fio NÃO é traduzido aqui: sobe como `OSError` **ou** como
    `http.client.HTTPException` para o cliente traduzir. Um lugar só de tradução,
    e ela vale para qualquer transporte injetado — não só para este. As duas
    famílias porque nem toda falha de transporte é `OSError`: corpo cortado e
    linha de status inválida não são.
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
        # `e.read()` pode quebrar no meio (o corpo do erro também vem pelo fio).
        # Não há `try` aqui de propósito: a exceção sobe e cai no mesmo `except`
        # do cliente, que é o único lugar de tradução deste sistema.
        return e.code, e.read().decode("utf-8", errors="replace")


def _detalhe(erro: BaseException) -> str:
    """Classe e mensagem da exceção, cortadas no teto."""
    texto = str(erro).strip()
    if len(texto) > _TETO_DETALHE:
        texto = texto[:_TETO_DETALHE] + "…"
    return f"{type(erro).__name__}: {texto}" if texto else type(erro).__name__


def _indisponivel(rota: str, erro: BaseException) -> RucardIndisponivel:
    """Traduz a falha de transporte, distinguindo os DOIS casos.

    "Timeout ou conexão recusada" é diagnóstico errado para um servidor que
    respondeu e respondeu mal — e quem lê decide coisas diferentes nos dois.
    """
    if isinstance(erro, http.client.HTTPException) and not isinstance(erro, OSError):
        return RucardIndisponivel(
            f"a resposta do RUCard em {rota} chegou quebrada e não dá para ler "
            f"({_detalhe(erro)}). O servidor respondeu, mas o que veio no fio não "
            "é uma resposta HTTP íntegra: corpo cortado antes do fim, ou primeira "
            "linha que não é status. Isto é transporte, não cardápio — não é "
            "'esse restaurante não tem comida hoje'."
        )
    return RucardIndisponivel(
        f"o RUCard não respondeu em {rota} — timeout ou conexão recusada "
        f"({_detalhe(erro)}). Tente de novo mais tarde."
    )


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


def _lembrada(erro: ErroRucard) -> ErroRucard:
    """A mesma falha, dizendo que é lembrada e que a chamada não se repetiu.

    Devolver a exceção original calada faria "tentei agora e falhou" e "falhou
    há pouco e eu não insisti" lerem igual, e são fatos diferentes para quem
    decide o que fazer em seguida. A classe é preservada: ela é o que separa
    "não respondeu" de "respondeu lixo", e as duas têm curas diferentes.
    """
    return type(erro)(
        f"{erro} Esta é a falha da tentativa anterior a esta mesma rota, "
        "lembrada por alguns minutos: a chamada NÃO foi repetida agora, para "
        "não insistir com um serviço que acabou de falhar. Ela volta a sair "
        "sozinha quando essa janela passar."
    )


class ClienteRucard:
    """Chamador das duas rotas públicas do RUCard, com política e cache.

    `transporte` recebe `(url, corpo, cabecalhos)` e devolve `(status, texto)`.
    `relogio` é injetável para que o teste de TTL verifique a REGRA, e não o
    valor da constante.
    """

    def __init__(self, transporte, *, hash_rucard: str | None = None, relogio=None,
                 ttl_menu: int = TTL_MENU, ttl_catalogo: int = TTL_CATALOGO,
                 ttl_falha: int = TTL_FALHA, permitir_escrita: bool = False):
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
        self._ttl_falha = ttl_falha
        self._permitir_escrita = permitir_escrita
        self._cache: dict[str, _Entrada] = {}
        # Falha tem cache próprio, e não uma entrada especial no de cima: TTL
        # diferente, e um valor bom nunca deve ser sombreado por uma falha
        # posterior nem o contrário.
        self._falhas: dict[str, tuple[float, ErroRucard]] = {}
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
            no_ttl = entrada is not None and self._relogio() - entrada.t < ttl
            if no_ttl and not self._precisa_revalidar(entrada, dia):
                return entrada.valor

            # Falha recente na mesma rota: não repete. É o que faz a semana
            # inteira custar UMA tentativa por RU fora do ar, e não sete.
            falha = self._falhas.get(chave_cache)
            if falha is not None and self._relogio() - falha[0] < self._ttl_falha:
                raise _lembrada(falha[1])

            try:
                valor = self._pedir(chave_cache, rota=rota)
            except ErroRucard as exc:
                self._falhas[chave_cache] = (self._relogio(), exc)
                raise

            self._falhas.pop(chave_cache, None)
            # `no_ttl` é o que faz esta refeita ter sido uma REVALIDAÇÃO POR
            # DATA: havia entrada viva e ela deixou de responder à pergunta. Uma
            # refeita por TTL vencido não é isso, e marcá-la como se fosse
            # desligava a proteção a partir da primeira expiração — toda entrada
            # nova nasceria "já revalidada" e a virada de semana passaria
            # despercebida pelo resto da vida do processo. Janela nova nasce com
            # a proteção armada; só quem gastou a revalidação a marca.
            self._cache[chave_cache] = _Entrada(
                self._relogio(), valor, revalidada=no_ttl
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

    def _pedir(self, rota_completa: str, *, rota: str):
        """`rota_completa` é o que vai na URL (`menu/6`); `rota` é a família
        (`menu`, `restaurants`). Obrigatório e sem default: a validação da
        resposta é POR ROTA, e um default silencioso a desligaria sem avisar."""
        try:
            status, texto = self._transporte(
                f"{URL_BASE}/{rota_completa}",
                urllib.parse.urlencode({"hash": self._chave}),
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": AGENTE,
                },
            )
        except _FALHAS_DE_TRANSPORTE as exc:
            raise _indisponivel(rota_completa, exc) from exc

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

        if rota == "restaurants" and not (isinstance(valor, list) and valor):
            # HTTP 200 com corpo `[]` ou `{}` não é "o RUCard não tem
            # restaurante": é resposta que não responde. Recusar aqui, ANTES do
            # cache, é o que impede o TTL de uma semana de congelar o vazio — e
            # é o que impede a ferramenta de ter de explicar por que o RU 6 não
            # está num catálogo que veio sem RU nenhum.
            raise RespostaInvalida(
                f"o catálogo de restaurantes veio vazio em {rota_completa}, com "
                "HTTP 200. Isso não é uma resposta: o RUCard publica 18 "
                "restaurantes, e uma lista sem nenhum é falha de leitura, não "
                "ausência de bandejão. Sem o catálogo não há nome, endereço, "
                "horário nem preço para montar resposta nenhuma."
            )

        return valor
