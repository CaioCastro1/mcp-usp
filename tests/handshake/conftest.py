"""Handshake stdio compartilhado — peças comuns.

Existe porque o mesmo furo foi registrado três vezes no backlog: o adaptador
`main()` de cada servidor não tem teste, e **verde na suíte não é verde nele**.
Na trilha do Moodle isso escondeu um `main()` escrito contra a API antiga do SDK
com 99/99 testes passando; `--auto-verificar` reduziu a chance de repetir, e não
eliminou.

Três decisões de desenho, e nenhuma é estilo:

**Um teste, N servidores, por descoberta.** Os servidores saem de um glob em
`usp_mcp/*/server.py`, não de uma lista escrita à mão. Um quarto sistema entra
coberto no dia em que nascer, em vez de entrar com o mesmo furo pela quarta vez.
Há teste que falha se o glob não achar nada — descoberta silenciosamente vazia é
a forma mais fácil de esta suíte inteira virar decoração.

**Sem cliente MCP falso.** A docstring dos três `main()` dizia que testar isto
exigiria "um cliente MCP falso, o que testaria o SDK e não este projeto". As
duas metades estavam erradas: o cliente é JSON-RPC por um pipe (a classe abaixo),
e o que se testa não é o SDK — é se **o nosso adaptador casa com o SDK que está
instalado**, que é exatamente o que quebrou uma vez.

**Nada de rede da USP, nada de credencial.** `initialize` e `tools/list` são
respondidos pelo processo sem tocar em `chamar_ferramenta`: nos três servidores o
cliente da API só é construído na chamada da ferramenta. Por isso esta camada
roda no gate, ao lado da suíte offline, e não atrás de `USP_MCP_LIVE=1`.
"""
from __future__ import annotations

import json
import os
import pathlib
import select
import subprocess
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[2]

# Tempo generoso: a máquina do dono sobe um interpretador e importa o SDK. O
# limite existe para uma falha virar vermelho em segundos em vez de travar a
# suíte para sempre — que é o outro jeito de um teste deixar de verificar.
TEMPO_LIMITE_S = 30

MOTIVO_SEM_SDK = (
    "o SDK do MCP (pacote `mcp`) não está instalado neste ambiente, então não há "
    "adaptador stdio para exercitar. Rode `.venv/bin/python -m pip install -r "
    "requirements.txt`. Este skip NÃO é o caso normal: no ambiente do dono o SDK "
    "está presente e estes testes rodam no gate."
)


def _tem_sdk() -> bool:
    try:
        import mcp.server  # noqa: F401
    except ImportError:
        return False
    return True


com_sdk = pytest.mark.skipif(not _tem_sdk(), reason=MOTIVO_SEM_SDK)


def descobrir_servidores() -> list[str]:
    """Módulos `usp_mcp.<sistema>.server`, por descoberta e em ordem estável."""
    achados = sorted(RAIZ.glob("usp_mcp/*/server.py"))
    return [f"usp_mcp.{p.parent.name}.server" for p in achados]


def sistema_de(modulo: str) -> str:
    return modulo.split(".")[1]


