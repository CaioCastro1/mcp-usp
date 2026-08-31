#!/usr/bin/env python3
"""Checagem 1 do `scripts/gate.sh`: nenhum segredo do `.env` em arquivo rastreado.

Sai com 0 se está limpo, 1 se vazou. Imprime o NOME da variável e o arquivo —
**nunca o valor** (Invariante 3). Roda antes das outras checagens porque é a
única falha do gate que é irreversível: commit empurrado com segredo não se
desfaz apagando o commit.

Script separado, e não heredoc dentro do `gate.sh`, por dois motivos: um heredoc
aninhado com o mesmo delimitador fecha cedo e produz um gate que silenciosamente
não roda, e um `.py` à parte pode ser testado isoladamente.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

from usp_mcp.env import achar_env

# Valor curto ou notoriamente público não é segredo. MOODLE_URL é a URL do
# e-Disciplinas e aparece no código de propósito.
_TAMANHO_MINIMO = 12
_NAO_SAO_SEGREDO = ("MOODLE_URL",)

# Colocações DELIBERADAS e documentadas, isentas por par (variável, arquivo) e
# não por variável. `RUCARD_HASH` é o hash embutido no app oficial do RUCard —
# compartilhado, não por usuário — e o §1.2 do SPEC1.md publica o valor de
# propósito, porque sem ele o §8 não é reproduzível.
#
# Por par, e não por variável, porque a mesma hash aparecendo em QUALQUER outro
# arquivo é surpresa e deve reprovar. Isentar a variável inteira transformaria
# este gate em teatro para ela.
_DELIBERADOS = {
    ("RUCARD_HASH", ".env.example"),
    ("RUCARD_HASH", "SPEC1.md"),
}


def main() -> int:
    # `achar_env` e NÃO `cwd/.env`: o `.env` é gitignorado, então um worktree
    # não tem o dele e o carregador sobe até o checkout principal. A primeira
    # versão deste gate procurava só no cwd — passava sem ter procurado nada, e
    # deixou passar um token plantado de propósito num arquivo rastreado. É o
    # mesmo erro que o `conftest` teve (§9, 31/08/2026), repetido por quem
    # acabara de consertá-lo.
    arquivo = achar_env(pathlib.Path.cwd())
    if arquivo is None:
        # Invariante 6 aplicado ao próprio gate: checagem que não pôde rodar
        # DIZ isso e reprova, em vez de reportar OK sem ter verificado nada.
        print("sem .env em lugar nenhum — esta checagem não verificou nada")
        return 1

    env: dict[str, str] = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.removeprefix("export ").strip()
        valor = valor.strip().strip('"').strip("'")
        if len(valor) >= _TAMANHO_MINIMO and chave not in _NAO_SAO_SEGREDO:
            env[chave] = valor

    if not env:
        print(f"{arquivo} não tem valor longo — esta checagem não verificou nada")
        return 1

    rastreados = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()

    vazados: set[str] = set()
    for nome in rastreados:
        p = pathlib.Path(nome)
        if not p.is_file():
            continue
        try:
            texto = p.read_text(errors="ignore")
        except OSError:
            continue
        for chave, valor in env.items():
            if valor in texto and (chave, nome) not in _DELIBERADOS:
                vazados.add(f"{chave} em {nome}")

    if vazados:
        print("\n".join(sorted(vazados)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
