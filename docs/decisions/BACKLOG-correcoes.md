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
| 31/08/2026 | Não existia gate automatizado — o `CLAUDE.md` §3 e o `CONVENTIONS.md` §4 tinham `<TODO>`. | repo | média | ✅ fechado 31/08 — `scripts/gate.sh`: segredo, cru ignorado, suíte offline; verificado por sabotagem das três checagens; decisão no §9 |
| 31/08/2026 | `server.py` lia `MOODLE_TOKEN`/`MOODLE_URL` de `os.environ` sem ninguém carregar o `.env` para ele. | `usp_mcp/moodle/server.py` | média | ✅ fechado 31/08 — `usp_mcp/env.py` compartilhado entre `conftest` e `server`; decisão no §9 |
| 31/08/2026 | Não existia fixture de erro do Moodle: os testes de erro asseguravam o contrato da camada, nunca a forma do erro real. | `fixtures/moodle/`, `tests/moodle/test_cliente.py` | média | ✅ fechado 31/08 — três fixtures reais (`invalidtoken`, `invalidparameter`, `limite_fora_da_faixa`) ligadas em T52/T56/T57. HTML de manutenção e timeout não são capturáveis sob demanda e seguem como contrato de camada |
| 31/08/2026 | Três caminhos sem teste offline: o transporte HTTP real do cliente, o caminho autenticado de `chamar_ferramenta` e o adaptador stdio de `main()`. Verde na suíte não é verde neles. | `usp_mcp/moodle/{cliente,server}.py` | média | 🔵 aberto |
| 31/08/2026 | O `.venv` não existe no repo nem em worktree novo, e o `.env` também não (gitignorado, não copiado por `git worktree add`). | repo | baixa | ✅ fechado 31/08 — `requirements-dev.txt` criado; o `.env` passou a ser achado pelo `conftest`, o venv segue por diretório (é o certo) |
| 31/08/2026 | `main()` do servidor MCP foi escrito contra a API antiga do SDK (`Server` + `@list_tools`) e não funcionava com o `mcp` 2.1.1 (`MCPServer` + `@tool`). A suíte estava 99/99 verde com ele quebrado — nenhum teste o alcança. | `usp_mcp/moodle/server.py` | alta | ✅ fechado 31/08 — reescrito e verificado por handshake stdio real; `--auto-verificar` reduz a chance de repetir |
| 31/08/2026 | §1.1 afirmava como fato que a rede da USP não é alcançável do sandbox; verdadeiro para o Cowork em nuvem, falso para o Claude Code na máquina do dono. Foi repetido em decisões sem ser remedido. | `SPEC1.md` §1.1, `CLAUDE.md` item 9 | alta | ✅ fechado 31/08 — ambos reescritos com a medição; decisão no §9 |
| 31/08/2026 | `o_que_vence` não mandava `limitnum` e o default do Moodle é 20: perdia entregas silenciosamente e reportava `truncado=False`. A suíte não pegava porque o duplo de cliente devolve o que o teste manda — nenhuma asserção olhava o parâmetro ENVIADO. | `usp_mcp/moodle/o_que_vence.py` | alta | ✅ fechado 31/08 — manda `limitnum=50` e declara quando bate no teto; T53/T54/T55; decisão no §9 |
| 31/08/2026 | O adaptador stdio `main()` do servidor do Jupiter não tem teste: a suíte cobre as funções puras, e verde nelas não é verde nele. Mesmo buraco que a trilha do Moodle registrou — e lá ele escondeu um `main()` escrito contra a API antiga do SDK. `--auto-verificar` reduz, não elimina. | `usp_mcp/jupiter/server.py` | alta | 🔵 aberto |
| 31/08/2026 | Não há fixture pareada de disciplina + pré-requisito da MESMA disciplina, então T31 cobre só a composição de duas chamadas. O pareamento foi confirmado ao vivo (MAT2454 → MAT2453), mas ao vivo não é regressão. | `fixtures/jupiter/`, `tests/jupiter/test_disciplina.py` | média | 🔵 aberto |
| 31/08/2026 | O significado de `verdis` continua não verificado: a Fase 1 passou `0` e recebeu `verdis:"2"`. O cliente manda `0` porque é o que o JS oficial manda, sem saber se isso é "corrente" ou coincidência. | `usp_mcp/jupiter/cliente.py` | baixa | 🔵 aberto |
| 31/08/2026 | Eu afirmei em três documentos que a rede da USP não era alcançável desta sessão, com a regra 9 do `CLAUDE.md` ("antes de dizer que a rede não dá, MEÇA") em contexto e com este backlog já registrando o mesmo erro como fechado. Custou um `curl` desmentir. Sinal de que aviso escrito não substitui verificação barata executada. | processo | média | ✅ fechado 31/08 — canários rodados, três documentos corrigidos, lição no §9 |
