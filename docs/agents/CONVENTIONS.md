# CONVENTIONS — padrões deste repo

> Complementa o `CLAUDE.md` (regras não-negociáveis) e o `SPEC1.md` (autoridade).
> Aqui vive o COMO. Seções que não se aplicam a este projeto foram apagadas em vez
> de deixadas como `<TODO>` morto — banco de dados e frontend não existem aqui.

## 0. Princípio guia: medir antes de desenhar

Toda resposta de API que entra no projeto ganha três números antes de qualquer
decisão sobre ela: **bytes**, **estimativa de tokens** e **quantas chamadas** foram
necessárias para responder à pergunta (§3.2 do `SPEC1.md`). Esses números decidem
mais sobre o desenho do que qualquer preferência estética — e são o que separa
"resumir no servidor" de "devolver cru".

O corolário: nunca despeje payload cru na janela. `scripts/capture.sh` existe para
que ler uma resposta de 251k tokens seja impossível por acidente.

## 1. Integrações externas

Uma API não documentada por vez, um client central por API. Regras que já
custaram medição para descobrir:

- **Moodle** (`scripts/ws.sh`): uma função por invocação, escolhida à mão. O script
  não itera sobre lista de propósito. Erro cru vai para stdout sem filtro
  (Invariante 6) — não engolir, não normalizar, não transformar em `[]`.
- **RUCard**: POST form-urlencoded (`GET` devolve 500 com HTML do Tomcat, não JSON).
  Todos os valores de `/restaurants` são string, inclusive booleanos — `hasCashier`
  vem `"false"` nos 18 RUs e é sempre errado; usar o tamanho de `cashiers`. Em
  `/menu`, `message.error` é booleano de verdade: as duas rotas não seguem a mesma
  regra. Resolver RU **por id**, nunca por `name`/`alias`.
- **Jupiter**: ver `notas/jupiter-recon.md` antes de tocar. Nenhum laço, nenhuma
  enumeração de id, nenhum catálogo baixado.

Cache com TTL colado na taxa de mudança do dado (Invariante 5), não na frequência
da pergunta.

## 2. Segredo e dado pessoal

- `.env` no gitignore, `.env.example` é forma e nunca conteúdo.
- Nenhum script imprime o valor de um token — só diagnóstico de forma
  (`fix-token.sh` é o modelo: valida 32 hex, nunca ecoa).
- Valor derivável não se configura à mão: `MOODLE_USERID` sai do próprio token via
  `core_webservice_get_site_info`, porque um userid errado devolve `[]` com HTTP 200
  e nenhum erro — o falso "não tem nada" que o Invariante 6 proíbe.
- Fixture com dado pessoal só entra no git depois da higienização do §3.3, que
  preserva a forma: mesmo id → mesmo valor falso.

## 3. Estrutura de código

**Python 3 + pytest.** O repo já rodava `python3`; `pytest` é a única dependência,
declarada em `requirements-dev.txt` e instalada num venv local (`.venv/`, no gitignore).

`usp_mcp/<sistema>/` por sistema (`jupiter/`, `moodle/`, `rucard/`), cada um com
`cliente.py` (transporte + allowlist na fronteira) e `ferramentas.py`. O que é comum aos
três mora em `usp_mcp/` (hoje `env.py` e `adaptador.py`). **O `server.py` mora dentro do
subpacote, nunca na raiz:** o §6 do `SPEC1.md` separa entrypoint local com credencial
(Moodle, stdio) de servidor público cacheável (Jupiter, RUCard), e a estrutura reflete
isso em vez de deixar a separação só na prosa. Testes em `tests/<sistema>/`.

Erro da API sobe como exceção com mensagem legível em português. O cru — stack trace,
classe interna do servidor — é descartado antes de qualquer log: no Jupiter isso são
1.978 tokens contra 17 da mensagem, e o cru é a resposta errada.

