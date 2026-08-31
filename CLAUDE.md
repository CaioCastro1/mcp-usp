# CLAUDE.md — usp-mcp

> **Leia isto primeiro.** Este é o cérebro compartilhado de todas as sessões de IA.
> É curto de propósito. Para detalhe profundo, siga os ponteiros em "Referências".
> Toda comunicação com o Caio é em português.
>
> **`SPEC1.md` é a autoridade do projeto.** Este arquivo é o atalho operacional;
> quando os dois divergirem, o `SPEC1.md` está certo e este aqui está desatualizado.

## 1. O produto (30 segundos)

Ferramentas MCP para responder perguntas reais sobre a vida acadêmica na USP:
cardápio dos bandejões (RUCard), prazos e material do e-Disciplinas (Moodle),
catálogo de disciplinas do JupiterWeb. Projeto não-oficial, sem vínculo com a
universidade, sobre APIs não documentadas descobertas por observação.

**Este arquivo não guarda estado, de propósito.** Nada aqui sobre que fase está
aberta, o que já foi construído ou quantos testes passam. Estado escrito em dois
lugares diverge, e este é o arquivo que toda sessão lê primeiro — a divergência
aqui é a mais cara de todas, porque contamina a sessão inteira antes da primeira
pergunta. Já aconteceu: por dois dias este parágrafo afirmou que não havia
servidor MCP nenhum enquanto dois rodavam (§9, 31/08).

**Onde ver o estado:** a última entrada do `§9 do SPEC1.md` diz o que foi
decidido e com que dado; o `README.md` resume em um parágrafo; o
`docs/decisions/BACKLOG-correcoes.md` lista a dívida aberta; e
`./scripts/gate.sh` responde em segundos o que de fato está verde. Nenhum dos
quatro é este arquivo.

## 2. Onde as coisas moram

| Caminho | O que é |
|---|---|
| `SPEC1.md` | Autoridade: fatos verificados, invariantes, questões abertas, registro de decisões (§9) |
| `usp_mcp/` | Código dos servidores MCP, um pacote por sistema |
| `tests/` | Suíte em três camadas: `politica` e `contrato` offline, `live` atrás de env var |
| `notas/` | Análise por sistema, com custo medido em bytes e tokens |
| `usp_mcp/<sistema>/` | Código: `politica`, `cliente`, ferramenta e `server` por sistema |
| `fixtures/rucard/`, `fixtures/jupiter/` | Respostas cruas versionadas (dado público) |
| `fixtures/moodle/raw/` | Cru do Moodle — **fora do git**, tem dado pessoal não higienizado |
| `scripts/` | Chamadores de descoberta (`ws.sh`, `capture.sh`, `userid.sh`, `reduzir.py`) e o gate (`gate.sh`) |
| `.env` / `.env.example` | Credenciais por env var; `.env` no gitignore |
| `docs/` | Este scaffold: domínios, convenções, handoffs, backlog |

## 3. Comandos

```bash
# Chamada única ao web service do Moodle (uma função por invocação, escolhida à mão)
./scripts/ws.sh <funcao> [param=valor ...]

# Capturar para fixture imprimindo SÓ a medida (bytes/tokens/forma) — nunca o payload
./scripts/capture.sh <nome> <funcao> [param=valor ...]

# Derivar o userid do token (cacheado em .cache/userid); --refresh força nova chamada
./scripts/userid.sh [--refresh]

# Medir quanto de cada resposta é resposta e quanto é transporte
python3 scripts/reduzir.py

# Cardápio de um RU (dado público, sem credencial pessoal)
curl -s -X POST https://uspdigital.usp.br/rucard/servicos/menu/6 -d "hash=$RUCARD_HASH"

# O venv é POR DIRETÓRIO e não vem no git: todo worktree novo precisa do seu,
# senão o .mcp.json falha com ENOENT em `.venv/bin/python`.
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt

# Gate antes de commit: segredo no git, cru ignorado, suíte offline. Não toca a rede.
./scripts/gate.sh

# Rodar TODOS os testes, inclusive a camada que fala com a USP de verdade
USP_MCP_LIVE=1 .venv/bin/python -m pytest

# O que dá para checar do servidor sem tocar a rede nem gastar chamada da conta
.venv/bin/python -m usp_mcp.<sistema>.server --auto-verificar

# Handshake stdio real com TODOS os servidores descobertos (offline; entra no gate)
.venv/bin/python -m pytest tests/handshake
```

## 4. Regras críticas (não negociáveis)

Os 8 invariantes vivem no **§2 do `SPEC1.md`** e valem mesmo que o dado sugira o
contrário. Os que mordem em toda sessão:

1. **Nunca varra a lista de funções do Moodle** (Regra de Ouro, §3.1). São 447
   funções habilitadas neste token; um sweep passa por `mod_quiz_start_attempt` e
   `mod_assign_submit_for_grading` com a credencial do dono. Uma função por
   invocação, escolhida à mão, com parâmetro real. Cada chamada fica no log da conta.
