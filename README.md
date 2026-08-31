# usp-mcp

Ferramentas para responder perguntas sobre a vida acadêmica na USP — cardápio dos
bandejões, prazos e material do e-Disciplinas, catálogo de disciplinas do JupiterWeb.

**Projeto não-oficial, sem nenhum vínculo com a Universidade de São Paulo.** Usa APIs
não documentadas, descobertas por observação. Elas podem mudar ou sumir sem aviso, e
"está público" não equivale a "liberado para redistribuir" — ver Invariante 8 do
`SPEC1.md`.

## Estado

**Fase 1 (descoberta) concluída.** Ainda não há servidor MCP: o que existe é fixture,
medição e registro de decisão. O desenho das ferramentas é a Fase 2, e o critério para
uma existir está no §5 do `SPEC1.md`.

Comece por `SPEC1.md` — ele é a autoridade do projeto, e o §9 registra cada decisão
tomada, com o dado que a fechou e o que foi descartado.

- `notas/` — análise por sistema, com custo medido em bytes e tokens
- `fixtures/` — respostas cruas capturadas (as do Moodle ficam fora do git: têm dado pessoal)
- `scripts/` — chamadores usados na descoberta

## Configuração

Copie `.env.example` para `.env`. O token do Moodle é pessoal e nunca sai da máquina de
quem usa (Invariante 4).
