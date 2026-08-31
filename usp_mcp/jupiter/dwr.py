"""Envelope DWR: decodificar a resposta e serializar a requisição.

O JupiterWeb não fala REST. Fala DWR — RPC Java sobre HTTP — e devolve um
objeto JavaScript dentro de um envelope que começa com `throw`. Não é JSON
válido: as chaves vêm sem aspas.

**Por que um parser e não uma conversão por expressão regular.** A saída
carrega ementa, objetivos e bibliografia — prosa livre escrita por docentes.
Um texto que contenha `, algo:` faria um regex de "põe aspas nas chaves"
corromper o valor silenciosamente. O parser abaixo distingue o que está dentro
de string do que é estrutura, que é justamente o que o regex não faz.

**Por que não desserializar executando.** O corpo vem da rede. Rodar o que a
rede manda é entregar a máquina; o parser lê e nunca roda — há teste para isso.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from usp_mcp.jupiter.erros import JupiterErro, RespostaInvalida

__all__ = ["decodificar", "serializar", "JupiterErro", "RespostaInvalida"]

_FIM = "//#DWR-END#"
_CHAMADA = re.compile(r'handle(Callback|Exception)\("[^"]*","[^"]*",')

_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
_LITERAIS = {"null": None, "true": True, "false": False}


class _Leitor:
    """Descida recursiva sobre o subconjunto de literal JS que o DWR emite."""

    def __init__(self, texto: str, i: int):
        self.t = texto
        self.i = i

    def erro(self, o_que: str) -> RespostaInvalida:
        return RespostaInvalida(f"{o_que} na posição {self.i} do envelope DWR")

    def espaco(self) -> None:
        while self.i < len(self.t) and self.t[self.i] in " \t\r\n":
            self.i += 1

    def valor(self):
        self.espaco()
        if self.i >= len(self.t):
            raise self.erro("envelope termina no meio de um valor")
        c = self.t[self.i]
        if c == "{":
            return self.objeto()
        if c == "[":
            return self.lista()
        if c == '"':
            return self.texto()
        for nome, valor in _LITERAIS.items():
            if self.t.startswith(nome, self.i):
                self.i += len(nome)
                return valor
        return self.numero()

    def objeto(self) -> dict:
        self.i += 1  # {
        obj: dict = {}
        self.espaco()
        if self.i < len(self.t) and self.t[self.i] == "}":
            self.i += 1
            return obj
        while True:
            self.espaco()
            chave = self.texto() if self.t[self.i : self.i + 1] == '"' else self.identificador()
            self.espaco()
            if self.t[self.i : self.i + 1] != ":":
                raise self.erro("esperava ':' depois da chave")
            self.i += 1
            obj[chave] = self.valor()
            self.espaco()
            sinal = self.t[self.i : self.i + 1]
            self.i += 1
            if sinal == "}":
                return obj
            if sinal != ",":
                raise self.erro("esperava ',' ou '}'")

    def lista(self) -> list:
        self.i += 1  # [
        itens: list = []
        self.espaco()
        if self.i < len(self.t) and self.t[self.i] == "]":
            self.i += 1
            return itens
        while True:
            itens.append(self.valor())
            self.espaco()
            sinal = self.t[self.i : self.i + 1]
            self.i += 1
            if sinal == "]":
                return itens
            if sinal != ",":
                raise self.erro("esperava ',' ou ']'")

    def identificador(self) -> str:
        inicio = self.i
        while self.i < len(self.t) and (self.t[self.i].isalnum() or self.t[self.i] in "_$"):
            self.i += 1
        if inicio == self.i:
            raise self.erro("esperava uma chave")
        return self.t[inicio : self.i]

    def texto(self) -> str:
        self.i += 1  # "
        partes: list[str] = []
        while True:
            if self.i >= len(self.t):
                raise self.erro("string sem fechamento")
            c = self.t[self.i]
            if c == '"':
                self.i += 1
                return "".join(partes)
            if c != "\\":
                partes.append(c)
                self.i += 1
                continue
            fuga = self.t[self.i + 1 : self.i + 2]
            if fuga == "u":
                partes.append(chr(int(self.t[self.i + 2 : self.i + 6], 16)))
                self.i += 6
            elif fuga in _ESCAPES:
                partes.append(_ESCAPES[fuga])
                self.i += 2
            else:
                raise self.erro(f"escape desconhecido \\{fuga}")

    def numero(self):
        inicio = self.i
        while self.i < len(self.t) and self.t[self.i] in "-+.eE0123456789":
            self.i += 1
        bruto = self.t[inicio : self.i]
        if not bruto:
            raise self.erro("token que não é objeto, lista, string, literal nem número")
        try:
            return int(bruto)
        except ValueError:
            try:
                return float(bruto)
            except ValueError:
                raise self.erro(f"número ilegível: {bruto!r}") from None


def decodificar(corpo: str):
    """Extrai o objeto (ou a lista) de uma resposta DWR.

    Levanta `JupiterErro` quando a USP respondeu `handleException` — o que ela
    faz com **HTTP 200**, então esta é a única fronteira onde o erro pode ser
    percebido. Levanta `RespostaInvalida` quando o corpo não é um envelope
    íntegro.
    """
    if _FIM not in corpo:
        raise RespostaInvalida(
            "envelope DWR sem o marcador de fim: resposta truncada, ou o corpo "
            "não veio do endpoint DWR (uma rota desconhecida devolve a tela de "
            "login em HTML)."
        )

    achado = _CHAMADA.search(corpo)
    if achado is None:
        raise RespostaInvalida("envelope sem handleCallback nem handleException")

    payload = _Leitor(corpo, achado.end()).valor()

    if achado.group(1) == "Exception":
        mensagem = None
        if isinstance(payload, dict):
            mensagem = payload.get("localizedMessage") or payload.get("message")
        # Só a mensagem atravessa. O stackTrace e o javaClassName ficam aqui:
        # 46 frames que custam mais que a resposta certa e vazam classe interna.
        raise JupiterErro(mensagem or "o JupiterWeb recusou o pedido, sem mensagem.")

    return payload


def serializar(*, metodo: str, consulta: str, params: dict) -> str:
    """Monta o corpo `text/plain` da chamada DWR (§4.2 de notas/jupiter-recon.md).

    Objetos vão por referência: cada valor ganha uma linha `c0-eN` própria e o
    parâmetro só aponta para ela. Formato lido em `dwr/engine.js`, não adivinhado.
    """
    linhas = [
        "callCount=1",
        "windowName=",
        "c0-scriptName=ControlePublicoDWR",
        f"c0-methodName={metodo}",
        "c0-id=0",
        f"c0-param0=string:{quote(consulta, safe='')}",
    ]

    referencias = []
    for n, (chave, valor) in enumerate(params.items(), start=1):
        rotulo = f"c0-e{n}"
        if isinstance(valor, bool):
            raise ValueError("o DWR desta fatia não usa booleano")
        if isinstance(valor, int):
            linhas.append(f"{rotulo}=number:{valor}")
        else:
            linhas.append(f"{rotulo}=string:{quote(str(valor), safe='')}")
        referencias.append(f"{chave}:reference:{rotulo}")

    linhas.append("c0-param1=Object_Object:{" + ", ".join(referencias) + "}")
    linhas += [
        "batchId=0",
        "instanceId=0",
        "page=%2Fjupiterweb%2FjupCarreira.jsp",
        "scriptSessionId=0000000000000000",
    ]
    return "\n".join(linhas)
