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

<TODO: definir com o primeiro código da Fase 2 — linguagem, runtime, se há core
compartilhado entre o entrypoint local (Moodle) e o servidor público (RUCard/Jupiter),
e como o erro da API sobe até a resposta da ferramenta. O §6 do `SPEC1.md` registra o
que já está decidido e o que continua aberto.>

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
3. **A suíte offline.** A camada `live` NÃO entra: precisa de rede e do token pessoal,
   e um gate que depende da USP estar de pé reprova commit por motivo errado.

O gate foi verificado sabotando cada checagem uma a uma — as três reprovam quando
devem (§9, 31/08/2026). A primeira versão dele passava sem ter verificado nada, porque
procurava o `.env` só no diretório atual e um worktree não tem o dele; hoje usa
`usp_mcp.env.achar_env` e **reprova** se não achar `.env` nenhum, em vez de reportar OK.

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
