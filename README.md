# usp-mcp

Ferramentas para responder perguntas sobre a vida acadêmica na USP — cardápio dos
bandejões, prazos e material do e-Disciplinas, catálogo de disciplinas do JupiterWeb.

**Projeto não-oficial, sem nenhum vínculo com a Universidade de São Paulo.** Usa APIs
não documentadas, descobertas por observação. Elas podem mudar ou sumir sem aviso, e
"está público" não equivale a "liberado para redistribuir" — ver Invariante 8 do
`SPEC1.md`.

## Estado — 31/08/2026

**Dois servidores MCP rodando, uma ferramenta cada, ambas verificadas contra a USP.**

| Servidor | Ferramenta | Responde |
|---|---|---|
| `usp-moodle` | `o_que_vence` | O que tenho para entregar nos próximos N dias |
| `usp-jupiter` | `disciplina` | Créditos, carga horária, ementa e pré-requisito, pela sigla |

O Moodle é entrypoint **local** por carregar credencial pessoal; o Jupiter não usa
credencial nenhuma e por isso segue candidato a servidor hospedado (§6 do `SPEC1.md`).
Suíte: 177 testes offline em menos de 1 s, mais uma camada `live` atrás de
`USP_MCP_LIVE=1` que fala com a USP de verdade.

**O que ainda não existe:** bandejão, notas, material de aula, aviso de professor —
cinco das sete perguntas candidatas do §5. Horário, sala e vagas não são prometidos.
Nenhuma ferramenta nasce por conveniência: o critério está no §5, e as questões
abertas do §4 fecham com dado registrado no §9.

Comece por `SPEC1.md` — ele é a autoridade do projeto, e o §9 registra cada decisão
tomada, com o dado que a fechou e o que foi descartado.

- `usp_mcp/` — os servidores, um pacote por sistema
- `tests/` — três camadas: política e contrato offline, `live` atrás de env var
- `notas/` — análise por sistema, com custo medido em bytes e tokens
- `fixtures/` — respostas cruas capturadas (as do Moodle ficam fora do git: têm dado pessoal)
- `scripts/` — chamadores da descoberta e o gate de pré-commit
- `docs/decisions/BACKLOG-correcoes.md` — a dívida que está em aberto

## Rodando

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt
./scripts/gate.sh
```

O `.mcp.json` versionado já registra os dois servidores, sem segredo. Abra um cliente
MCP neste diretório e pergunte.

## Configuração

Copie `.env.example` para `.env`. O token do Moodle é pessoal e nunca sai da máquina de
quem usa (Invariante 4).
