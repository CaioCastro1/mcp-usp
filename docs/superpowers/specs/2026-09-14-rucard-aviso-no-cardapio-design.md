# O comunicado que virou prato — design

> 14/09/2026. Revisão de má prática nos servidores RUCard e Jupiter, achado nº 1.
> Descoberto numa chamada ao vivo, não nas fixtures: o RUCard passou a anexar um
> comunicado dentro do campo de cardápio, e a ferramenta o imprime como comida.

## O que foi medido

Chamada real `bandejao(dia="hoje", refeicao="almoco")` em 14/09/2026, 4 RUs. Em três
deles (PUSP-CB, FÍSICA, QUÍMICAS) o campo `lunch.menu` termina assim:

```
Salada de escarola
Goiabada
Minipão / refresco

**Os Restaurantes Universitários não fornecem copos descartáveis. Tragam suas canecas.**
```

A linha é markdown em negrito, separada por linha em branco, e aparece em **todos
os cinco dias úteis** da semana de 14/09 a 20/09 no RU 7 (fixture capturada:
`fixtures/rucard/menu_7_semana_14-09.json`, 2.784 B, 6 ocorrências).

O `_itens_e_opcao` de `usp_mcp/rucard/ferramentas.py` divide o texto por linha e
trata toda linha que não começa com `Opção:` como item. Resultado no texto que o
modelo lê, três vezes na mesma resposta:

```
FÍSICA · almoço · 11:15 às 14:15 · R$ 2,00 (aluno) · 1005 kcal
  Arroz / feijão / arroz integral · Filé de peito de frango empanado · ... · Minipão / refresco · **Os Restaurantes Universitários não fornecem copos descartáveis. Tragam suas canecas.**
```

Custo: ~25 tokens por ocorrência, ~75 por resposta, e a informação errada: o modelo
lê um "prato" que é um comunicado, repetido. A docstring do próprio módulo previa
"tolerância, não teste" para HTML e ` - `; este caso é outro, e agora tem fixture.

## Decisão

1. **Linha de comunicado sai da lista de itens e vira aviso** (Invariante 7: nada
   é descartado; o que não é cardápio é declarado como o que é).
2. **Duas regras, ambas documentadas no código**, para reconhecer comunicado:
   - a linha inteira está entre `**` e `**` (o caso medido);
   - a linha tem 6 ou mais palavras **e** termina em `.` ou `!` — frase, não prato.
     Nome de prato nas duas semanas de fixture nunca termina em ponto.
3. **Um aviso por texto distinto, nomeando os RUs** em que apareceu:
   `⚠ aviso publicado no cardápio de PUSP-CB, FÍSICA, QUÍMICAS: Os Restaurantes
   Universitários não fornecem copos descartáveis. Tragam suas canecas.`
   Três ocorrências viram uma linha. Se o texto for diferente entre RUs, são avisos
   diferentes.
4. **A projeção estruturada guarda o dado por refeição** no campo novo
   `avisos_publicados: list[str]` (entra em `CAMPOS_REFEICAO`, que é a trava
   categórica R36). O texto para o modelo mostra só o agregado.
5. **Os `**` são removidos** do texto do aviso: são formatação da fonte, não conteúdo.

## O que NÃO muda

- Nenhuma rota nova, nenhuma allowlist tocada, nenhuma chamada a mais.
- `opcao`, `opcao_vegetariana_marcada`, `calorias`: intocados.
- A fixture nova é dado público e entra no git (o RUCard não tem dado pessoal).

## Riscos aceitos

- A regra de "frase" pode errar um prato com 6+ palavras terminado em ponto. Não há
  nenhum nas ~120 refeições de fixture; se aparecer, a linha vira aviso, não some.
- Um comunicado sem negrito e sem ponto final passa como prato, como hoje. É o
  limite declarado: a regra reconhece o que foi medido, não o que se imagina.

## Aceite

- `bandejao(dia="14/09/2026", restaurantes=["7"])` sobre a fixture nova: nenhum item
  contém "canecas" nem `**`; há exatamente um aviso contendo "canecas" e "PUSP-CB".
- Mesma fixture servida para dois RUs: um aviso só, com os dois nomes.
- `_itens_e_opcao` continua devolvendo os itens e a opção como antes para as
  fixtures da Fase 1 (R33c intacto).
- Teto de custo R34/R37b continua verde.
