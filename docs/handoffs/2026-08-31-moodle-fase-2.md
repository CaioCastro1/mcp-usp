# HANDOFF — Fase 2 do Moodle (fatia vertical `o_que_vence`) — 2026-08-31 — sessão de implementação

> Este handoff existe para o que NÃO cabe no §9 nem no git: o que ficou fora de
> escopo, o que não tem teste, e onde a próxima sessão pisa em falso. As decisões
> fechadas com dado estão no §9 do `SPEC1.md` — **sete entradas** desta sessão,
> das linhas 697 a 904, e elas são a fonte, não este arquivo. (O §9 tem outras
> quatro de 31/08 que são das sessões anteriores do mesmo dia.)

## Objetivo da sessão
Implementar a Fase 2 do Moodle contra `tests/moodle/`, tratando a suíte como
especificação executável e sem alterar nenhum teste, até ficar verde. Depois, a
pedido, plugar o servidor MCP num cliente real e fechar o que aparecesse.

## Estado
CONCLUÍDO — **105 testes passando**: 103 offline (0,3 s, sem rede) + 2 na camada
`live`, que fala com o e-Disciplinas de verdade. Zero vermelho, zero pulado
quando `USP_MCP_LIVE=1`.

**A ferramenta funciona ponta a ponta.** `o_que_vence` chamada por um cliente MCP
real, pelo `.mcp.json` versionado, devolveu 30 vencimentos reais numa janela de
365 dias. O `tools/call` não é mais hipótese.

`main` sincronizada com `origin/main`, working tree limpo, gate verde.

## O que foi feito

**Sete PRs**, todos mergeados na `main`:

| PR | O que |
|---|---|
| #1 | Os 5 módulos: `politica`, `projecao`, `cliente`, `o_que_vence`, `server`. 91 vermelhos → verdes |
| #2 | `conftest` carrega o `.env` — nada no lado Python fazia isso |
| #3 | `requirements-dev.txt` e o comando de retomada que de fato funciona |
| #4 | Pluga o MCP; `usp_mcp/env.py` compartilhado; conserta o `main()` que nunca rodou |
| #5 | Fixture do `invalidtoken` real; §1.1 corrigido com medição |
| #6 | **Bug do limite silencioso de 20**; mais dois erros reais capturados |
| #7 | `scripts/gate.sh`, verificado por sabotagem das três checagens |

**Três bugs reais achados depois do verde**, e cada um diz algo sobre o que a
suíte não alcança:

1. **`main()` nunca tinha funcionado** — escrito contra a API antiga do SDK
   (`Server` + `@list_tools`); o `mcp` 2.1.1 usa `MCPServer` + `@tool`. A suíte
   estava 99/99 verde com esse caminho quebrado.
2. **`o_que_vence` perdia entregas.** O `limitnum` do calendário tem default 20 e
   a API não avisa que parou: 20 eventos sem o parâmetro, 30 com `limitnum=50`.
   A suíte não pegava porque o duplo de cliente devolve o que o teste manda — o
   corte era do lado do Moodle, e **nenhuma asserção olhava o parâmetro enviado**.
3. **A primeira versão do `gate.sh` passava sem verificar nada** — procurava o
   `.env` em `cwd/.env`, e um worktree não tem o dele. Mesmo erro do `conftest`,
   no mesmo dia, por quem acabara de consertá-lo.

## O que falta

- **As outras perguntas do §5.** Isto é **uma** ferramenta de sete candidatas
  (bandejão, notas, material de aula, aviso de professor, créditos/pré-requisito).
  Nenhuma existe. O §5 manda não decidir número e nome por conveniência.
- **Dois modos de erro sem forma verificada:** HTML de manutenção com HTTP 200 e
  timeout. **Não são capturáveis sob demanda** — exigiriam a USP em manutenção ou
  fora do ar. Os testes dos dois seguem assegurando contrato de camada, e é o
  máximo que dá para afirmar. Não trate como dívida acionável.
- **Jupiter.** A branch `claude/jupiter-mcp-validation-tests-c1e08a` (sessão irmã)
  segue fora da `main`. O §7 do documento de desenho tem os acordos combinados
  entre as duas suítes.
- **Branches de trabalho não apagadas**, locais e remotas. Limpeza cosmética.

## Arquivos tocados

Praticamente tudo. O que **não** foi tocado: `scripts/{ws,capture,userid,reduzir,fix-token}.sh`,
`notas/`, `fixtures/{rucard,jupiter}/`, `pytest.ini`, `fixtures/moodle/action_events.json`.

