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

# Caminho que caracteriza arquivo servido pelo webservice — a allowlist do
# download. Não é o mesmo endpoint das funções (`/webservice/rest/server.php`).
_PREFIXO_ARQUIVO = "/webservice/pluginfile.php/"

# Timeout do download. Maior arquivo medido em 01/09: 6,3 MB. Mais generoso que o
# das funções porque aqui o custo é banda, não processamento do Moodle.
_TIMEOUT_DOWNLOAD_SEGUNDOS = 120

# Teto por arquivo. Maior medido: 6,3 MB — folga deliberada de ~8x.
TETO_ARQUIVO_BYTES = 50 * 1024 * 1024

# Timeout do transporte HTTP padrão. Não é configurável por parâmetro porque
# nenhum teste exercita esse caminho (só tests/moodle/test_live.py, pulado) —
# um valor fixo e conservador é suficiente até haver dado medido que peça algo
# diferente (decisão de §9, não conveniência de código).
# Medido ao vivo em 31/08/2026: `core_enrol_get_users_courses` levou **14,7 s**
# para devolver as 74 matrículas (104 kB). Com o teto anterior de 15 s, a chamada
# mais pesada da ferramenta `material` rodava a 2% de margem — e estourou na
# primeira execução real, com a suíte inteira verde. Não baixe este valor sem
# remedir: a suíte não alcança este caminho (§9, 31/08).
_TIMEOUT_PADRAO_SEGUNDOS = 60


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


def _levantar_se_erro(rotulo: str, resposta) -> None:
    """Traduz o erro do Moodle, e é chamada pelos DOIS caminhos.

    Existe como função e não embutida em `chamar` porque o download
    (`baixar`) recebe o mesmo formato de erro por outro transporte. Duplicar a
    tradução criaria duas mensagens diferentes para `invalidtoken`, e a
    divergência só apareceria no dia em que o token expirasse.
    """
    if not (isinstance(resposta, dict) and "errorcode" in resposta):
        return
    errorcode = resposta["errorcode"]
    if errorcode == "invalidtoken":
        raise TokenInvalido(
            "Token do Moodle inválido ou expirado — gere um novo e "
            "atualize MOODLE_TOKEN no .env (ver §8 do SPEC1.md)."
        )
    mensagem = resposta.get("message", "") or resposta.get("error", "")
    raise ErroMoodle(f"Moodle recusou {rotulo}: {errorcode} — {mensagem}")


def _transporte_download_padrao(*, url: str, dados: dict, teto_bytes: int):
    """POST form-urlencoded que devolve (content_type, bytes). Só stdlib.

    Lê no máximo `teto_bytes + 1` de propósito: é assim que um arquivo sem
    `filesize` utilizável ainda respeita o teto, e o byte extra é o que permite
    detectar que o teto foi ultrapassado em vez de truncar calado.
    """
    corpo = urllib.parse.urlencode(dados).encode("utf-8")
    requisicao = urllib.request.Request(url, data=corpo, method="POST")
    with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_DOWNLOAD_SEGUNDOS) as resp:
        return resp.headers.get("Content-Type", ""), resp.read(teto_bytes + 1)


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
        transporte_download=None,
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
        self.transporte_download = (
            transporte_download
            if transporte_download is not None
            else _transporte_download_padrao
        )
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

        _levantar_se_erro(funcao, resposta)

        return resposta

    def baixar(
        self,
        fileurl: str,
        *,
        tamanho_esperado: int | None = None,
        teto_bytes: int = TETO_ARQUIVO_BYTES,
    ) -> bytes:
        """Baixa UM arquivo do webservice do Moodle. O token vai no CORPO.

        Medido em 01/09/2026 (§9): o corpo do POST autentica igual à query
        string, e por isso a credencial nunca precisa entrar numa URL. Também
        medido: erro de credencial chega com **HTTP 200** e `Content-Type:
        application/json` — checar status não serve de nada aqui.

        A restrição de origem é a allowlist deste caminho. Ela roda antes de
        qualquer I/O: como o token viaja no corpo, uma URL de outro host
        entregaria a credencial do dono a esse host.
        """
        esperado = f"{self.url}{_PREFIXO_ARQUIVO}"
        if not fileurl.startswith(esperado):
            raise FuncaoBloqueada(
                f"Download recusado: {fileurl!r} não começa com {esperado!r}. "
                "O token vai no corpo da requisição, então baixar de outro "
                "endereço entregaria a sua credencial a ele."
            )

        try:
            content_type, corpo = self.transporte_download(
                url=fileurl,
                dados={"token": self._token.get()},
                teto_bytes=teto_bytes,
            )
        except OSError as exc:
            raise MoodleIndisponivel(
                "O e-Disciplinas não respondeu ao download (timeout ou conexão "
                "recusada). Tente de novo mais tarde."
            ) from exc

        if "json" in (content_type or "").lower():
            try:
                _levantar_se_erro("o download do arquivo", json.loads(corpo))
            except ValueError as exc:
                raise RespostaIlegivel(
                    "O e-Disciplinas devolveu algo que não é o arquivo nem um "
                    "erro compreensível no lugar do download."
                ) from exc
            raise RespostaIlegivel(
                "O e-Disciplinas devolveu JSON no lugar do arquivo, sem "
                "`errorcode` para explicar o motivo."
            )

        if len(corpo) > teto_bytes:
            raise ErroMoodle(
                f"O arquivo passa do teto de {teto_bytes} bytes e não foi "
                "gravado. Baixe pelo e-Disciplinas."
            )

        if tamanho_esperado is not None and len(corpo) != tamanho_esperado:
            raise ErroMoodle(
                f"O download veio incompleto: esperava {tamanho_esperado} bytes "
                f"e recebeu {len(corpo)}. Nada foi gravado."
            )

        return corpo
