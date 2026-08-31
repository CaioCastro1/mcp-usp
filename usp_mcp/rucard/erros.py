"""ESQUELETO-FASE2 — erros legíveis do RUCard (Invariante 6)."""
from __future__ import annotations


class ErroRucard(Exception):
    """Base. Toda mensagem daqui diz o que houve em português."""


class ConsultaNegada(ErroRucard):
    """Rota ou RU fora da allowlist (Invariante 2)."""


class HashAusente(ErroRucard):
    """`RUCARD_HASH` não configurada — falha antes de sair requisição."""


class RespostaInvalida(ErroRucard):
    """Corpo que não é o JSON esperado (o HTML do Tomcat cai aqui)."""


class RucardIndisponivel(ErroRucard):
    """Timeout, conexão recusada. O serviço não respondeu."""
