# usp-mcp

Ferramentas para responder perguntas sobre a vida acadêmica na USP — cardápio dos
bandejões, prazos e material do e-Disciplinas, catálogo de disciplinas do JupiterWeb.

**Projeto não-oficial, sem nenhum vínculo com a Universidade de São Paulo.** Usa APIs
não documentadas, descobertas por observação. Elas podem mudar ou sumir sem aviso, e
"está público" não equivale a "liberado para redistribuir" — ver Invariante 8 do
`SPEC1.md`.

## Estado

**Fase 1 (descoberta) concluída nos três sistemas. Fase 2 implementada como uma fatia
vertical em cada um** — uma pergunta real, ponta a ponta, com suíte e custo medido:

| Servidor | Ferramenta | Responde |
|---|---|---|
| `usp-rucard` | `bandejao` | o que tem no bandejão hoje, e onde vale a pena comer |
| `usp-moodle` | `o_que_vence` | o que eu tenho que entregar, e até quando |
| `usp-jupiter` | `disciplina` | créditos, ementa e pré-requisito de uma disciplina |

O que **não** existe: histórico de cardápio, horário/sala de turma, grade curricular,
notas, material — e nenhuma escrita (Invariante 1).

Comece por `SPEC1.md` — ele é a autoridade do projeto, e o §9 registra cada decisão
tomada, com o dado que a fechou e o que foi descartado.

- `usp_mcp/<sistema>/` — código: política, cliente, ferramenta e servidor por sistema
- `notas/` — análise por sistema, com custo medido em bytes e tokens
- `fixtures/` — respostas cruas capturadas (as do Moodle ficam fora do git: têm dado pessoal)
- `scripts/` — chamadores da descoberta, e `gate.sh` antes de cada commit

## Configuração

Copie `.env.example` para `.env`. O token do Moodle é pessoal e nunca sai da máquina de
quem usa (Invariante 4).
