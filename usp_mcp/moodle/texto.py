"""Casar o que a pessoa digita com o que o Moodle escreveu.

Um lugar só, porque já houve dois. `disciplinas._normalizar` nasceu para resolver
sigla e ganhou o `NFD` em 31/08, quando o dono digitou "eletronica" e o filtro
descartou a letra acentuada inteira (T83). O filtro `busca` de `material` nasceu
no mesmo dia com `filtro in nome.lower()` e **não** ganhou a correção: medido em
01/09, "formulario" não achava "Formulário Provas Substitutivas.pdf". Duas
semânticas de casamento no mesmo servidor, e a terceira estava prestes a nascer
em `arquivo.py`.
"""
from __future__ import annotations

import re
import unicodedata


def normalizar(s: str) -> str:
    """"psi 3323" → "PSI3323"; "Eletrônica" → "ELETRONICA".

    O `NFD` é o que faz isso funcionar e não é decoração: ele separa "ô" em "o"
    mais a marca combinante, e aí o filtro descarta só a marca. Sem ele o filtro
    descartava o "ô" inteiro, "Eletrônica" virava "ELETRNICA", e deixava de casar
    com "eletronica". T83 fica vermelho se alguém o remover por parecer supérfluo.
    """
    decomposto = unicodedata.normalize("NFD", s or "")
    return re.sub(r"[^A-Z0-9]", "", decomposto.upper())


def casa(termo: str, alvo: str) -> bool:
    """Substring, sem acento, sem caixa, sem pontuação. Termo vazio casa com tudo.

    Termo vazio casando com tudo é o que faz `material` sem `busca` continuar
    listando o espaço inteiro — não é permissividade acidental.
    """
    return normalizar(termo) in normalizar(alvo)
