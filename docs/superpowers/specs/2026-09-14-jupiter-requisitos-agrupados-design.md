# Vinte e três currículos, quatro respostas — design

> 14/09/2026. Revisão de má prática nos servidores RUCard e Jupiter, achado nº 2 do
> Jupiter. Só formatação: a projeção de `requisitos` não muda.

## O que foi medido

`server.formatar_requisitos(ferramentas.requisitos("MAT2455"))` sobre a fixture
`html-listarCursosRequisitos-MAT2455.html`: **6.238 B ≈ 1.700 tokens**, 23 blocos.
Dezoito deles têm exatamente as mesmas duas linhas:

```
• 3044 — Habilitação: Engenharia Mecânica (integral), 3º período ideal [não consta na lista de ingresso]
    Requisito fraco (dá para matricular devendo): MAT2454 — Cálculo Diferencial e Integral II
    Requisito fraco (dá para matricular devendo): MAT3458 — Álgebra Linear II
```

Agrupando os currículos pelo **conjunto exato de (sigla, nome, tipo)** das
exigências, os 23 caem em **4 combinações**:

| combinação | currículos |
|---|---|
| MAT2454 + MAT3458, ambas requisito fraco | 13 (3022, 3032, 3033, 3044, 3045, 3072, 3083, 3092, 3112, 3122, 3151, 3152, 3200) |
| 2000101 Fundamentos Científicos e Modelagem para Engenharia I, pré-requisito | 7 (3023, 3073, 3084, 3093, 3123, 3201, 3251) |
| MAT2454 + MAT2458, ambas requisito fraco | 2 (3021, 3091) |
| MAT2454 + MAT3458, ambas pré-requisito (duro) | 1 (3250) |

Protótipo do formato agrupado: **2.458 B** (2,5× menor). Para PSI3323 (1 currículo)
o agrupado dá 408 B contra 437 B; para PTC3313 (zero currículo) não muda.

O desenho de 14/09 exige a resposta **por currículo** porque o tipo da exigência é
propriedade do currículo (MAT2454 é dura em 3250 e fraca em 3032). O agrupamento
por conjunto exato **preserva isso por construção**: 3250 fica sozinho no seu grupo
justamente porque o tipo é outro. Nenhuma informação é achatada; só a repetição sai.

## Decisão

### 1. `agrupar_curriculos` em `ferramentas.py`

Função pura: `list[dict]` de currículos → `list[tuple[chave, list[dict]]]`, onde a
chave é `tuple(sorted((sigla, nome, tipo, rotulo)))` das exigências. Ordem dos
grupos: maiores primeiro; o grupo vazio (currículo sem linha de exigência) por
último. Dentro do grupo, a ordem da página (crescente de `codcur`).

### 2. `formatar_requisitos` imprime por grupo

```
Exigências para cursar MAT2455 — 23 currículos, 4 combinações diferentes:

• Requisito fraco (dá para matricular devendo): MAT2454 — Cálculo Diferencial e Integral II; MAT3458 — Álgebra Linear II
    3022 Habilitação: Engenharia Civil (integral, 3º período ideal)
    3032 Ciclo Básico - Engenharia Elétrica (integral, 3º período ideal)
    3033 Ciclo Básico - Engenharia Elétrica (integral, 3º período ideal) [curso de ingresso]
    ...

• Pré-requisito: 2000101 — Fundamentos Científicos e Modelagem para Engenharia I
    3023 Habilitação: Engenharia Civil (integral, 3º período ideal) [curso de ingresso]
    ...

• Pré-requisito: MAT2454 — Cálculo Diferencial e Integral II; MAT3458 — Álgebra Linear II
    3250 Ciclo Básico - Minas/Petróleo (integral, 3º período ideal)

⚠ 13 dos 23 currículos listados não constam na lista de cursos de ingresso. ...
```

- Cabeçalho do grupo: as exigências agrupadas por rótulo (`rotulo_de`), separadas
  por `; `; rótulos diferentes no mesmo grupo separados por ` | `.
- Grupo vazio: `• (a página não traz linha de exigência para estes)`.
- Linha do currículo: `codcur habilitação (período, Nº período ideal)` e a marca
  `[curso de ingresso]` quando `ingresso` é verdadeiro. A ausência da marca não
  vira frase: o aviso já existente explica o que "não constar" pode significar.
- Um currículo só: mesma estrutura, sem a contagem no cabeçalho
  (`Exigências para cursar PSI3323, por currículo:`).
- Zero currículo: inalterado (`Não há exigência listada para ... — leia o aviso:`).

### 3. Teto

| caso | medido | teto |
|---|---|---|
| MAT2455 agrupado | 2.458 B | 3.500 B |

## O que NÃO muda

- `ferramentas.requisitos`, `requisitos.py`, a política, a descrição da ferramenta.
- Os avisos: mesmos textos, mesmo lugar (fim).
- T70–T72 (correquisito, fraco × duro, silêncio) continuam verdes: as palavras que
  eles procuram continuam no texto.

## Aceite

- `agrupar_curriculos` sobre MAT2455: 4 grupos; a soma dos tamanhos é 23; 3033,
  3032 e 3045 estão no mesmo grupo; 3250 está sozinho; os 7 do piloto (3023, 3073,
  3084, 3093, 3123, 3201, 3251) estão juntos.
- Texto de MAT2455: ≤ 3.500 B; `3033` aparece uma vez e sua linha termina com
  `[curso de ingresso]`; a linha de `3032` não tem a marca;
  `Cálculo Diferencial e Integral II` aparece no máximo 3 vezes (uma por grupo que
  a exige).
- Texto de PSI3323: continua contendo `Correquisito (cursa junto)` e `PSI3322`.
