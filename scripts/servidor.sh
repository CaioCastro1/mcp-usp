#!/usr/bin/env bash
# Lançador de um servidor MCP deste checkout — de qualquer cwd.
#
# Uso:  ./scripts/servidor.sh <sistema>            # rucard | jupiter | moodle
#       /caminho/do/checkout/scripts/servidor.sh rucard
#
# Por que existe: o `.mcp.json` é versionado e compartilhado, então não pode
# trazer o caminho absoluto da máquina de ninguém — é o Invariante 3 aplicado a
# caminho em vez de segredo. Mas `"command": ".venv/bin/python"` transfere para o
# cliente uma premissa que nem todo cliente cumpre: a de rodar o servidor com o
# cwd na raiz do projeto. O Claude Code faz; o Claude Desktop, alvo do `.mcpb` do
# §6.1, não. Medido: `cd /tmp && .venv/bin/python -m usp_mcp.rucard.server` sai
# com rc=127 e "no such file or directory" — falha calada, o modo mais caro.
#
# Aqui o único caminho absoluto que existe é o DESTE script, e ele fica no
# arquivo de config da máquina de quem usa (ver "Cliente que não faz cd" no
# README), nunca no git. O `.mcp.json` segue relativo e segue servindo o Claude
# Code, porque o `cd` de dentro daqui resolve o resto.

set -euo pipefail

# `cd` + `pwd` em vez de só `dirname`: normaliza o caminho e faz o script falhar
# aqui, com o diretório na mensagem, se o checkout sumiu debaixo do cliente.
raiz="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd -- "$raiz"

# Descoberta, não lista escrita à mão — mesma razão do glob de
# `tests/handshake/conftest.py`: um quarto sistema passa a ser aceito no dia em
# que nascer, em vez de precisar que alguém lembre de editar este arquivo.
sistemas=()
for arquivo in usp_mcp/*/server.py; do
  [ -f "$arquivo" ] || continue
  sistemas+=("$(basename -- "$(dirname -- "$arquivo")")")
done
validos="${sistemas[*]+${sistemas[*]}}"

if [ $# -ne 1 ]; then
  echo "uso: $0 <sistema>" >&2
  echo "sistemas deste checkout: ${validos:-nenhum encontrado em usp_mcp/*/server.py}" >&2
  exit 2
fi

sistema="$1"

# Validar no shell, antes do interpretador: subir o Python para descobrir que
# `usp_mcp.bandejao` não existe custa uma subida e devolve um traceback onde
# cabia uma frase (Invariante 6).
achou=0
for valido in ${sistemas[@]+"${sistemas[@]}"}; do
  [ "$valido" = "$sistema" ] && achou=1
done
if [ "$achou" -ne 1 ]; then
  echo "sistema desconhecido: '$sistema'" >&2
  echo "os deste checkout são: ${validos:-nenhum encontrado em usp_mcp/*/server.py}" >&2
  exit 2
fi

# O venv é POR DIRETÓRIO e não vem no git (§3 do CLAUDE.md), então "acabei de
# clonar" e "worktree novo" caem os dois aqui. Dizer qual comando cura vale mais
# do que o ENOENT cru que o exec devolveria.
if [ ! -x .venv/bin/python ]; then
  echo "não há .venv/bin/python em $raiz" >&2
  echo "o venv é por diretório e não vem no git. Crie o deste checkout:" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt" >&2
  exit 1
fi

# `exec`: o servidor stdio herda os pipes do cliente MCP e vira o processo, sem
# um shell no meio segurando sinal nem bufferizando o JSON-RPC.
exec .venv/bin/python -m "usp_mcp.$sistema.server"
