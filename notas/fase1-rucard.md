# Fase 1 — linha 12: RUCard (captura de 27/08/2026)

Fixtures: `fixtures/rucard/{restaurants,menu_6,menu_7,menu_8,menu_9}.json`.
Semana capturada: 24/08 a 30/08/2026 (seg→dom). Dado público, sem credencial pessoal —
não passa por higienização (§3.3 vale para o Moodle).

## Custo medido (§3.2)

| resposta | bytes | ~tokens (bytes/4) | chamadas |
|---|---:|---:|---:|
| `/restaurants` | 27.661 | ~6.900 | 1 |
| `/menu/6` | 2.938 | ~730 | 1 |
| `/menu/7` | 2.306 | ~580 | 1 |
| `/menu/8` | 3.108 | ~780 | 1 |
| `/menu/9` | 3.602 | ~900 | 1 |

"O que tem no bandejão hoje" nos 4 RUs do Caio = **4 chamadas**, ~3.000 tokens crus, para
extrair 8 refeições — das quais interessa ~1/7 do payload (só o dia de hoje). Não existe
endpoint que devolva vários RUs de uma vez.

`/restaurants` a ~6.900 tokens é a resposta mais cara do projeto até agora, e é a mais
estática de todas. Devolver ela crua para o modelo é desperdício; ela é tabela de apoio
(id → nome, horário, preço), não resposta.

## Correções ao §1.2

1. **A forma do `/menu/{id}` não é uma lista de 7 dias.** É objeto com três chaves:
   `message` (`{error: bool, message: str}`), `meals` (lista de 7) e `observation`
   (`{"observation": "Cardápio sujeito a modificação."}`). Um dia tem `date` (`DD/MM/AAAA`),
   `lunch` e `dinner`.

2. **"Fechado" não tem grafia estável.** RU 6 devolve `"Fechado"`; RUs 7, 8 e 9 devolvem
   `"FECHADO"`. Qualquer comparação tem que ser case-insensitive. O §1.2 registrava só
   `"Fechado"`.

3. **Não há café da manhã no `/menu`.** As refeições são só `lunch` e `dinner`, mas
   `workinghours` publica `breakfast` para os RUs 6 e 7 (07:00 às 08:30). "O que tem no café
   da manhã" é pergunta **sem fonte** nesta API — se alguém perguntar, a resposta honesta é
   dizer que o serviço existe e o cardápio não é publicado (Invariante 6).

4. **`hasCashier` é `"false"` nos 18 RUs**, inclusive nos 14 que têm `cashiers` preenchido.
   O campo está sempre errado — e é a *string* `"false"`, que em JS é truthy. Usar
   `len(cashiers)`, nunca esse campo.

5. **`/restaurants` é string em 100% dos valores** (ids, coordenadas, preços com vírgula,
   booleanos). Já estava no §1.2; fica confirmado com exemplo. Mas `/menu` **não** segue a
   mesma regra: `message.error` é booleano de verdade. Os dois endpoints não concordam.

6. **HTML e separador ` - ` não apareceram** nesta amostra (7 dias × 2 refeições × 4 RUs).
   Itens vêm separados só por `\n`. Isso não refuta o §1.2 (que dizia "às vezes") — refuta
   só a ideia de que dá para testar o parser com a semana corrente. Fixture com HTML precisa
   ser construída à mão ou capturada em outra semana.

## Universo real

10 campi, **18 RUs**. Ids conferidos contra o §1.2: 6=CENTRAL, 7=PUSP-CB, 8=FÍSICA,
9=QUÍMICAS. O §1.2 chama o 7 de "Prefeitura/PUSP-C"; a API devolve `PUSP-CB`. Confirma a
regra de resolver por id e tratar `name`/`alias` como exibição.

Horário de semana dos 4: almoço 11:15–14:15 em todos; jantar 17:30–19:45 em 6, 8 e 9;
**o 7 não serve jantar** — e é coerente com o dado: os 7 jantares do 7 vêm `FECHADO`.
Ou seja, dá para distinguir "fechado hoje" de "nunca serve essa refeição" cruzando
`/menu` com `workinghours`, mas só cruzando. Isolado, o `/menu` do 7 parece um RU quebrado.

## Segunda captura — 31/08/2026, segunda-feira, 19:22 (-03)

Quatro dias depois da primeira, do terminal do dono. Motivo: a Fase 2 precisava do TTL do
cache, e ele dependia de uma pergunta que a captura única não podia responder.

| resposta | bytes | semana devolvida |
|---|---:|---|
| `/menu/6` | 2.928 | 31/08 → 06/09 |
| `/menu/7` | 2.303 | 31/08 → 06/09 |
| `/menu/8` | 3.084 | 31/08 → 06/09 |
| `/menu/9` | 3.624 | 31/08 → 06/09 |
| `/restaurants` | 27.661 | — (byte-idêntico ao de 27/08) |

O que a segunda captura resolveu, e o que continua aberto:

1. **A semana vira na segunda, ou antes dela.** Às 19:22 de segunda a resposta já era a
   semana nova. Isso **não** dá o instante da virada — pode ser domingo à noite, pode ser
   segunda de manhã. É suficiente para o desenho do cache, e insuficiente para um TTL que
   dependa da hora: por isso o cliente valida a data que o payload traz em vez de confiar
   só no relógio (§9, Fase 2 do RUCard).
2. **`/restaurants` é estável a ponto de ser byte-idêntico** em quatro dias. Confirma o
   TTL longo para o catálogo e a leitura de que ele é tabela de apoio, não resposta.
3. **A grafia de "fechado" é estável por RU**, não aleatória: 6 capitalizado, 7/8/9 em
   caixa alta, nas duas semanas. A comparação segue case-insensitive — estabilidade
   observada em duas amostras não é contrato.
4. **HTML e ` - ` continuam não aparecendo**: agora em 2 semanas × 7 dias × 2 refeições ×
   4 RUs. O parser tolera os dois (o §1.2 registra que existem), e não há fixture — a que
   houver terá que vir de uma captura que os traga, não da imaginação de quem escreve.
5. **Correção à própria nota** (item 3 de "Correções ao §1.2", acima): eu havia escrito que `workinghours` publica
   `breakfast` "para os RUs 6 e 7". São três — o 9 publica café **no fim de semana**. E o
   9 é o único dos quatro que abre sábado e domingo, o que esta nota não registrava. §1.2
   corrigido.

## Aberto, não testado

- Se `/menu` aceita algum parâmetro de data (o §1.2 diz que não; não retestei — não vale
  chamada nova até haver motivo).
- **A que horas** a semana vira. Fechado o suficiente para o cache (item 1 acima), aberto
  para quem quiser prever a virada. Custaria uma captura por hora numa madrugada de
  domingo, e nenhuma pergunta do dono depende disso hoje.
- Se algum RU já teve cardápio publicado num dia sem horário publicado (ou o inverso). As
  duas fontes concordaram nas duas capturas; o código declara o desacordo se ele aparecer,
  em vez de escolher um lado calado.
