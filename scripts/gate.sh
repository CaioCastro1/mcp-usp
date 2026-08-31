#!/usr/bin/env bash
# Gate antes de commit — o <TODO> do §4 do CONVENTIONS.md, fechado em 31/08/2026.
#
# Uso:  ./scripts/gate.sh
#
# Três checagens, nesta ordem, porque a mais barata que pode reprovar vem antes:
#
#   1. Nenhum segredo do .env em arquivo rastreado (Invariante 3). Roda primeiro
#      porque é a única falha aqui que, se passar, é irreversível — commit
#      empurrado com segredo não se desfaz apagando o commit.
#   2. O cru gitignorado continua fora do git (§3.3).
#   3. Os testes OFFLINE. A camada live NÃO entra: ela precisa de rede e do
#      token pessoal, e cada chamada fica no log da conta (§1.1). Um gate que
#      depende da USP estar de pé é um gate que reprova commit por motivo
#      errado. Rode a live à mão quando quiser o canário.
#
# Nunca imprime valor de segredo — só o NOME da variável que vazou.

set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

falhou=0
passo() { printf '  %-46s' "$1"; }
ok()    { echo "OK"; }
erro()  { echo "FALHOU"; falhou=1; }

echo "gate: $(pwd)"

# ---------------------------------------------------------------- 1. segredos
passo "1. nenhum segredo do .env rastreado"
# PYTHONPATH: rodar `scripts/x.py` poe `scripts/` no sys.path, nao a raiz —
# e o import de usp_mcp falha. O gate ja fez cd para a raiz la em cima.
if vazados=$(PYTHONPATH="$(pwd)" "$PY" scripts/_gate_segredos.py); then ok; else
  erro; echo "$vazados" | sed 's/^/       /'; falhou=1
fi

# ------------------------------------------------------------------- 2. o cru
passo "2. fixtures/moodle/raw/ segue ignorada"
if git check-ignore -q fixtures/moodle/raw/action_events.json; then ok; else
  erro; echo "       o cru com dado pessoal deixou de ser ignorado (§3.3)"
fi

# --------------------------------------------------------------- 3. os testes
passo "3. suite offline"
# Sem -q extra: o pytest.ini já traz um, e o segundo engole a linha de resumo.
if saida=$(USP_MCP_LIVE= "$PY" -m pytest 2>&1); then
  ok; echo "$saida" | grep -E "passed|failed" | tail -1 | sed 's/^/       /'
else
  erro; echo "$saida" | tail -20 | sed 's/^/       /'
fi

echo
if [ "$falhou" -eq 0 ]; then
  echo "gate: PASSOU. A camada live NAO foi exercitada — rode a mao se quiser o canario:"
  echo "  USP_MCP_LIVE=1 $PY -m pytest -m live"
else
  echo "gate: REPROVOU. Nao commite."
fi
exit "$falhou"
