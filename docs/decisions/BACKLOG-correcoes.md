# Backlog de correções — achados colaterais

> Durante uma tarefa você percebe algo errado/melhorável que NÃO é a tarefa
> atual: registre aqui e siga — não desvie. Revisite esta lista periodicamente
> (início de ciclo, sessão exploratória).
>
> Isto **não** é o registro de decisões — decisão fechada com dado vai para o §9
> do `SPEC1.md`. Aqui fica dívida em aberto.

| Data | Achado | Onde | Prioridade | Estado |
|---|---|---|---|---|
| 28/08/2026 | Fixtures do Moodle nunca passaram pela higienização do §3.3 — têm `userid`, nome e nota. Ficam gitignoradas até lá. | `fixtures/moodle/raw/` | alta (bloqueia versionar fixture de teste) | 🔵 aberto |
| 31/08/2026 | HTML de turma nomeia professor real e traz sala/vagas; gitignorado como evidência, pendente de higienização. | `fixtures/jupiter/html-obterTurma-*.html` | média | 🔵 aberto |
| 31/08/2026 | Não existe gate automatizado — o `CLAUDE.md` §3 tem o `<TODO>`. Definir junto com o primeiro código da Fase 2. | repo | média (vira alta quando houver código) | 🔵 aberto |
