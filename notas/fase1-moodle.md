# Fase 1 — Moodle, linhas 1 a 6 (captura de 28/08/2026)

Cru em `fixtures/moodle/raw/` (gitignorado — tem userid, nome e nota).
Nada aqui passou pela higienização do §3.3 ainda.

## Custo medido (§3.2)

| # | chamada | bytes | ~tokens | chamadas |
|---|---|---:|---:|---:|
| 1 | `core_webservice_get_site_info` | 31.386 | ~7.800 | 1 |
| 2 | `core_enrol_get_users_courses` | 104.712 | ~26.200 | 1 |
| 3 | `core_course_get_contents` (1 curso) | 58.049 | ~14.500 | 1 |
| 4 | `mod_assign_get_assignments` **sem parâmetro** | 1.005.502 | **~251.000** | 1 |
| 4' | `mod_assign_get_assignments` com 10 `courseids` | 38.123 | ~9.500 | 1 |
| 6 | `core_calendar_get_action_events_by_timesort` (50) | 541.022 | **~135.000** | 1 |

Duas dessas respostas sozinhas não cabem numa janela de contexto confortável. Isso não é
detalhe de otimização: **resumir no servidor é requisito, não escolha de design.**

## Linha 1 — site_info

447 funções expostas (o §1.3 dizia "~400"). Versão 5.0.8+ (Build 20260722), confirma o §1.3.
`downloadfiles=1` e `uploadfiles=1` — o token *pode* escrever; o Invariante 1 é que impede,
não a API.

**Erro achado no `.env`:** `MOODLE_USERID` tinha sido preenchido com o `username` (o número
USP, 8 dígitos) em vez do `userid` interno do Moodle (6 dígitos). `get_users_courses` com o
userid errado devolve lista vazia — o falso "não tem nada" que o Invariante 6 proíbe. Vale
como caso de teste: a ferramenta tem que distinguir "sem matrícula" de "userid errado".

## Linha 2 — quais disciplinas, e o filtro do §3.2.1

74 matrículas acumuladas (startdate de 2021 a 2026). O §3.2.1 estava certo: o número que sai
da API não é "disciplinas deste semestre".

**O discriminador é `startdate`/`enddate`.** Dois filtros independentes convergem no mesmo
conjunto exato de **10 disciplinas**:

- `enddate` no futuro ∧ `visible` → 10
- `startdate` nos últimos 120 dias → 10
- interseção: idêntica (0 de diferença nos dois sentidos)

As 10 começam em 03–04/08/2026 e terminam em 12–14/12/2026.

Descartados, com motivo:

- **`visible` é inútil** — vale `true` nas 74. Não separa nada.
- **`hidden`** separa 2 de 74; não é semestre, é outra coisa.
- **`shortname` não serve**, apesar de tentador: `PME3344-2026` não marca semestre, e
  `PSI3322-2026-REOF` carrega "2026" mas começou em 23/02 (1º semestre). Ler semestre de
  string de shortname quebra.
- **`lastaccess` ≤ 30d** dá 12: as 10 do semestre mais 2 disciplinas antigas que o Caio
  revisitou em agosto. Superconjunto útil para "o que ando abrindo", errado para "o que
  estou cursando".

## Linha 3 — o que tem dentro de uma disciplina

Curso PSI3323 (142033): 16 seções, 32 módulos — 22 `resource`, 7 `url`, 2 `forum`, 1 `assign`.

**Material não exige chamada extra:** os 22 arquivos já vêm com URL direta dentro de
`contents`. Só 3 módulos não têm `contents` (os 2 fóruns e o assign), e esses têm função
própria de qualquer jeito. Isso fecha a questão "get_contents é suficiente ou exige N
chamadas por módulo" do §4: **é suficiente para material.**

Custo: ~14.500 tokens por disciplina. Puxar as 10 = ~145.000 tokens. Inviável varrer;
viável sob demanda, uma disciplina por vez.

Tem HTML embutido nos campos de descrição — confirma o que o §1.2 dizia do RUCard e vale
aqui também.

### Projeção medida — 31/08/2026

Medido em cima da mesma captura (`course_contents_142033.json`, 58.049 B), sem
nova chamada à conta.

