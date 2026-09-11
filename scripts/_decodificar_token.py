#!/usr/bin/env python3
"""Decodifica o payload do fluxo de `launch.php` do Moodle (§1.3 do SPEC1.md).

Lê no stdin a URL `moodlemobile://token=<base64>` — ou só o base64 — e imprime
no stdout, uma por linha:

    siteid=<32 hex>
    wstoken=<32 hex>
    partes=<quantas partes o payload trazia>

O `privatetoken`, terceira parte do payload, é decodificado por força do formato
e **morre aqui dentro**: ele habilita `tool_mobile_get_autologin_key`, que está
no bloqueio permanente do §2.2 e não é liberado por `USP_MCP_ALLOW_WRITES=1`.
Nada além dos três campos acima sai deste script.

Forma errada reprova com mensagem legível em português no stderr e código 1
(Invariante 6) — nunca com stack trace, e nunca ecoando a entrada, que É a
credencial. O diagnóstico fala de forma (quantos caracteres, quantas partes),
nunca de conteúdo.

Usado por `scripts/token.sh` (setup guiado) e `scripts/fix-token.sh` (conserto
de `.env` preenchido à mão). A regra do formato mora aqui, em um lugar só.
"""
from __future__ import annotations

import base64
import binascii
import re
import sys

RE_32HEX = re.compile(r"[a-f0-9]{32}")


def erro(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def decodificar(entrada: str) -> tuple[str, str, int]:
    """(siteid, wstoken, quantas_partes). Levanta SystemExit com mensagem."""
    bruto = entrada.strip().strip("\"'")
    if not bruto:
        erro(
            "Nada foi colado. Copie a linha `token=…` do DevTools → Network e "
            "cole de novo — ver §8 do SPEC1.md."
        )

    b = bruto.split("token=", 1)[1] if "token=" in bruto else bruto
    b = re.sub(r"[^A-Za-z0-9+/=_-]", "", b.rstrip("/"))
    b = b.replace("-", "+").replace("_", "/")
    if not b:
        erro(
            f"O valor colado ({len(bruto)} caracteres) não tem base64 nenhum "
            "depois do `token=`. Refaça o §8 do SPEC1.md."
        )

    try:
        cru = base64.b64decode(b + "=" * (-len(b) % 4), validate=False)
        texto = cru.decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        erro(
            f"O valor colado ({len(bruto)} caracteres) não decodifica como "
            "base64. O mais comum é ter copiado a URL do `launch.php` em vez da "
            "do redirect — a que interessa começa com `moodlemobile://token=`."
        )

    partes = texto.split(":::")
    if len(partes) < 2:
        erro(
            f"O payload decodificou em {len(partes)} parte(s); o formato do "
            "Moodle é `siteid:::token:::privatetoken`. Refaça o §8 do SPEC1.md."
        )

    siteid, wstoken = partes[0], partes[1]
    if not RE_32HEX.fullmatch(wstoken):
        erro(
            f"A segunda parte do payload tem {len(wstoken)} caracteres e não é "
            "hexadecimal de 32 — um token real é. Se você usou "
            "`urlscheme=http`, é isso: o Chrome põe o base64 na posição de host "
            "e minusculiza, corrompendo o valor. Use `urlscheme=moodlemobile` "
            "(§1.3 do SPEC1.md)."
        )

    # partes[2] existe e não é usado. É o privatetoken; ver docstring.
    return siteid, wstoken, len(partes)


def main() -> None:
    siteid, wstoken, quantas = decodificar(sys.stdin.read())
    print(f"siteid={siteid}")
    print(f"wstoken={wstoken}")
    print(f"partes={quantas}")


if __name__ == "__main__":
    main()
