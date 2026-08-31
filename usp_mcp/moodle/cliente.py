"""Camada 2 — o cliente: transporte, política na fronteira, e erro legível.

A política (Invariante 2) é aplicada AQUI, dentro de `chamar`, de propósito: se
a checagem morasse só na camada de ferramenta (o wrapper MCP), qualquer código
novo que instanciasse `ClienteMoodle` direto — um script de depuração, uma
segunda ferramenta — contornaria a allowlist sem perceber. O cliente é o único
lugar por onde toda chamada ao web service passa, então é o único lugar onde a
política pode ser garantida e não apenas convencionada.

Este módulo é deliberadamente incapaz de iterar sobre funções do Moodle: não
existe `chamar_varias`, `sweep`, nem nada parecido. Um laço sobre as 447
funções habilitadas neste token passaria por `mod_quiz_start_attempt` e
`mod_assign_submit_for_grading` com a credencial do dono (Regra de Ouro, §3.1)
— a defesa mais confiável contra isso é a ausência do método, não uma checagem
em tempo de execução que alguém pode esquecer de manter.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from . import politica
from .erros import (
    ErroMoodle,
    FuncaoBloqueada,
    MoodleIndisponivel,
    RespostaIlegivel,
    TokenInvalido,
)

_URL_SUFIXO_WEBSERVICE = "/webservice/rest/server.php"

# Timeout do transporte HTTP padrão. Não é configurável por parâmetro porque
# nenhum teste exercita esse caminho (só tests/moodle/test_live.py, pulado) —
# um valor fixo e conservador é suficiente até haver dado medido que peça algo
# diferente (decisão de §9, não conveniência de código).
_TIMEOUT_PADRAO_SEGUNDOS = 15


class _TokenOculto:
    """Guarda o token sem deixar `repr`/`str` (nem o despejo de `vars()` de
    quem o contém) imprimirem o valor por acidente (Invariante 3).

    `__slots__` é o que faz isso valer também para `vars(cliente)`: o atributo
    do cliente aponta para um objeto deste tipo, e `str()` de um dicionário
    chama `repr()` em cada valor — nunca o valor bruto. `get()` é a única
    porta de saída, usada só na hora de montar o payload da requisição.
    """

    __slots__ = ("_valor",)

    def __init__(self, valor: str) -> None:
        self._valor = valor

    def get(self) -> str:
        return self._valor

    def __repr__(self) -> str:  # pragma: no cover — exercitado via vars(c)
        return "TokenOculto(***)"

    def __str__(self) -> str:  # pragma: no cover
        return "***"


def _transporte_padrao(*, url: str, dados: dict) -> dict:
    """Transporte HTTP real, só stdlib (sem dependência nova).

    POST form-urlencoded — é o que o web service REST do Moodle espera. Erro
    de rede e JSON inválido não são tratados aqui: sobem como `OSError` e
    `ValueError` (ou subclasses, como `json.JSONDecodeError` e
    `urllib.error.URLError`) para `chamar` traduzir num erro legível, exigindo
    só um lugar de tradução em vez de duplicá-la no transporte injetável.
    """
    corpo = urllib.parse.urlencode(dados).encode("utf-8")
    requisicao = urllib.request.Request(url, data=corpo, method="POST")
    with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_PADRAO_SEGUNDOS) as resp:
        bruto = resp.read()
    return json.loads(bruto)


class ClienteMoodle:
    """Uma função por invocação, escolhida à mão (Regra de Ouro, §3.1).

    Deliberadamente SEM método que itere sobre funções: um sweep sobre as 447
    passa por `start_attempt` e `submit_for_grading` com o token do dono.
    """

    def __init__(
        self,
        *,
        token: str,
        url: str,
        transporte=None,
        permitir_escrita: bool = False,
    ) -> None:
        # Falhar cedo (Invariante 6): token vazio nunca deveria chegar a uma
        # requisição. A instrução de correção vai na mensagem, não só o fato.
        if not token:
            raise ErroMoodle(
                "MOODLE_TOKEN ausente ou vazio — configure-o no .env "
                "(ver .env.example) antes de usar o cliente."
            )
        self._token = _TokenOculto(token)
        self.url = url
        self.transporte = transporte if transporte is not None else _transporte_padrao
        self.permitir_escrita = permitir_escrita

    def chamar(self, funcao: str, **params) -> dict:
        """Aplica a política, emite EXATAMENTE UMA requisição, traduz o erro.

        A política roda antes de qualquer I/O: uma função negada nunca chega
        a tocar o transporte (T21), nem mesmo com `permitir_escrita=True`
        (T22 — essa flag não abre o bloqueio permanente do §2.2).
        """
        decisao = politica.decidir(funcao, permitir_escrita=self.permitir_escrita)
        if not decisao.permitida:
            raise FuncaoBloqueada(decisao.motivo)

        url = f"{self.url}{_URL_SUFIXO_WEBSERVICE}"
        dados = {
            "wstoken": self._token.get(),
            "wsfunction": funcao,
            "moodlewsrestformat": "json",
            **params,
        }

        try:
            resposta = self.transporte(url=url, dados=dados)
        except ValueError as exc:
            # JSON inválido com HTTP 200 — o caso real mais comum é página de
            # manutenção em HTML. Não deixar isso virar KeyError/JSONDecodeError
            # cru mais adiante (Invariante 6).
            raise RespostaIlegivel(
                f"{funcao}: a resposta do e-Disciplinas não é um JSON válido "
                "(provável página de manutenção ou erro HTML com HTTP 200)."
            ) from exc
        except OSError as exc:
            # TimeoutError é subclasse de OSError, assim como ConnectionError e
            # urllib.error.URLError — cobre timeout e recusa de conexão com um
            # único except.
            raise MoodleIndisponivel(
                f"{funcao}: o Moodle/e-Disciplinas não respondeu (timeout ou "
                "conexão recusada). Tente de novo mais tarde."
            ) from exc

        if isinstance(resposta, dict) and "errorcode" in resposta:
            errorcode = resposta["errorcode"]
            mensagem = resposta.get("message", "")
            if errorcode == "invalidtoken":
                raise TokenInvalido(
                    "Token do Moodle inválido ou expirado — gere um novo e "
                    "atualize MOODLE_TOKEN no .env (ver §8 do SPEC1.md)."
                )
            # Erro real do Moodle: repassado legível, com o errorcode cru
            # preservado (Invariante 6 — não engolir, não normalizar).
            raise ErroMoodle(f"Moodle recusou {funcao}: {errorcode} — {mensagem}")

        return resposta