**Composição.** Os 22 `resource` e os 7 `url` produzem **29 entradas em
`contents`**. Por mimetype: **19 `application/pdf`**, 1 `.docx`, 1 `image/jpeg`,
1 `application/octet-stream`, e 7 sem mimetype — os links externos, cujos hosts
saem do domínio da USP (`youtube.com`, `docs.google.com`, `ni.com`).

**Campos de um `contents`:** `filename`, `filesize`, `fileurl`, `mimetype`,
`timecreated`, `timemodified`, `author`, `userid`, `filepath`, `type`,
`license`, `isexternalfile`, `sortorder`.

**Projeção.** Guardando só o que responde "que arquivos tem aqui" — seção, nome
do módulo, tipo, e por arquivo `filename`/`filesize`/`mimetype`/`timemodified` —
sobram **6.486 B, ~1.621 tokens: 11,2% do cru.** Uma ferramenta de material cabe
folgado no contexto por disciplina. Varrer as 10 continua inviável (145k crus);
sob demanda, uma por vez, é confortável.

**O `fileurl` não carrega o token: 0 de 29.** A resposta como capturada não tem
segredo dentro, o que é bom e é também o aviso — para **baixar** o arquivo o
token precisa ir junto na URL, e é aí que o Invariante 3 morde. Uma ferramenta
que devolva URL pronta põe a credencial no contexto do modelo e em todo log por
onde ela passar. **O download com token anexado não foi verificado neste repo.**

**`author` e `userid` vêm dentro de `contents`** — quem subiu o arquivo. É dado
pessoal e cai na higienização do §3.3 se isto virar fixture versionada.


## Linha 4 — entregas

**Sem parâmetro, a função devolve as 74 disciplinas: 1 MB, ~251.000 tokens, 303 assigns.**
Passando os 10 `courseids` do semestre: 38 kB, ~9.500 tokens — **redução de 96,2%**.
Qualquer ferramenta que chame essa função sem escopo explícito estoura o contexto.

No semestre corrente: **20 assigns**, dos quais **12 com `duedate` no futuro**, nenhum com
`duedate = 0`. Data é epoch int.

**4 das 10 disciplinas têm pelo menos um assign.** As outras 6 têm zero — e as que têm,
concentram: PSI3472 tem 11, PTC3312 e PTC3314 têm 4 cada, PSI3323 tem 1.

## Linha 6 — o que vence, pelo calendário

35 eventos, e **541 kB para transportá-los**. A causa é específica e vale registrar: cada
evento embute um objeto `course` de **9,5 kB** — 88% do payload — repetido a cada evento da
mesma disciplina. Os campos que respondem "o que vence" (`name`, `timesort`,
`course.shortname`, `url`) somam **132 bytes por evento**.

Ou seja: ~135.000 tokens carregam ~4,6 kB de resposta útil. Proporção de ~1000:1. É o
argumento mais forte do projeto inteiro a favor de resumir no servidor.

**Cobertura:** só `assign` (17) e `quiz` (18); `eventtype` só `due` e `close`. Nenhum evento
manual, de curso ou de usuário.

O calendário **vê quiz, que o `get_assignments` não vê** — 6 disciplinas aparecem no
calendário contra 4 que têm assign. As duas fontes não se substituem.

## Questões do §4 que fecham aqui

**"Que fração das disciplinas do semestre usa o Moodle de forma viva?"** — medido, não
estimado: **4 de 10** têm entrega; **6 de 10** aparecem no calendário (entrega ou quiz);
4 de 10 não aparecem em nenhuma das duas. Falta medir material postado e aviso em fórum
(linhas 3 e 10) para as 10 antes de chamar isso de resposta final.

**"O calendário cobre prova presencial?"** — **não.** Ele só conhece prazo de atividade do
Moodle: assign e quiz, `due` e `close`. Uma prova marcada no quadro da sala não existe ali.
Pelo Invariante 6, "o que vence" tem que dizer que não sabe de prova presencial, em vez de
devolver a lista e deixar parecer completa.

## Ainda aberto

Linhas 5, 7, 8, 9, 10, 11 — `submission_status`, as duas visões de nota,
`get_updates_since`, fóruns e o feed iCal.
