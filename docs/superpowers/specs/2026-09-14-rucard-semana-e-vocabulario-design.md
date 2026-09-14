# A semana inteira numa chamada, e o vocabulário de quem pergunta — design

> 14/09/2026. Revisão de má prática nos servidores RUCard e Jupiter, achados nº 2, 3
> e 4 do RUCard. Três mudanças na mesma ferramenta `bandejao`, todas na projeção e
> na fronteira: nenhuma rota nova, nenhuma chamada a mais à USP.

## O que foi medido

Saída atual (`server.formatar`), fixtures da Fase 1, semana 24/08 a 30/08/2026:

| pergunta | como o modelo responde hoje | custo |
|---|---|---|
| "o que tem hoje?" (4 RUs, almoço e jantar) | 1 chamada | 1.927 B ≈ 510 tokens |
| "o que tem na sexta?" | calcula a data e chama `dia="28/08/2026"` | 1 chamada, se acertar a data |
| "que dia tem lasanha essa semana?" | 5 a 7 chamadas, uma por dia | 5 × ~1.000 B ≈ 1.400 tokens (almoço) |
| "o que tem no bandejão da Prefeitura?" | precisa saber que Prefeitura = PUSP-CB = id `7` | descrição não cita "Prefeitura" |

Protótipo do formato semanal medido sobre as mesmas fixtures (4 RUs × 7 dias):

| refeição | bytes | linhas |
|---|---|---|
| almoço | 4.818 B | 34 |
| almoço e jantar | 8.381 B | 66 |

Requisições HTTP para a semana inteira: **5** (1 catálogo + 4 menus), porque o
`/menu` já devolve a semana e o cliente cacheia por RU. A semana não custa nada a
mais para a USP do que um dia.

Itens comuns a **todas** as refeições abertas da semana: só `Minipão / refresco`.
`Arroz / feijão / arroz integral` não é comum porque alguns dias vêm com `feijão
preto`. A fatoração de itens repetidos rende pouco (~28 × 20 B na semana) e por isso
entra com a regra mais estrita possível, não com heurística.

## Decisão

### 1. `dia` aceita o que a pessoa fala

Além de `hoje`, `amanhã`, `ontem` e data (`DD/MM/AAAA`, `AAAA-MM-DD`, `DD/MM`):

- `depois de amanhã`;
- **nome de dia da semana**, com e sem `-feira`, com e sem acento, abreviado com 3
  letras: `segunda`, `terça`, `terca`, `qua`, `sexta-feira`, `sáb`, `sabado`, `dom`…
  Resolve para **o dia dessa semana** (segunda a domingo da semana de `hoje`),
  inclusive se já passou — é a única semana que tem cardápio, e "o que teve na
  segunda" é pergunta válida na quarta;
- artigo na frente é ignorado: `na sexta`, `no sábado`, `nesta quinta`;
- **`semana`**: os sete dias, segunda a domingo, da semana de `hoje`.

### 2. `restaurantes` aceita nome

O `enum` que o modelo vê passa a ser **`["central", "prefeitura", "fisica",
"quimicas"]`** — o vocabulário de quem pergunta, sem acento porque trafega em JSON
digitado por modelo. O id numérico continua aceito pela função pura (`"6"`…`"9"`)
para não quebrar quem chama por código, e `politica.RUS_PERMITIDOS` continua sendo
a allowlist por **id** (§1.2: resolver por id, `name`/`alias` é exibição — o alias
aqui é entrada do usuário traduzida para id antes de qualquer política).

Aliases aceitos: `central`→6; `prefeitura`, `pusp`, `pusp-cb`→7; `fisica`,
`física`→8; `quimicas`, `químicas`, `quimica`, `química`→9. Nome desconhecido dá
erro legível citando os quatro válidos — não passa para a política como se fosse id.

### 3. Modo semana: `bandejao_semana`

Função pura nova em `ferramentas.py`, ao lado de `bandejao`, que chama `bandejao`
uma vez por dia da semana e agrega:

```
{"inicio": "24/08/2026", "fim": "30/08/2026", "refeicoes": [...],
 "dias": [{"data", "dia_semana", "restaurantes"}, ...7], "avisos": [...]}
```