Novos: `usp_mcp/{env.py,moodle/*.py}`, `scripts/{gate.sh,_gate_segredos.py}`,
`requirements.txt`, `requirements-dev.txt`, `.mcp.json`,
`fixtures/moodle/erro_*.json` (3).

Alterados: `SPEC1.md` (§1.1 + seis entradas no §9), `CLAUDE.md` (item 9 e §3),
`docs/agents/CONVENTIONS.md` (§4), `docs/decisions/BACKLOG-correcoes.md`,
`tests/moodle/{conftest,test_cliente,test_o_que_vence,test_live}.py`.

**Sobre tocar `tests/`:** o contrato original proibia, e foi respeitado até a
suíte ficar verde (PR #1 não tem uma linha de `tests/`). Depois disso o dono
autorizou explicitamente, e as mudanças foram só ADITIVAS — T52 a T57 novos, mais
o carregamento do `.env`. **Nenhuma asserção existente foi afrouxada.**

## Como retomar

```bash
cd /Users/caiocastro/Padrao/GitHub/mcp-usp

# se o venv não existir NESTE diretório (cada worktree precisa do seu):
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt   # suíte
.venv/bin/python -m pip install -r requirements.txt       # SDK do MCP (entrypoint)

./scripts/gate.sh                                # antes de commitar
USP_MCP_LIVE=1 .venv/bin/python -m pytest        # todos os 105
.venv/bin/python -m usp_mcp.moodle.server --auto-verificar   # o que main() não testa
```

Para usar a ferramenta: abrir um cliente MCP neste diretório — o `.mcp.json` já
está versionado, sem segredo — e perguntar o que vence.

## Cuidados

- **Três números estão travados por teste, de propósito.** `politica.ALLOWLIST`
  tem 1 nome (T7), `server.listar_ferramentas()` devolve 1 ferramenta (T42), e
  `limitnum` é 50 (T53). Se você precisar de "só mais uma", o teste fica vermelho
  — e ele está certo. O caminho é entrada nova no §9, não editar a asserção.
- **`.env` tem UM jeito de ser achado: `usp_mcp.env.achar_env`.** Duas versões
  diferentes deste algoritmo já falharam em silêncio no mesmo dia. Não copie a
  lógica; importe a função.
- **Não mexa nos campos da projeção sem remedir.** `activityname` (não `name`) e
  `url` (não `viewurl`) saíram do orçamento de bytes; `viewurl` sozinho joga a
  medida para fora da faixa da suíte.
- **`errorcode` do Moodle nem sempre é um código.** Pode ser frase em inglês
  (`"Limit must be between 1 and 50 (inclusive)"`). Nunca trate como enum; o
  cliente compara por igualdade exata com `invalidtoken` e T57 trava isso.
- **O import do SDK do MCP fica dentro de `server.main()`.** No topo do módulo
  quebra a coleta da suíte inteira. Parece erro de estilo e não é.
- **A rede da USP É alcançável do Claude Code na máquina do dono** — o §1.1
  afirmava o contrário e foi corrigido em 31/08 com medição. O que separa uma
  sessão do teste real é a **credencial**, não a rede: o token é pessoal e cada
  chamada fica no log da conta. Peça antes de gastar.
- **Verde na suíte não é verde nos caminhos que ela não alcança.** Isso deixou de
  ser aviso teórico três vezes hoje. Antes de confiar no entrypoint, rode
  `--auto-verificar`; antes de confiar num parâmetro, asserte sobre o parâmetro
  enviado, não sobre a saída.

## Como esta sessão foi conduzida

Registrado porque afeta quem retomar, não como mérito.

**Não foi seguido o workflow das skills do superpowers** (`brainstorming`,
`test-driven-development`, `verification-before-completion`,
`requesting-code-review`). O contrato do dono na abertura já especificava o
processo — ordem dos módulos pelo grafo de dependência, um subagente `sonnet` por
módulo, suíte inteira entre ondas, um commit por módulo verde — e instrução
explícita do usuário precede skill. As skills não chegaram a ser invocadas nem
anunciadas.

O que **foi** seguido: a Definição de Pronto do `CLAUDE.md` §5 (dado registrado
no §9, nenhum segredo no git, achado colateral no backlog) e o fluxo de merge do
`CONVENTIONS.md` §5 (branch curta → PR → merge, `main` como referência, sem
force-push).

Quatro subagentes `sonnet`, um por módulo, sem dois no mesmo arquivo. Todo o
trabalho posterior ao verde foi feito na sessão principal, sem subagente.