2. **Allowlist, nunca denylist** (Invariante 2). `tool_mobile_call_external_functions`
   é bloqueio permanente sem flag que libere — ela anula qualquer filtro por nome.
   O campo `type` do Moodle não é fronteira de segurança, e glob não é blindagem.
3. **Read-only por padrão** (Invariante 1). Escrita só atrás de `USP_MCP_ALLOW_WRITES=1`,
   e nunca implícita numa ferramenta de leitura. A lista de bloqueio permanente do
   §2.2 não é liberada por essa flag.
4. **Nenhum segredo no repositório** (Invariante 3). Nunca leia, imprima ou ecoe o
   valor de `MOODLE_TOKEN`. Fixture do Moodle só entra no git depois da higienização
   do §3.3 — nome, e-mail, `userid`, `fullname` de turma e notas viram valor sintético
   estável, preservando a forma.
5. **Credencial pessoal não sai da máquina do dono** (Invariante 4). Dado autenticado
   só no entrypoint local (stdio). Servidor hospedado não recebe token de ninguém,
   nem "só pra testar".
6. **Erro legível vence silêncio** (Invariante 6) e **sem limite silencioso**
   (Invariante 7). Nunca devolver lista vazia que parece "não tem nada". Se truncou,
   paginou ou amostrou, a saída diz isso. Não engolir erro cru da API.
7. **Não martelar a USP** (Invariante 5). Cache com TTL coerente com a taxa de mudança
   do dado (semana para cardápio, semestre para ementa), não com a frequência das
   perguntas.
8. **Nunca ler uma resposta crua acima de ~200 kB.** `capture.sh` imprime medida, não
   payload, exatamente para isso. `core_enrol_get_users_courses` sozinha já custa
   ~26.200 tokens.
9. **Antes de dizer que a rede da USP não dá, MEÇA** (§1.1). Do sandbox em nuvem
   do Cowork ela realmente não sai (proxy com allowlist), mas do Claude Code na
   máquina do dono ela sai — verificado em 31/08/2026. O que separa uma sessão do
   teste real é a **credencial**, não a rede: o token é pessoal e cada chamada
   fica no log da conta. Por isso a camada `live` fica atrás de `USP_MCP_LIVE=1`,
   e por isso ela é decisão do dono, não limitação de infraestrutura.
10. **Ferramenta não nasce por conveniência.** O critério para uma existir é o §5
    do `SPEC1.md`, e questão aberta do §4 fecha com dado registrado no §9 — não com
    opinião nem com o que a API oferece. O Anexo A (§7) é a lista de ferramentas
    derivada da API: está lá para ser confrontada, não seguida.
11. **Verde na suíte não é verde no que ela não alcança.** Já custou três bugs num
    dia só, um deles um entrypoint que nunca tinha funcionado com a suíte inteira
    verde. Antes de confiar num parâmetro, asserte sobre o parâmetro **enviado**,
    não sobre a saída — o dublê devolve o que o teste mandou.

## 5. Fluxo padrão de uma mudança

Branch curta saindo da `main` → PR → merge. `main` é a referência; nada de
force-push.

Mudança de **conhecimento** (fato novo sobre uma API, questão aberta fechada) vale
tanto quanto mudança de código: entra no `SPEC1.md` — fato no §1, decisão datada no
§9 com o dado que a fechou e o que foi descartado. Análise longa e medição vão para
`notas/`, e `notas/` não edita o `SPEC1.md` por conta própria.

### Definição de Pronto

1. O dado que sustenta a mudança está registrado (§9 do `SPEC1.md` para decisão,
   `notas/` para medição) — não só na janela da conversa.
2. Nenhum segredo nem dado pessoal não higienizado entrou no git.
3. Achado colateral foi para `docs/decisions/BACKLOG-correcoes.md` e a tarefa atual
   seguiu — sem desvio.

## 6. Referências (detalhe profundo)

| Assunto | Onde |
|---|---|
| Autoridade do projeto: fatos, invariantes, decisões | `SPEC1.md` |
| Domínios do sistema (RUCard, Moodle, Jupiter) | `docs/domains/README.md` |
| Convenções deste repo | `docs/agents/CONVENTIONS.md` |
| Achados colaterais em aberto | `docs/decisions/BACKLOG-correcoes.md` |
| Handoff de sessão exploratória | `docs/handoffs/_TEMPLATE.md` |

---

*Mantenha este arquivo curto e **sem estado**. Se algo aqui ficar grande, mova o
detalhe para `SPEC1.md`/`docs/` e deixe só o ponteiro. Se for a resposta de "em
que pé estamos", não escreva aqui: aqui ela envelhece calada e a próxima sessão
começa com o mapa errado.*
