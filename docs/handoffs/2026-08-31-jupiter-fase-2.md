# HANDOFF — Fase 2 do Jupiter (fatia vertical `disciplina`) — 2026-08-31 — sessão de implementação

> Este handoff existe para o que NÃO cabe no §9 nem no git: o que ficou fora de
> escopo, o que não tem teste, e onde a próxima sessão pisa em falso. A decisão
> fechada com dado está no §9 do `SPEC1.md`, entrada de 31/08/2026.

## Objetivo da sessão
Escrever a suíte do Jupiter como especificação executável e, depois de aprovada,
implementar a Fase 2 contra ela — sem alterar teste para passar.

## Estado
CONCLUÍDO **contra fixture**, NÃO contra a USP. **173 verdes, 4 pulados, 0
falhas** nas duas trilhas juntas. Os 4 pulados são os canários `live` (2 do
Moodle, 2 do Jupiter); os do Jupiter **nunca rodaram**, porque esta sessão não
alcança `uspdigital.usp.br` (§1.1). Enquanto não rodarem, o que existe é "verde
contra fixture".

## O que foi feito
1. Suíte primeiro, 44 funções de teste, todas vermelhas por `NotImplementedError`.
2. Merge da Fase 2 do Moodle, que entrou na `main` em paralelo — 5 conflitos de
   andaime, todos resolvidos preservando as duas trilhas.
3. Implementação: `erros`, `politica`, `dwr`, `cliente`, `ferramentas`, `server`.
4. `.mcp.json` registra `usp-jupiter`. Auto-verificação dos dois servidores passa.

## O que falta
- **Rodar os canários ao vivo.** É o único passo que separa "verde" de
  "verificado". Duas requisições reais, no máximo.
- **Grade curricular** e **navegação unidade→curso**: fatias seguintes, já
  desenhadas no spec e deliberadamente fora desta.
- **Horário, sala e vagas**: continua não prometido. Uma amostra só de
  `obterTurma`, scraping de 48 tabelas sem âncora, e a manutenção semestral que o
  §4 exige nunca foi assumida.
- **Invariante 8.** Não há `robots.txt` nem termo de uso. Antes de divulgar, o
  caminho é perguntar à STI — não deduzir do nome de uma classe Java.

## Arquivos tocados
`usp_mcp/jupiter/*.py`, `tests/jupiter/*.py`, `.mcp.json`, `requirements.txt`,
`SPEC1.md` (§9), `CLAUDE.md` e `docs/agents/CONVENTIONS.md` (os três `<TODO>` de
gate), `docs/superpowers/{specs,plans}/2026-08-31-*jupiter*`.

## Como retomar

```bash
# se o venv não existir NESTE diretório (cada worktree precisa do seu):
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt

.venv/bin/python -m pytest                              # gate: 173 passed, 4 skipped
.venv/bin/python -m usp_mcp.jupiter.server --auto-verificar
USP_MCP_LIVE=1 .venv/bin/python -m pytest tests/jupiter -m live   # só no terminal do dono
```

## Cuidados

**Não "simplifique" o parser de `dwr.py` para um regex.** A tentação é óbvia — o
corpo é quase JSON, faltam só aspas nas chaves. Mas os valores são ementa e
bibliografia escritas por docentes; um texto que contenha `, algo:` faz a
substituição corromper o valor **sem erro nenhum**. O parser existe por isso, e o
teste que o protege é de comportamento, não de forma.

**Não troque a carga horária calculada pelo campo.** `cgahoreto` existe, vem `"0"`
nas duas amostras, e parece o campo certo. Lê-lo devolve zero hora com cara de
resposta certa. A conta aparece no texto de saída (`3×15 + 0×30`) justamente para
que a "correção" pareça errada a quem for fazê-la.

**Não deixe a ferramenta responder pré-requisito sem curso.** A resposta é
condicional ao curso. Dizer "sem pré-requisito" quando ninguém consultou é o
Invariante 7 quebrado, e é o tipo de erro que ninguém percebe até matricular.

**Não suba o import do SDK do MCP para o topo de `server.py`.** A suíte roda sem
o SDK; um import de topo quebra a coleta inteira por uma dependência que as
funções puras nem usam. Há teste (T43) que falha se alguém fizer isso.

**Não acrescente consulta à allowlist "só para testar".** A superfície está
travada em duas, e o teste compara o conjunto inteiro. Crescer é decisão de §9.

**Cuidado ao mexer em `cliente.py`:** há teste de política que varre o fonte
procurando nome de variável de ambiente com segredo e cabeçalho de identificação.
Ele não é paranoia — é o que impede o servidor público do §6 de virar portador de
credencial num refactor futuro.
