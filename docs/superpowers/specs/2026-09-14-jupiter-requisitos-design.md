# O pré-requisito que o código descobrível não tem — design

> 14/09/2026. A fatia de "resolver curso" foi desenhada para destravar o
> pré-requisito do `disciplina`. A medição mostrou que o caminho óbvio entrega
> justamente o `codcur` que responde **vazio** para as disciplinas do dono, e o
> desenho virou do avesso: a pergunta passa a ser respondida pela **sigla**, não
> pelo curso.

## O que foi medido, antes de qualquer desenho

Onze chamadas à mão ao JupiterWeb (dado público, sem credencial), 14/09.

### 1. O código que dá para descobrir é o que não responde

| disciplina | `3033-0` (o que `pubListarCursoEntrada` lista) | `3032-0` (o que não aparece em lugar nenhum) |
|---|---|---|
| PSI3323 | **0 linhas** | PSI3322 `[CR]` |
| PTC3314 | **0 linhas** | PTC3213 `[PR]`, PSI3213 `[PR]` |
| MAT2454 | MAT2453 `[PR]` | — |

`pubGradeCurricular {3033,0}` → 67 registros, semestres ideais **1 a 5**; PSI3323
e PTC3314 não estão nela. `pubGradeCurricular {3032,0}` → **vazio**, embora 3032
seja quem carrega os requisitos. São duas metades do mesmo programa sob códigos
diferentes — o que o §5.1 do recon registrou como discrepância e não explicou.

**Consequência de desenho:** uma ferramenta `curso` construída sobre
`pubListarCursoEntrada` — o único caminho DWR de descoberta — entregaria ao
modelo o `codcur` que faz `disciplina` responder *"a consulta não trouxe nenhuma
linha"* para PTC3314. Correta e inútil.

### 2. Filtrar por "vigente" piora a resposta

`listarCursosRequisitos?coddis=MAT2455` → 23 currículos:

| | tem requisito | `(sem linha)` |
|---|---|---|
| **na lista de ingresso** | 3033, 3152 | **3023, 3073, 3084, 3093, 3123, 3201, 3251** |
| fora da lista | 3021, 3022, 3032, 3044, 3072, 3083, 3091, 3092, 3112, 3122, 3151, 3200, 3250 | — |

Os currículos **novos** estão vazios: o curso existe, a estrutura é nova
(projeto piloto), o requisito ainda não foi cadastrado. Cortar o que está fora
da lista de ingresso devolveria "nada" exatamente para as turmas recentes.