class ClienteStdio:
    """Cliente MCP mínimo: JSON-RPC por linha, sobre os pipes do processo.

    Não é dublê de nada — é um cliente de verdade, pequeno. O servidor sob teste
    é o processo real, subido como o `.mcp.json` o sobe.
    """

    def __init__(
        self,
        modulo: str,
        comando: list[str] | None = None,
        cwd: pathlib.Path | str | None = None,
        env: dict[str, str] | None = None,
    ):
        # `comando`/`cwd` existem para a suíte do lançador (L1/L2), que precisa
        # subir o MESMO servidor por outro caminho e a partir de um cwd que não
        # é a raiz — que é exatamente o que esta suíte aqui nunca exercita, e
        # foi por isso que o `.mcp.json` relativo passou verde quebrado fora do
        # Claude Code. O default é o comportamento de sempre.
        self._modulo = modulo
        self._comando = comando or [sys.executable, "-m", modulo]
        self._cwd = str(cwd) if cwd is not None else str(RAIZ)
        # `env` existe para o E14, que precisa subir o MESMO servidor com
        # `USP_MCP_ENTREGA` explicitamente ligada e explicitamente desligada.
        # O default continua sendo herdar o ambiente, que é como o cliente MCP
        # de verdade sobe o processo — herdar é o comportamento sob teste em
        # todo o resto desta suíte, e não podia virar exceção por causa de um
        # teste. Passar um `env` é dizer "esta propriedade não depende de quem
        # rodou a suíte", que é exatamente o que E14 afirma.
        self._env = env
        self._proc: subprocess.Popen | None = None
        self._id = 0
        self.info: dict = {}
        # Preenchido quando a subida falha. Quem reporta é o teste, não a
        # fixture — ver a docstring de `servidor_vivo`.
        self.falha: str | None = None

    def __enter__(self) -> ClienteStdio:
        self._proc = subprocess.Popen(
            self._comando,
            cwd=self._cwd,
            env=({**os.environ, **self._env} if self._env is not None else None),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return self

    def __exit__(self, *_):
        proc = self._proc
        if proc is None:
            return
        # Fechar o stdin é o fim de linha normal de um servidor stdio; matar
        # depois é o seguro contra um servidor que não trate isso.
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    # ------------------------------------------------------------------ i/o

    def _escrever(self, mensagem: dict) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        self._proc.stdin.write(json.dumps(mensagem) + "\n")
        self._proc.stdin.flush()

    def _ler(self) -> dict:
        assert self._proc is not None and self._proc.stdout is not None
        prontos, _, _ = select.select([self._proc.stdout], [], [], TEMPO_LIMITE_S)
        if not prontos:
            raise AssertionError(
                f"{self._modulo} não respondeu em {TEMPO_LIMITE_S}s. "
                f"stderr: {self.stderr_disponivel()[:800]!r}"
            )
        linha = self._proc.stdout.readline()
        if not linha.strip():
            raise AssertionError(
                f"{self._modulo} fechou o stdout sem responder — o processo "
                f"provavelmente morreu. stderr: {self.stderr_disponivel()[:800]!r}"
            )
        return json.loads(linha)

    def pedir(self, metodo: str, params: dict | None = None) -> dict:
        self._id += 1
        self._escrever(
            {"jsonrpc": "2.0", "id": self._id, "method": metodo, "params": params or {}}
        )
        resposta = self._ler()
        if "error" in resposta:
            raise AssertionError(
                f"{self._modulo} respondeu erro JSON-RPC em {metodo}: "
                f"{resposta['error']}"
            )
        return resposta["result"]

    def notificar(self, metodo: str, params: dict | None = None) -> None:
        self._escrever({"jsonrpc": "2.0", "method": metodo, "params": params or {}})

    # ------------------------------------------------------------- inspeção

    def stderr_disponivel(self) -> str:
        """O que o processo escreveu em stderr SEM bloquear se não escreveu nada."""
        proc = self._proc
        if proc is None or proc.stderr is None:
            return ""
        prontos, _, _ = select.select([proc.stderr], [], [], 0)
        return proc.stderr.readline() if prontos else ""

    def vivo(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def apertar_mao(self) -> dict:
        """`initialize` + `notifications/initialized`, como um cliente real faz."""
        resultado = self.pedir(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "tests.handshake", "version": "0"},
            },
        )
        self.notificar("notifications/initialized")
        self.info = resultado
        return resultado


@pytest.fixture(scope="session", params=descobrir_servidores())
def servidor_vivo(request):
    """Um processo por servidor, com a mão já apertada, para a sessão inteira.

    Escopo de sessão por medida, não por gosto: um processo por teste custava
    67 s no gate (26 subidas de interpretador com o SDK), e 3 subidas custam ~8 s.
    O que cada teste exercita continua sendo o processo REAL — o que se
    compartilha é a subida, não a asserção.

    A subida a frio continua coberta: `initialize` acontece uma vez por
    processo, e H1 assere sobre o resultado guardado dessa subida.
    """
    if not _tem_sdk():
        pytest.skip(MOTIVO_SEM_SDK)
    modulo = request.param
    with ClienteStdio(modulo) as cliente:
        # A falha de subida é CAPTURADA e guardada, nunca levantada aqui: uma
        # fixture que levanta transforma `FAILED` em `ERROR`, e o §4 do
        # CONVENTIONS.md registra que erro de setup não é vermelho honesto — é
        # justamente o caso mais importante desta suíte (o servidor não sobe)
        # que ficaria com a cara errada.
        try:
            cliente.apertar_mao()
        except Exception as exc:  # noqa: BLE001 — o diagnóstico vai para o teste
            cliente.falha = f"{modulo} não completou o handshake: {exc}"
        yield modulo, cliente
