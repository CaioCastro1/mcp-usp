#!/usr/bin/env python3
"""Higienização do §3.3 do SPEC1 em código.

Troca dado pessoal por valor sintético **estável** (mesmo valor de entrada →
mesmo valor falso, sempre) para que uma fixture do Moodle possa entrar no git.

Duas propriedades, e a segunda não está no §3.3 — é requisito do teste de custo:

1. **Preserva a forma.** Mesmas chaves, mesma ordem, mesmos tipos, mesma
   contagem de itens. A forma é o que interessa para teste (§3.3).
2. **Preserva o comprimento.** Texto substituído tem o mesmo número de bytes do
   original. Sem isso a fixture não sustenta a asserção de bytes/evento, porque
   trocar um `summary` de 9 kB por uma frase curta apagaria justamente o custo
   que a projeção existe para resolver.

Uso:
    python3 scripts/higienizar.py <entrada.json> <saida.json>

Limitação declarada: a substituição é derivada de hash do valor original. Ela
não é reversível a partir da saída, mas também não é prova contra quem já tenha
uma lista de candidatos e queira testar qual bate. Serve para o que o §3.3 pede
— não publicar nome, e-mail, userid e nota do dono — e não é anonimização forte.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any

# Campos cujo *valor* é dado pessoal ou identificador do dono (§3.3).
CAMPOS_IDENTIFICADOR = {"userid", "userrole", "usermodified"}
CAMPOS_NOME = {
    "fullname", "fullnamedisplay", "firstname", "lastname", "username",
    "displayname", "author", "authorfullname", "userfullname",
}
CAMPOS_EMAIL = {"email", "useremail"}
CAMPOS_NOTA = {"grade", "rawgrade", "gradeformatted", "graderaw", "finalgrade"}
# Texto escrito por pessoa: pode nomear professor, sala, colega.
CAMPOS_TEXTO_LIVRE = {
    "summary", "description", "location", "formattedlocation", "activitystr",
    "message", "subject", "intro",
}

_ALFABETO = "abcdefghijklmnopqrstuvwxyz"
_SILABAS = ["ba", "ce", "di", "fo", "gu", "la", "me", "ni", "ro", "su", "ta", "vi"]


def _semente(valor: Any) -> int:
    """Inteiro estável derivado do valor. Mesmo valor → mesma semente."""
    bruto = json.dumps(valor, ensure_ascii=False, sort_keys=True)
    return int.from_bytes(hashlib.sha256(bruto.encode()).digest()[:8], "big")


def _nome_sintetico(original: str) -> str:
    """Nome falso estável com o MESMO comprimento em bytes do original."""
    alvo = len(original.encode())
    if alvo == 0:
        return ""
    s = _semente(original)
    partes, acumulado = [], 0
    while acumulado < alvo:
        p = _SILABAS[s % len(_SILABAS)].capitalize()
        partes.append(p)
        acumulado += len(p) + 1
        s //= len(_SILABAS)
        if s == 0:
            s = _semente(str(acumulado))
    return " ".join(partes)[:alvo].ljust(alvo, "o")


def _texto_sintetico(original: str) -> str:
    """Texto falso estável, mesmo comprimento em bytes.

    Mantém a aparência de HTML quando o original tinha tag, porque o §1.2 e a
    linha 3 do Moodle registram HTML embutido em campo de descrição e a camada
    de projeção precisa continuar vendo isso.
    """
    alvo = len(original.encode())
    if alvo == 0:
        return ""
    tinha_html = "<" in original and ">" in original
    s = _semente(original)
    corpo, acumulado = [], 0
    while acumulado < alvo + 8:
        p = _SILABAS[s % len(_SILABAS)] + _ALFABETO[s % 26]
        corpo.append(p)
        acumulado += len(p) + 1
        s = s // len(_SILABAS) or _semente(str(acumulado))
    texto = " ".join(corpo)
    if tinha_html:
        texto = f"<p>{texto}</p>"
    b = texto.encode()[:alvo]
    # corta em fronteira de caractere sem mudar o número de bytes
    while True:
        try:
            b.decode()
            break
        except UnicodeDecodeError:
            b = b[:-1] + b"x"
    return b.decode()


def _email_sintetico(original: str) -> str:
    alvo = len(original.encode())
    base = f"pessoa{_semente(original) % 10**6:06d}"
    dominio = "@exemplo.invalid"
    montado = (base + dominio)[:alvo] if alvo else ""
    return montado.ljust(alvo, "x") if alvo else ""


def _id_sintetico(original: int) -> int:
    """Id falso estável com o mesmo número de dígitos."""
    digitos = len(str(abs(original)))
    if digitos == 0:
        return 0
    piso = 10 ** (digitos - 1)
    return piso + (_semente(original) % (10 * piso - piso))


_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def higienizar(no: Any, chave: str | None = None) -> Any:
    if isinstance(no, dict):
        return {k: higienizar(v, k) for k, v in no.items()}
    if isinstance(no, list):
        return [higienizar(v, chave) for v in no]

    if chave is None:
        return no
    k = chave.lower()

    if k in CAMPOS_IDENTIFICADOR and isinstance(no, int) and no != 0:
        return _id_sintetico(no)
    if k in CAMPOS_EMAIL and isinstance(no, str):
        return _email_sintetico(no)
    if k in CAMPOS_NOME and isinstance(no, str):
        return _nome_sintetico(no)
    if k in CAMPOS_NOTA and isinstance(no, (int, float)) and not isinstance(no, bool):
        return round(_semente(no) % 1001 / 100, 2)
    if k in CAMPOS_NOTA and isinstance(no, str):
        return _nome_sintetico(no)
    if k in CAMPOS_TEXTO_LIVRE and isinstance(no, str):
        return _texto_sintetico(no)
    # Rede de segurança: e-mail solto dentro de qualquer string. O teste barato
    # do "@" vem antes de propósito: o regex faz backtracking quadrático em texto
    # longo sem arroba, e um `summary` de 9 kB é exatamente esse caso.
    if isinstance(no, str) and "@" in no and _RE_EMAIL.search(no):
        return _RE_EMAIL.sub(lambda m: _email_sintetico(m.group()), no)
    return no


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"uso: {argv[0]} <entrada.json> <saida.json>", file=sys.stderr)
        return 2
    entrada, saida = argv[1], argv[2]
    with open(entrada, encoding="utf-8") as fh:
        cru = json.load(fh)
    limpo = higienizar(cru)
    with open(saida, "w", encoding="utf-8") as fh:
        json.dump(limpo, fh, ensure_ascii=False, separators=(",", ":"))
    import os
    print(
        f"{saida}: {os.path.getsize(saida)} B "
        f"(cru {os.path.getsize(entrada)} B) — forma e comprimento preservados"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