Os pares 3021/3022/**3023**, 3072/**3073**, 3083/**3084**, 3092/**3093**,
3122/**3123**, 3200/**3201**, 3250/**3251** são o mesmo curso em gerações de
currículo; o maior é o que consta como ingresso hoje.

### 3. A ausência tem quatro formas, e nenhuma é "não precisa de nada"

| forma | exemplo medido |
|---|---|
| bloco existe, zero linhas | MAT2455 em 3023 |
| zero blocos na página inteira | **PTC3313: 26.623 B, nenhum `Curso:`** |
| curso não informado | o `disciplina` de hoje |
| sigla inexistente | erro no corpo com HTTP 200 (já tratado) |

PTC3314, PTC3360 e PTC3361 aparecem **só** sob 3032, 6º período. Da ênfase (7º) e
do módulo (9º) em diante — estruturas que o dono descreveu e que viram curso
novo — esse endpoint não registra nada. O silêncio do segundo caso é, muito
provavelmente, essa fronteira.

### 4. Dois "não verificado" fechados, e uma hipótese rejeitada

- `pubObterInfoCurso {3033,0}` → **objeto vazio**, 196 B. Estava como não
  verificado no §8 do recon desde 31/08. Não serve de fonte de vigência —
  nenhum payload do Jupiter tem campo de vigência.
- `pubListarColegiado` → 47 unidades, só `codclg`/`nomclg`.
- **Hipótese rejeitada:** `codclg` como prefixo de `codcur`. Oito colegiados
  (`1 2 3 5 6 7 8 9`) são prefixo de outro, então `27223` pode ser da unidade
  `2` ou da `27`. Derivar a unidade do código do curso é chute, e não se faz.
  Mas *pertencimento* é decidível: basta testar os ≤2 candidatos.

### 5. Há três tipos de exigência, e o `main` de hoje mostra um só

O HTML usa três rótulos. Cruzando com o DWR **no mesmo par** (curso, disciplina),
o discriminador é `stamtrrcp`, campo que o `disciplina` de hoje descarta:

| DWR | HTML | o que significa para quem se matricula |
|---|---|---|
| `tipreq=PR`, `stamtrrcp=N` | "Requisito" | exigência dura |
| `tipreq=PR`, `stamtrrcp=S` | "Requisito fraco" | dá para matricular devendo |
| `tipreq=CR`, `stamtrrcp=N` | "Indicação de Conjunto" | correquisito, cursa junto |

Verificado em 3 pares (MAT2455 em 3250 e em 3032; PSI3323 em 3032) — **é um
mapeamento de 3 pontos, não uma lei**, e entra assim no §9.

O mesmo par pode ser duro num currículo e fraco em outro: MAT2454 é "Requisito"
em 3250 (Minas/Petróleo) e "Requisito fraco" em 3032 (Elétrica). Ou seja, o tipo
é propriedade do **currículo**, não da dupla de disciplinas — mais uma razão
para a resposta sair por curso, e não achatada.

**Dois defeitos no que já está na `main`**, ambos em `formatar()` de
`usp_mcp/jupiter/server.py`: (a) tudo sai sob o rótulo "Pré-requisito:", então
PSI3322 — correquisito de PSI3323 — é anunciado como exigência prévia; (b)
`stamtrrcp` nunca é lido, então "fraco" e "duro" ficam indistinguíveis. O
primeiro é resposta errada; o segundo é uma distinção que muda a decisão de
matrícula do aluno.

## O que muda

1. **Ferramenta nova `requisitos(sigla)`** — um parâmetro, a sigla que o aluno
   já sabe. Nenhum `codcur` na superfície: os códigos são detalhe de
   implementação do JupiterWeb, e a medição mostrou que são inconsistentes.
2. **Segundo transporte, com allowlist própria.** `listarCursosRequisitos` é
   `GET` de HTML, não DWR. A política ganha uma allowlist de **caminho** —
   apenas esse — pelo mesmo motivo do §2 do SPEC: o default é negar, e um
   buscador genérico de URL anularia qualquer filtro.
3. **Parser de bloco** (`requisitos.py`), validado offline contra
   `fixtures/jupiter/html-listarCursosRequisitos-PSI3323.html`. Recorta
   `Curso: <b>CODCUR NOMCUR</b> - Habilitação: NOMHAB (período) - Período ideal:
   N` e as linhas de disciplina abaixo dele, com o rótulo de tipo. Redução
   medida: ~30 kB → ~600 B.
4. **A allowlist DWR cresce de 2 para 3 consultas**, com `pubListarCursoEntrada`
   — usada só para decidir pertencimento à lista de ingresso, nos ≤2 colegiados
   candidatos, com o TTL de 120 dias que já existe.
5. **Cada bloco sai rotulado**: `curso de ingresso vigente`, ou `não consta na
   lista de ingresso — currículo antigo, ênfase ou módulo; o JupiterWeb não
   distingue os três`. A segunda frase é literal: as três causas não são
   distinguíveis com o dado disponível, e escolher uma seria inventar.
6. **Os quatro silêncios ganham texto próprio** (Invariantes 6 e 7). Nenhum
   deles pode ser lido como "não há exigência":
   - bloco vazio → *"o currículo 3023 não tem requisito cadastrado. Comum em
     estrutura curricular nova: o curso existe, o cadastro ainda não."*
   - zero blocos → *"o JupiterWeb não lista requisito para esta disciplina em
     curso nenhum. Da ênfase (7º) e do módulo (9º) em diante esse endpoint
     costuma não ter registro — não conclua que não há exigência."*
7. **Os três tipos saem distintos**, aqui e no `disciplina` que já existe:
   *"requisito"*, *"requisito fraco (pode matricular devendo)"* e *"correquisito
   (cursa junto)"*. O rótulo do HTML sai **verbatim** junto, porque é o que o
   aluno vê no JupiterWeb e é a âncora de conferência.
8. **O `disciplina` sem curso passa a apontar para `requisitos`** em vez de
   pedir um par `(codcur, codhab)` que ninguém sabe de cabeça.

## O que NÃO muda

- **Ferramenta `curso` de navegação unidade→curso: fica para a fatia seguinte.**
  A medição mostrou que ela não destrava o pré-requisito — destrava a grade
  curricular, que é outra pergunta.
- Grade curricular, horário, sala e vagas seguem fora, e a descrição da
  ferramenta continua dizendo isso.
- `pubObterInfoCurso`, `pubObterInfoCursoWeb`, `pubListarDiscipResp` e
  `recuperarProjetoPedagogico` seguem fora da allowlist.

## Custo

| chamada | bruto | depois do recorte |
|---|---|---|
| `listarCursosRequisitos` (PTC3314, 1 currículo) | 30.720 B | ~400 B |
| `listarCursosRequisitos` (MAT2455, 23 currículos) | 66.116 B | ~3 kB |
| `pubListarCursoEntrada` (por colegiado, cacheado) | 1.576 B | usado só como conjunto |

O teto de 66 kB está abaixo do limite de ~200 kB do Invariante 8, e o parser lê
por bloco — nunca devolve o HTML cru. Cache de 120 dias: requisito muda por
currículo, não por pergunta.

## Testes

Camadas de sempre: `politica` e `contrato` offline, `live` atrás de
`USP_MCP_LIVE=1`. Fixtures novas, todas de dado público:

| fixture | o que trava |
|---|---|
| `html-listarCursosRequisitos-PSI3323.html` (já existe) | o `CR` virando "cursa junto" |
| `html-listarCursosRequisitos-MAT2455.html` | 23 currículos, vigente × antigo, bloco vazio do 3023, e o **mesmo par saindo duro em 3250 e fraco em 3032** |
| `html-listarCursosRequisitos-PTC3313.html` | zero blocos, e o texto que explica o silêncio |
| `dwr-pubListarCursoEntrada-codclg3.txt` (já existe) | o conjunto de ingresso |

As oito perguntas do dono, que são o critério de pronto do §5 do SPEC:

1. "o que eu preciso ter feito antes de PTC3314?" → PTC3213 e PSI3213, sob 3032, 6º
2. "posso pegar PSI3323 junto com PSI3322?" → **sim, é correquisito**
3. "quantos créditos tem PME3344 e qual a ementa?" → regressão da fatia atual
4. "quais os pré-requisitos de MAT2455?" → 23 currículos, vigentes e antigos separados
5. "sou da turma nova de Civil, o que preciso pra MAT2455?" → 3023 vazio, e diz por quê
6. "o que preciso pra PTC3313?" → zero blocos, e diz que silêncio ≠ ausência
7. "preciso de algo pra MAT2453?" → primeira do currículo, ausência real
8. "o que preciso pra PTC9999?" → erro legível
9. "dá pra me matricular em MAT2455 devendo Cálculo II?" → **depende do
   currículo**: em 3032 é requisito fraco, em 3250 é duro

**Sabotagem obrigatória**, pela lição do T47: asserção sobre o **parâmetro
enviado**, não só sobre a saída. O dublê de transporte devolve a fixture
aconteça o que acontecer, então um teste que só olha a saída fica verde com a
sigla trocada.