Avisos iguais entre dias são deduplicados. `chamar_ferramenta` despacha para ela
quando `dia == "semana"`. A ferramenta MCP continua sendo **uma** (`bandejao`): a
pergunta "que dia tem X" é a mesma pergunta do §5 com outro recorte de tempo.

Formato para o modelo (`formatar_semana`), agrupado por RU e refeição, um dia por
linha:

```
Bandejão — semana de 24/08/2026 a 30/08/2026
CENTRAL · almoço · R$ 2,00 (aluno)
  seg 24/08 · 11:15 às 14:15 · 1065 kcal: Arroz / feijão / arroz integral · Iscas de tilápia empanadas · ... | Opção: Grão-de-bico à indiana (V)
  ter 25/08 · ...
  sáb 29/08: não serve
PUSP-CB · almoço · R$ 2,00 (aluno)
  ...
Em todas as refeições acima: Minipão / refresco
⚠ ...
```

Horário fica na linha do dia, não no cabeçalho do RU: o 9 serve jantar até 19:45 em
dia útil e até 19:00 no sábado, e um horário só no cabeçalho mentiria no sábado.
Situação fechada é uma palavra (`não serve`, `fechado`, `indisponível`), não a frase
inteira do detalhe — o detalhe continua na projeção estruturada.

### 4. Fatoração de itens comuns, estrita

Em `formatar` (dia) e `formatar_semana`: se há **duas ou mais** refeições abertas na
resposta, os itens presentes em **todas** elas saem das linhas e vão para um rodapé
`Em todas as refeições acima: A · B`. Com uma refeição só, nada muda. Regra estrita
de propósito: "na maioria" exigiria marcar exceções, e o ganho medido não paga a
complexidade. A projeção estruturada (`itens`) não é alterada — R33c continua
verdadeiro.

## Descrição da ferramenta

Passa a citar "Prefeitura", os nomes de dia e o modo semana. Exemplos de uso na
descrição: `'o que tem no bandejão hoje'`, `'o que tem na sexta?'`, `'que dia tem
lasanha essa semana?'`, `'vale a pena almoçar na Prefeitura?'`. Continua dizendo o
que NÃO faz (só a semana corrente, sem cardápio de café, sem saldo).

## O que NÃO muda

- Nenhuma rota, nenhuma allowlist, nenhuma requisição a mais (teste trava em 5 para
  a semana inteira).
- `refeicao`, `cafe`, situações `nao_serve`/`fechado`/`indisponivel`: intocados.
- O `hoje` continua injetável; `chamar_ferramenta` ganha `hoje=` só para os testes.

## Tetos (com folga de ~30% sobre o medido)

| saída | medido | teto |
|---|---|---|
| dia, 4 RUs, almoço e jantar | 1.927 B | 4.500 B (já existe, R34/R37b) |
| semana, 4 RUs, almoço | 4.818 B | 6.500 B |
| semana, 4 RUs, almoço e jantar | 8.381 B | 11.000 B, < 80 linhas |

## Aceite

- `resolver_dia("sexta", hoje=qua 26/08)` → 28/08; `("segunda")` → 24/08;
  `("dom")` → 30/08; `("na sexta")` → 28/08; `("depois de amanhã", seg 24/08)` → 26/08.
- `resolver_restaurantes(["Prefeitura", "6", "fisica"])` → `["7", "6", "8"]`;
  `(None)` → os quatro; `(["each"])` → `ErroRucard` citando "central".
- `chamar_ferramenta("bandejao", {"dia": "semana", "refeicao": "almoco"})` sobre as
  fixtures: cita `24/08/2026` e `30/08/2026`, tem a linha `sex 28/08`, contém um
  prato de outro dia (`Lombo com molho de limão`, terça no Central), e o transporte
  registrou exatamente 5 rotas.
- Schema: `restaurantes.items.enum == ["central", "prefeitura", "fisica", "quimicas"]`;
  o handshake H8 continua verde (o `Literal` de `main()` acompanha).
- Fatoração: com 4 RUs, `Minipão / refresco` aparece uma vez no texto, na linha
  `Em todas as refeições acima`; com um RU e uma refeição, não há rodapé e o item
  está na linha da refeição.
