"""Erros legíveis (Invariante 6).

O Jupiter tem uma particularidade que torna estas classes mais do que estilo:
**ele devolve HTTP 200 no erro**. Um cliente que discrimine por status code
produz exatamente o silêncio que o Invariante 6 proíbe, e a distinção entre
"sigla não existe" e "a USP devolveu lixo" só existe se alguém a criar aqui.
"""
from __future__ import annotations


class ErroJupiter(Exception):
    """Base. Toda mensagem daqui deve dizer o que houve em português."""


class JupiterErro(ErroJupiter):
    """`handleException` do lado da USP — a aplicação recusou o pedido.

    Carrega SÓ a mensagem. O corpo cru traz 46 frames de stack trace do Tomcat
    e o nome da classe Java interna: ~1.978 tokens contra ~17 da mensagem, 116x,
    e é a resposta errada. Descartar isso é a razão de esta classe existir em
    vez de repassar o objeto do servidor.
    """

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class RespostaInvalida(ErroJupiter):
    """Corpo que não é um envelope DWR íntegro.

    Acontece de verdade: qualquer rota desconhecida no host cai em 302 para a
    tela de login, e o corpo que chega é HTML. Sem esta classe, isso viraria
    parse parcial — um objeto meio preenchido com cara de resposta.
    """


class ConsultaNegada(ErroJupiter):
    """Método ou consulta fora da allowlist (Invariante 2)."""


class JupiterIndisponivel(ErroJupiter):
    """Timeout, conexão recusada, 5xx. O serviço não respondeu."""
