"""Um servidor local que responde ERRADO, de três jeitos que a USP responde.

Por que um servidor de socket cru e não um dublê de transporte: as três
patologias desta lista não são exceções que alguém levanta — são exceções que o
`http.client` levanta ao tentar ler um fio que não segue o protocolo. Um dublê
que faça `raise IncompleteRead(...)` prova que o `except` pega a classe; ele não
prova que a classe é essa. Quem decide isso é a biblioteca padrão lendo bytes
reais, e é por isso que aqui entram bytes reais.

As três, medidas nesta máquina (a `sonda` que gerou esta lista está no corpo do
`test_transporte_no_fio` de cada sistema):

- `incompleto` — `Content-Length` maior que o corpo, e o servidor fecha. Levanta
  `http.client.IncompleteRead`, que **não** é `OSError`.
- `linha_ruim` — a primeira linha não é uma linha de status HTTP. Levanta
  `http.client.BadStatusLine`, que também **não** é `OSError`.
- `desconecta` — fecha sem escrever um byte. Levanta
  `http.client.RemoteDisconnected`, que é as duas coisas: `ConnectionResetError`
  (logo `OSError`) e `BadStatusLine`. É a que separa os dois sistemas — o
  `except OSError` do RUCard já a pegava, o `except (URLError, TimeoutError)` do
  Jupiter não.

Nada aqui toca a rede da USP: escuta em `127.0.0.1` numa porta que o sistema
escolhe, atende UMA conexão e morre. E guarda o que recebeu, para o teste poder
assertar sobre o que FOI ENVIADO e não só sobre a exceção que voltou.
"""
from __future__ import annotations

import socket
import threading

__all__ = ["MODOS", "ServidorRuim"]

# O corpo que cada modo escreve no fio. `desconecta` escreve nada, de propósito.
MODOS: dict[str, bytes] = {
    "incompleto": (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"Content-Length: 4096\r\n"
        b"\r\n"
        b"comeco de corpo que nunca chega ao fim"
    ),
    "linha_ruim": b"isto nao e uma linha de status HTTP\r\n\r\n",
    "desconecta": b"",
}

_TEMPO_LIMITE_SOCKET = 5


class ServidorRuim:
    """Escuta em `127.0.0.1`, atende uma conexão e responde mal.

    Use como context manager. `url(caminho)` monta o endereço; `pedido` traz os
    bytes crus que o cliente mandou, depois que a conexão fechou.
    """

    def __init__(self, modo: str):
        assert modo in MODOS, f"modo {modo!r} não existe; use {sorted(MODOS)}"
        self._modo = modo
        self.pedido: bytes = b""
        self._socket = socket.socket()
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(1)
        self.porta = self._socket.getsockname()[1]
        self._thread = threading.Thread(target=self._atender, daemon=True)

    # ------------------------------------------------------------------ uso
    def __enter__(self) -> "ServidorRuim":
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._thread.join(timeout=_TEMPO_LIMITE_SOCKET)
        try:
            self._socket.close()
        except OSError:  # pragma: no cover — já fechado pelo laço
            pass

    def url(self, caminho: str = "/") -> str:
        return f"http://127.0.0.1:{self.porta}{caminho}"

    # ---------------------------------------------------------------- miolo
    def _atender(self) -> None:
        try:
            conexao, _ = self._socket.accept()
        except OSError:  # pragma: no cover — só se ninguém conectar
            return
        with conexao:
            conexao.settimeout(_TEMPO_LIMITE_SOCKET)
            self.pedido = _ler_requisicao(conexao)
            corpo = MODOS[self._modo]
            if corpo:
                try:
                    conexao.sendall(corpo)
                except OSError:  # pragma: no cover — cliente já desistiu
                    pass
        try:
            self._socket.close()
        except OSError:  # pragma: no cover
            pass


def _ler_requisicao(conexao: socket.socket) -> bytes:
    """Cabeçalhos até a linha em branco, e o corpo que o `Content-Length` promete.

    Ler o pedido inteiro antes de responder não é zelo: sem isso o `sendall` da
    resposta pode chegar antes de o cliente terminar de escrever, e o que o
    teste mediria seria um `ECONNRESET` do próprio teste, não a patologia.
    """
    dados = b""
    while b"\r\n\r\n" not in dados:
        try:
            pedaco = conexao.recv(65536)
        except OSError:  # pragma: no cover
            return dados
        if not pedaco:
            return dados
        dados += pedaco

    cabecalhos, _, resto = dados.partition(b"\r\n\r\n")
    tamanho = 0
    for linha in cabecalhos.split(b"\r\n"):
        nome, _, valor = linha.partition(b":")
        if nome.strip().lower() == b"content-length":
            try:
                tamanho = int(valor.strip())
            except ValueError:  # pragma: no cover
                tamanho = 0
    while len(resto) < tamanho:
        try:
            pedaco = conexao.recv(65536)
        except OSError:  # pragma: no cover
            break
        if not pedaco:
            break
        resto += pedaco
    return cabecalhos + b"\r\n\r\n" + resto
