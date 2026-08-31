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
| 31/08/2026 | `server.py` lia `MOODLE_TOKEN`/`MOODLE_URL` de `os.environ` sem ninguém carregar o `.env` para ele. | `usp_mcp/moodle/server.py` | média | ✅ fechado 31/08 — `usp_mcp/env.py` compartilhado entre `conftest` e `server`; decisão no §9 |
| 31/08/2026 | Não existe fixture de erro do Moodle: os testes de erro do cliente asseguram o contrato da camada, nunca a forma do erro real. Capturar um `invalidtoken` com token propositalmente inválido é barato e não toca a conta. | `fixtures/moodle/`, `tests/moodle/test_cliente.py` | média | 🔵 aberto |
| 31/08/2026 | Três caminhos sem teste offline: o transporte HTTP real do cliente, o caminho autenticado de `chamar_ferramenta` e o adaptador stdio de `main()`. Verde na suíte não é verde neles. | `usp_mcp/moodle/{cliente,server}.py` | média | 🔵 aberto |
| 31/08/2026 | O `.venv` não existe no repo nem em worktree novo, e o `.env` também não (gitignorado, não copiado por `git worktree add`). | repo | baixa | ✅ fechado 31/08 — `requirements-dev.txt` criado; o `.env` passou a ser achado pelo `conftest`, o venv segue por diretório (é o certo) |
| 31/08/2026 | `main()` do servidor MCP foi escrito contra a API antiga do SDK (`Server` + `@list_tools`) e não funcionava com o `mcp` 2.1.1 (`MCPServer` + `@tool`). A suíte estava 99/99 verde com ele quebrado — nenhum teste o alcança. | `usp_mcp/moodle/server.py` | alta | ✅ fechado 31/08 — reescrito e verificado por handshake stdio real; `--auto-verificar` reduz a chance de repetir |