Nome de ferramenta vem da pergunta do dono, não da função do Moodle: `o_que_vence`
é bom nome, `get_action_events_by_timesort` não é (§5 do `SPEC1.md`).

## 4. Antes de cada commit

```bash
./scripts/gate.sh
```

Três checagens, na ordem em que a mais barata que pode reprovar vem antes:

1. **Nenhum segredo do `.env` em arquivo rastreado** (Invariante 3). Primeiro porque é
   a única falha do gate que é irreversível — commit empurrado com segredo não se
   desfaz apagando o commit. Imprime o NOME da variável e o arquivo, nunca o valor.
   `RUCARD_HASH` no `.env.example` e no `SPEC1.md` é isento **por par**, não por
   variável: a mesma hash em qualquer outro arquivo reprova.
2. **`fixtures/moodle/raw/` segue gitignorada** (§3.3).
3. **A suíte offline**, incluindo a camada `handshake` — que sobe cada servidor como
   processo e aperta a mão com ele. Ela é offline de verdade: `initialize` e `tools/list`
   não passam por `chamar_ferramenta`, que é onde mora qualquer credencial. Custa ~6 s
   (um processo por servidor, escopo de sessão) e é o que impede o furo que ficou três
   vezes neste backlog — `main()` quebrado com a suíte verde.

   A camada `live` NÃO entra: precisa de rede e do token pessoal, e um gate que depende da
   USP estar de pé reprova commit por motivo errado.

O gate foi verificado sabotando cada checagem uma a uma — as três reprovam quando
devem (§9, 31/08/2026). A primeira versão dele passava sem ter verificado nada, porque
procurava o `.env` só no diretório atual e um worktree não tem o dele; hoje usa
`usp_mcp.env.achar_env` e **reprova** se não achar `.env` nenhum, em vez de reportar OK.

**Um teste que falha por erro de coleta, erro de setup ou fixture ausente não está
vermelho, está quebrado** — conserte antes de commitar. Os três casos que já morderam:
módulo ausente aborta a coleta inteira e some com os verdes; construir o objeto sob teste
numa fixture do pytest transforma `FAILED` em `ERROR`; e a fixture que sobe o servidor no
handshake fazia o mesmo com o caso mais importante da suíte (o servidor não sobe) — hoje
ela **guarda** o diagnóstico e quem reprova é o teste.

**Sabotagem se faz sobre árvore limpa.** Verificar um teste quebrando de propósito o que
ele protege é a prática deste repo (o gate, o handshake). Faça `git add` antes: o
`git checkout` que desfaz a sabotagem desfaz junto qualquer conserto não estagiado — e o
vermelho que sobra parece do teste, não da restauração (§9, 31/08/2026).

O gate não substitui a Definição de Pronto do `CLAUDE.md` §5 — ele cobre "nenhum
segredo entrou", e o dado registrado e o achado colateral continuam sendo humanos.

Mensagem de commit: `feat|fix|chore|docs|test(escopo): descrição`.

## 5. Fluxo de merge — `main` é a referência

| | Mudança direta | Trabalho faseado |
|---|---|---|
| Branch | `fix/…`/`feat/…` curta, saindo da `main` | 1 guarda-chuva `feat/<tema>-vN` + N branches de etapa saindo DELA |
| Destino do PR | `--base main` | Etapas: `--base <guarda-chuva>`. Só o PR final: `--base main` |

**A regra de ouro do faseado:** a `main` só aparece **uma vez**, no PR final.
Nunca force-push na `main`.

## 6. Verificação honesta

**Nunca afrouxe uma verificação para passar** — se o gate falha, o problema é o
código ou o dado. Uma verificação que não pode falhar não verifica nada.

O análogo desta regra na fase de descoberta: se uma questão do §4 do `SPEC1.md`
ainda não tem dado, ela continua aberta. Fechá-la por conveniência é afrouxar o
gate do projeto inteiro — e o Anexo A (§7) existe justamente como registro de uma
vez em que a tentação apareceu.
