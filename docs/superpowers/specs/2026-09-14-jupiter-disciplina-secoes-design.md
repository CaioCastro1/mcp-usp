# A ficha por seção, e uma ferramenta por pergunta — design

> 14/09/2026. Revisão de má prática nos servidores RUCard e Jupiter, achados nº 1,
> 3, 6 e 7 do Jupiter. Quatro mudanças na ferramenta `disciplina`, todas na
> projeção e na fronteira, mais **uma consulta a menos** na allowlist.

## O que foi medido

`server.formatar(ferramentas.disciplina(...))` sobre as fixtures da Fase 1:

| sigla | cabeçalho (3 linhas) | ementa | objetivos | programa | bibliografia | avaliação | texto completo |
|---|---|---|---|---|---|---|---|
| PSI3323 | 154 B | 233 B | 717 B | 388 B | 251 B | 219 B | 2.434 B |
| PTC3314 | 139 B | 355 B | 1.487 B | 937 B | 214 B | 276 B | 3.880 B |
| PTC3314 + inglês | | | | | | | 6.452 B |

A pergunta mais comum da descrição — "quantos créditos tem PTC3314" — é respondida
pelo cabeçalho, 139 B. A ferramenta entrega 3.880 B: **28 vezes** o necessário. O
bloco de objetivos, com a lista de "competências e habilidades", é 38% do texto e
não responde pergunta nenhuma do §5.

Além disso:

- **Duas ferramentas para a mesma pergunta.** `disciplina(codcur, codhab)` e
  `requisitos(sigla)` respondem "o que preciso ter feito antes", e as duas
  descrições dizem isso. O §9 de 14/09 mediu que o único `codcur` que a API deixa
  descobrir (3033) devolve **zero linha** para as disciplinas do dono; `requisitos`
  nasceu justamente por isso. Mesmo assim `codcur`/`codhab` continuam no schema, e
  a resposta vazia carrega **três avisos** de até 600 B explicando por que falhou —
  um deles cita "medido em 14/09", texto de registro de projeto, não de resposta.
- **Bibliografia duplicada na fonte.** `dscbbgdis` de PTC3314 vem com o mesmo
  parágrafo duas vezes. Repassado tal qual.
- **O teste de custo mede o dicionário, não o texto.** T34 (`tests/jupiter/
  test_custo.py`) aplica o teto de 5.000 B ao JSON da projeção. O que o modelo lê é
  `server.formatar(...)`, que nenhum teste mede — e `ingles=True` não é medido em
  lugar nenhum.
- `_auto_verificar` de `usp_mcp/jupiter/server.py` compara só
  `listar_ferramentas()[0]`: o mesmo bug de índice que o handshake pegou no
  `main()` em 14/09, agora no utilitário.

## Decisão

### 1. Parâmetro `secoes`

`disciplina` ganha `secoes: array` com `enum` **`["ementa", "objetivos",
"programa", "bibliografia", "avaliacao", "todas"]`** e default `["ementa"]`.

- O **cabeçalho** (sigla, nome, créditos, carga horária calculada, tipo, ativação)
  vem sempre. É a resposta de "quantos créditos".
- `avaliacao` agrupa `metodo_avaliacao`, `criterio_avaliacao` e
  `norma_recuperacao`: ninguém pergunta por um dos três separadamente.
- `todas` expande para as cinco. Ordem de saída é fixa (a da ficha), não a do pedido.
- Seção desconhecida é erro legível citando as válidas, não silêncio.
- **O que ficou de fora é declarado** (Invariante 7): última linha antes dos avisos,
  `(Seções não incluídas: objetivos, programa, bibliografia, avaliacao. Peça-as em
  secoes, ou secoes=["todas"].)` — ~25 tokens para o modelo saber que existe mais.
- O filtro é na **projeção** (`ferramentas.disciplina`), não só na formatação: o
  dicionário devolvido carrega só as seções pedidas, mais `secoes` e
  `secoes_omitidas`. Assim o teto de custo sobre o dicionário continua fazendo
  sentido.
- `ingles=True` continua valendo para as seções pedidas que têm versão em inglês
  (`nome_en` sempre; `ementa_en`, `objetivos_en`, `programa_en` conforme a seção).

### 2. `codcur` e `codhab` saem de `disciplina`

- O schema fica com `sigla`, `secoes`, `ingles`. `required` continua `["sigla"]`.
- `ferramentas.disciplina` perde o parâmetro `curso`, o campo `pre_requisito`, o
  dicionário `_DISCREPANCIA_CODCUR` e os três avisos longos. Fica **um aviso curto**
  fixo: `Pré-requisito não vem por aqui: use a ferramenta requisitos com a mesma
  sigla.`
- `ClienteJupiter.listar_requisito` é removido, e **`pubListarRequisitoDisciplina`
  sai de `CONSULTAS_PERMITIDAS`** (4 → 3). A allowlist encolhe: é a direção certa do
  Invariante 2, e a trava T23 muda junto com decisão registrada no §9.
- A fixture `dwr-pubListarRequisitoDisciplina-MAT2454.txt` sai da `FATIA` do
  `conftest` mas **fica no disco**: é evidência pública do formato DWR citada em
  `notas/jupiter-recon.md`.
- A descrição de `disciplina` deixa de prometer pré-requisito e aponta para
  `requisitos`. A descrição de `requisitos` não muda.

### 3. Parágrafos repetidos são deduplicados

Em toda seção de texto livre, parágrafos idênticos (separados por linha em branco,
comparados sem diferença de espaçamento) saem uma vez só, na primeira posição.
Não é perda de informação; é a fonte que se repetiu.

### 4. O teto passa a ser sobre o texto

Novos testes de custo medem `server.formatar(...)`:

| caso | medido | teto |
|---|---|---|
| padrão (`secoes=["ementa"]`), PTC3314 | ~700 B (139 + 355 + rótulos + rodapé) | 1.200 B |
| `todas`, PTC3314 | 3.880 B | 5.000 B |
| `todas` + `ingles`, PTC3314 | ~6.700 B | 8.500 B |

O teto do dicionário (T34, 5.000 B) continua, agora sobre `todas`.

### 5. `_auto_verificar` compara todas as ferramentas

Uma sonda por ferramenta declarada, e o utilitário reprova se qualquer uma divergir.

## O que NÃO muda

- `requisitos`, `requisitos.py`, a allowlist de caminho, `pubListarColegiado` e
  `pubListarCursoEntrada`.
- Carga horária calculada (`creaul*15 + cretrb*30`), normalização de sigla, erro da
  USP sem stack trace.
- Espanhol nunca sai.

## Aceite

- `disciplina("PTC3314")` sem `secoes`: o dicionário tem `ementa` e não tem
  `objetivos`, `programa`, `bibliografia`, `metodo_avaliacao`;
  `secoes_omitidas == ["objetivos", "programa", "bibliografia", "avaliacao"]`.
- `secoes=["avaliacao"]`: tem os três campos de avaliação e não tem `ementa`.
- `secoes=["todas"]`: tem as cinco; texto ≤ 5.000 B.
- `secoes=["horario"]`: `ErroJupiter` citando `ementa` e `todas`.
- Texto padrão contém `Seções não incluídas` e `requisitos`; texto com `todas` não
  contém `Seções não incluídas`.
- `bibliografia` de PTC3314 contém `Mariotto` **uma** vez.
- `inspect.signature(ferramentas.disciplina)` não tem `curso`; o schema não tem
  `codcur` nem `codhab`; `set(CONSULTAS_PERMITIDAS)` tem três consultas.
- Handshake H6–H8 verdes: `secoes` chega ao fio com `enum` e descrição.
