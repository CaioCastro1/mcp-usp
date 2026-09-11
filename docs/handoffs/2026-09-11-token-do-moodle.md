# HANDOFF — o token do Moodle virou script — 2026-09-11

> Para o que NÃO cabe no §9 nem no git: o que não tem teste, o que ficou por medir,
> e onde a próxima sessão pisa em falso. As decisões fechadas com dado estão no §9 do
> `SPEC1.md` — **quatro entradas** (10/09 duas, 11/09 duas), e elas são a fonte. O
> desenho está em `docs/superpowers/specs/2026-09-10-script-token-moodle-design.md`.

## Objetivo da sessão

O dono pediu "um readme ou, melhor, um script" para a pessoa que está fazendo o setup
obter o `MOODLE_TOKEN`. O fluxo existia só em prosa, no §8 do `SPEC1.md`, dentro de um
arquivo de 117 kB.

## Estado

CONCLUÍDO e **verificado contra o e-Disciplinas de verdade**. PR #22 mergeado
(`969f3b0`). `./scripts/gate.sh`: **419 passed, 5 skipped**.

O token do dono foi obtido pelo script, autenticou e está no `.env`; `.cache/userid`
preenchido. Nenhum valor de token apareceu em tela em momento nenhum da sessão.

## O que foi feito

`./scripts/token.sh` (manual por padrão), `scripts/_capturar_redirect.sh` (o `--auto`),
`scripts/_decodificar_token.py` (a regra do formato, num lugar só, usada também pelo
`fix-token.sh`), 18 testes offline em `tests/moodle/test_token_decode.py`.

O que destravou tudo foi **ler a fonte do Moodle** em vez de tentar e errar: o
`admin/tool/mobile/launch.php` da 5.0 STABLE respondeu, em seis linhas, o que era
possível e o que não era. Está no §9 de 10/09 com o número de cada linha.

## O que a rodada real ensinou, e o dublê não

Três defeitos que só apareceram rodando na máquina do dono, todos corrigidos:

1. **A guarda de esquema contava claims sem olhar o identificador do bundle** — um
   registro obsoleto do *nosso próprio* handler fazia o script recusar a captura.
2. **`open` em primeiro plano não retorna com diálogo modal aberto no navegador.** Um
   "cannot open the page" esquecido de uma tentativa anterior pendurou o script por 6
   minutos, sem nunca chegar no `read` cujo timeout deveria governar a espera.
3. **A checagem 0 do gate reprovava em todo worktree** (chegou na `main` no mesmo dia,
   achada no merge). Ver "Cuidados".
4. **A suíte do gate recorria sobre si mesma.** `tests/test_gate.py::D5` roda o
   `gate.sh` dentro de um clone, e a checagem 3 rodava a suíte **do clone** — que contém
   `test_gate.py`, que clona de novo. Ficou latente até o merge de 11/09 pôr o arquivo no
   HEAD que o clone copia; aí D5 passou a estourar os 300 s do próprio timeout. A suíte
   caiu de **326 s com um vermelho** para **40,8 s verde**.

## O que falta

**Uma coisa só, e ela precisa dos olhos de quem roda:** a captura automática (`--auto`)
nunca entregou contra a USP. Três tentativas, três falhas antes de o navegador seguir o
redirect — as duas primeiras eram os bugs acima, a terceira não tem causa identificada
porque mora na tela do dono. Com ela morre junto a questão do `forcedurlscheme`, que
**não é observável de fora**: `tool_mobile_get_public_config` custou uma chamada e não
expõe a chave (36 chaves, nenhuma com `forced`).

Se alguém rodar `--auto` e funcionar, a decisão do §9 de 11/09 se inverte com uma linha,
e a fórmula do passaporte fecha na mesma rodada, de graça.

## Arquivos tocados

`scripts/{token,_capturar_redirect,fix-token,gate}.sh`, `scripts/_decodificar_token.py`,
`tests/moodle/test_token_decode.py`, `SPEC1.md` (§8 e quatro entradas no §9),
`README.md`, `CLAUDE.md`, `docs/agents/CONVENTIONS.md`,
`docs/decisions/BACKLOG-correcoes.md`, o desenho em `docs/superpowers/specs/`.

## Como retomar

Nada em aberto no git: `main` está com tudo, zero PR aberto. Para retomar o `--auto`,
o comando é um só, com o navegador logado na Senha Única — e o que interessa é **olhar
o navegador nos 120 s seguintes** e anotar o que aparece (página da Senha Única?
diálogo? aba em branco?). Isso separa as três causas que sobraram.

```bash
./scripts/token.sh --auto --sobrescrever
```

## Cuidados

**1. A dívida mais cara desta sessão não é o `--auto`: é o `.env` procurado no
diretório errado.** Três lugares diferentes olharam só `./.env` e quebraram em worktree
— a checagem de segredos do gate (já registrada no §4 do `CONVENTIONS.md`), o
`token.sh`/`fix-token.sh` (corrigidos em 11/09), e a checagem 0 do gate (chegou na
`main` em 11/09 e reprovava em **todo** worktree, no mesmo arquivo em que as checagens
1 e 3 já perguntavam ao `achar_env`). **`scripts/ws.sh` ainda tem o dele.** Três
repetições dizem que a cura é estrutural: `usp_mcp.env.achar_env` como única porta, e
nenhum `[ -f .env ]` sobrevivendo em script nenhum. Está no backlog como **alta**.

**2. Verificação casa a condição, não a mensagem.** Quatro verificadores meus, nesta
sessão, casaram string demais: a limpeza do handler testava a mensagem de erro do `open`
e reportou "ainda atende" numa máquina limpa; a guarda de esquema contava sem olhar
quem; o polling casou "handler **pronto**" no lugar do "pronto" final; e uma contagem de
processos contou o próprio `grep`. Nenhum é bug de produto, e os quatro produziram
diagnóstico errado antes de alguém medir. O §6 do `CONVENTIONS.md` diz "não afrouxe uma
verificação"; falta o corolário. Backlog.

**3. Um teste pode passar sem testar nada, e o `cd` é o disfarce.** O primeiro T-tok-14
passava **sabotado**, porque o `fix-token.sh` faz `cd` para a própria raiz e ali `./.env`
e `achar_env` apontam para o mesmo arquivo. Só um layout de worktree de verdade (`.git`
diretório no principal, worktree sem `.env`) discrimina. Se for mexer nesses testes,
sabote antes de confiar.

**4. A conferência do passaporte não discrimina no caminho manual**, e isso é por
construção: nada obriga a pessoa a abrir a URL que o script imprimiu, então um payload
de outra rodada *dela mesma* — válido, o Moodle devolve o mesmo token — não confere. Ela
só carrega informação no `--auto`. Não "conserte" isso endurecendo a checagem.

**5. `pkill -f <padrão>` casa o próprio shell** quando o padrão aparece na linha de
comando dele. Custou dois comandos mortos com exit 144 aqui. Use `pgrep` e mate por PID.

**6. Não rode `token.sh` esperando que ele escreva no `.env` do worktree.** Ele escreve
no do checkout, de propósito (§9, 11/09) — é o arquivo que o projeto usa.
