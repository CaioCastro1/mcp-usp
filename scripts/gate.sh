#!/usr/bin/env bash
# Gate antes de commit — o <TODO> do §4 do CONVENTIONS.md, fechado em 31/08/2026.
#
# Uso:  ./scripts/gate.sh
#
# Um pré-requisito e quatro checagens, nesta ordem, porque a mais barata que
# pode reprovar vem antes:
#
#   pré. Isto é um clone git. Sem numeração porque não é uma propriedade do
#      código, e sim do chão em que ele está: as checagens 1 e 2 PERGUNTAM ao
#      git (`git ls-files`, `git check-ignore`), e fora de um repositório as
#      duas mentem. Medido: quem baixa o ZIP do GitHub em vez de clonar recebe
#      um traceback de `CalledProcessError` na 1 e, na 2, "o cru com dado
#      pessoal deixou de ser ignorado", que é falso, e é o pior diagnóstico
#      possível porque manda a pessoa procurar um vazamento que não existe.
#      Aborta, como a 0, em vez de somar ao placar.
#   0. O .env existe e tem RUCARD_HASH com valor. Custa um `test -f` e um grep,
#      e é a única falha do gate com cura de uma linha — por isso ela é dita com
#      o COMANDO, e não com o nome da variável que faltou. Vem antes da 1 porque
#      sem .env nenhuma das outras tem o que fazer: a 1 reprovava com "sem .env
#      em lugar nenhum" (verdade, e não é cura) e a 3 reprovava depois de 364
#      testes falando de RUCARD_HASH, que é consequência e não causa. Num clone
#      limpo, seguindo o README de cima para baixo, era esse o primeiro
#      resultado que alguém novo via. Aborta o gate em vez de somar ao placar:
#      as outras três só repetiriam o mesmo diagnóstico, mais caro e pior dito.
#      NÃO exige MOODLE_TOKEN — este gate roda offline, e credencial pessoal não
#      é pré-requisito para commitar (Invariante 4).
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

# Código de saída de "as checagens que rodaram passaram, mas a suíte não rodou".
# Não é 0 e não é 1 de propósito: 0 seria mentira (§6 do CONVENTIONS.md: uma
# verificação que não pode falhar não verifica nada) e 1 diria "reprovou", que
# também não é verdade. Um número próprio deixa quem chama distinguir os três.
SAIDA_SEM_SUITE=3

echo "gate: $(pwd)"

# ------------------------------------------------------- pré. isto é um clone
passo "pre. isto e um clone git"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then ok; else
  echo "FALHOU"
  cat <<'FIM' | sed 's/^/       /'
isto não é um repositório git. Provavelmente é o ZIP do GitHub, descompactado.
As checagens 1 e 2 perguntam ao git quais arquivos estão rastreados e quais
estão ignorados; sem repositório elas não têm a quem perguntar, e o que sai é
diagnóstico falso (traceback na 1, "o cru deixou de ser ignorado" na 2).

Cura: clone em vez de baixar o ZIP. O comando exato está no README, na seção
"Rodando a partir do código". O ZIP serve para ler o código, não para trabalhar
nele: sem `.git` não há histórico, não há branch e não há commit para este gate
proteger.
FIM
  echo
  echo "gate: REPROVOU. Nao commite."
  exit 1
fi

# ------------------------------------------------------------------- 0. o env
# `CHAVE=` seguido de pelo menos um caractere que não seja espaço nem aspa: um
# RUCARD_HASH declarado e vazio é o mesmo que ausente para quem vai usá-lo, e
# reprovar sem ter verificado nada é justamente o que esta checagem existe para
# não deixar acontecer. Tolera `export ` porque o .env é feito para ser sourceado.
PADRAO_HASH="^[[:space:]]*(export[[:space:]]+)?RUCARD_HASH[[:space:]]*=[[:space:]]*[^[:space:]\"']"

passo "0. .env existe e tem RUCARD_HASH"
# Pergunta ao usp_mcp.env onde o .env esta, como as checagens 1 e 3 ja fazem. `-f .env`
# olhava so o diretorio atual, e o .env e gitignorado: `git worktree add` nao o copia,
# entao o gate REPROVAVA em todo worktree por um .env que existe no checkout. E o mesmo
# defeito que a primeira versao deste gate teve na checagem de segredos (§4 do
# CONVENTIONS.md) e que o token.sh teve em 11/09 — terceira vez, mesmo molde.
ENV_GATE=$(PYTHONPATH="$(pwd)" "$PY" -c \
  'from usp_mcp.env import achar_env; a = achar_env(); print(a or "")' 2>/dev/null || true)
if [ -n "$ENV_GATE" ] && grep -Eq "$PADRAO_HASH" "$ENV_GATE"; then ok; else
  erro
  # A saída é o produto desta checagem: quem chega aqui é quem acabou de clonar.
  cat <<'FIM' | sed 's/^/       /'
falta o .env, ou o RUCARD_HASH nele está vazio. Procurei na raiz e, se ela for
um worktree, no checkout que tem o .git — é onde o usp_mcp.env procura. Cura, na
raiz do CHECKOUT (não a do worktree, que não deve ter .env próprio):

    cp .env.example .env

A hash do RUCard já vem preenchida no exemplo — é a chave embutida no app
oficial, pública e compartilhada, não credencial de ninguém. O MOODLE_TOKEN
pode continuar vazio: este gate roda offline (Invariante 4).
FIM
  echo
  echo "gate: REPROVOU. Nao commite."
  exit 1
fi

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
# QUEBRA DE RECURSAO. `tests/test_gate.py` roda este script dentro de um clone do
# repo; a checagem 3 rodaria a suite DO CLONE, que contem test_gate.py, que clona
# de novo. Cada nivel custa mais que o timeout do nivel acima, e o teste estoura.
# Ficou latente ate o merge de 11/09, quando o clone passou a ter test_gate.py.
#
# O pulo e BARULHENTO de proposito (Invariante 7: sem limite silencioso). Quem
# pula a suite nao pode achar que passou por ela: a linha diz PULADA, o rodape diz
# que a suite nao rodou, e o codigo de saida NAO vira 0 por causa disto: sai
# $SAIDA_SEM_SUITE. Por dois dias o comentario dizia isso e o codigo saia 0: quem
# lesse `./scripts/gate.sh && git push` via verde sem a suite ter rodado, e o
# `tests/test_gate.py` (D6) existe para essa divergencia nao voltar calada.
if [ "${USP_MCP_GATE_SEM_SUITE:-0}" = "1" ]; then
  passo "3. suite offline"
  echo "PULADA"
  echo "       USP_MCP_GATE_SEM_SUITE=1 — a suite NAO foi executada."
  echo "       Isto existe para tests/test_gate.py nao recorrer sobre si mesmo."
  echo "       Numa maquina de gente, NAO use: o gate sem a checagem 3 nao"
  echo "       verifica o codigo, so o .env e o cru ignorado."
  echo
  if [ "$falhou" -eq 0 ]; then
    echo "gate: checagens 0-2 passaram. A SUITE NAO RODOU — isto nao e um gate verde."
    echo "      Saida $SAIDA_SEM_SUITE, e nao 0: sem a checagem 3 nao ha o que aprovar."
    exit "$SAIDA_SEM_SUITE"
  fi
  echo "gate: REPROVOU. Nao commite."
  exit 1
fi

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
