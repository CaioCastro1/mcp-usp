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
RE_HTTP = re.compile(r"https?://", re.IGNORECASE)

# O texto exato do link da página do `launch.php` com `confirmed=1`. Está aqui e
# não só no `token.sh` porque é ele que faz a mensagem de erro ser acionável: sem
# citar o link, "copie o endereço do link" não diz QUAL link, e a página tem três
# elementos clicáveis. Se o Moodle mudar essa string, o pior que acontece é a
# mensagem citar um texto que não existe mais — o diagnóstico continua certo.
LINK = "Clique aqui se a aplicação não abrir automaticamente"


def erro(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def e_url_de_ida(bruto: str) -> bool:
    """A URL da PÁGINA do `launch.php` (a de ida), não a do redirect (a de volta).

    Distingue pela ausência do campo `token=`: a de volta é
    `moodlemobile://token=<base64>` e a de ida é a URL http(s) que a pessoa
    acabou de abrir no navegador. Vale para `launch.php` por nome — que é o caso
    medido — e para qualquer http(s) sem `token=`, que é a mesma confusão com
    outra página no meio.
    """
    if "token=" in bruto:
        return False
    return "launch.php" in bruto or bool(RE_HTTP.match(bruto))


def decodificar(entrada: str) -> tuple[str, str, int]:
    """(siteid, wstoken, quantas_partes). Levanta SystemExit com mensagem."""
    bruto = entrada.strip().strip("\"'")
    if not bruto:
        erro(
            "Nada foi colado. Copie a linha `token=…` do DevTools → Network e "
            "cole de novo — ver §8 do SPEC1.md."
        )

    # A URL de IDA é o erro nº 1 do fluxo, e é MEDIDO: numa passagem real de um
    # segundo usuário em 12/09/2026, o que foi para o clipboard na primeira
    # tentativa foram os 137 bytes da URL do próprio `launch.php`. Sem esta
    # checagem a recusa acontece do mesmo jeito — mas lá embaixo, falando de
    # base64, e base64 não é o que a pessoa fez de errado. Reconhecer a entrada
    # antes de tentar decodificá-la é o que permite dizer a cura em vez de
    # adivinhar a causa ("o mais comum é…"), e a cura aqui é uma frase: o link
    # certo é aquele, e é botão direito.
    if e_url_de_ida(bruto):
        erro(
            f"O que você colou ({len(bruto)} caracteres) é a URL de IDA — a da "
            "página que você abriu no navegador — e não a de VOLTA, que é a "
            "única que carrega o token. As duas são URLs, e é por isso que se "
            "confundem.\n"
            f'A de volta só existe no ENDEREÇO do link "{LINK}": clique nele '
            'com o BOTÃO DIREITO e escolha "copiar endereço do link". Não '
            "clique com o esquerdo — isso tenta abrir o app e não copia nada.\n"
            "O que você quer no clipboard começa com `moodlemobile://token=`."
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
        # A URL do `launch.php` costumava cair AQUI, e esta mensagem a adivinhava
        # ("o mais comum é…"). Desde 14/09 ela é reconhecida lá em cima, por
        # nome, com a cura junto. O que sobra neste ramo é cópia truncada ou
        # colada pela metade — diga isso, e não a causa que já tem dono.
        erro(
            f"O valor colado ({len(bruto)} caracteres) não decodifica como "
            "base64 — o mais provável é ter sido copiado pela metade. Copie o "
            "endereço do link inteiro; ele começa com `moodlemobile://token=`."
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
