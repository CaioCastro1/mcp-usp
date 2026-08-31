# Domínios — mapa das partes do sistema

> Um domínio = uma área do sistema com responsabilidade própria e "o que quebra
> junto" conhecido. Cada domínio ganha um arquivo `docs/domains/<dominio>.md`
> quando o comportamento dele para de caber num parágrafo aqui.
>
> Desde 31/08/2026 cada domínio tem código em `usp_mcp/<sistema>/` (uma fatia
> vertical: política, cliente, ferramenta, servidor). O conhecimento continua
> vivendo no `SPEC1.md` (fato/invariante), em `notas/` (medição) e no §9
> (decisão). Estas linhas são ponteiro, não duplicata — não copie fato do
> `SPEC1.md` para cá.

| Domínio | Onde está o conhecimento | O que é |
|---|---|---|
| RUCard (bandejão) | `SPEC1.md` §1.2, `notas/fase1-rucard.md`, `usp_mcp/rucard/` | Cardápio dos RUs. Dado **público**, sem credencial pessoal. POST form-urlencoded, hash compartilhada. Só semana corrente, sem parâmetro de data. Fatia: `bandejao` nos 4 RUs da Cidade Universitária. |
| e-Disciplinas (Moodle) | `SPEC1.md` §1.3 e §2.2, `notas/fase1-moodle.md`, `notas/moodle-catalogo.md`, `usp_mcp/moodle/` | Prazos, material, notas, avisos. Dado **pessoal e autenticado** — Invariante 4 prende no entrypoint local. 447 funções expostas; a superfície é allowlist. |
| JupiterWeb | `notas/jupiter-recon.md`, `SPEC1.md` §9 (31/08/2026), `usp_mcp/jupiter/` | Catálogo de disciplinas, créditos, pré-requisitos, grade curricular. Dado público. Superfície estruturada existe (DWR), e não onde se esperava. |

## O que quebra junto

- Os três são APIs **não documentadas**, descobertas por observação: podem mudar
  ou sumir sem aviso. Toda regra de parsing aqui é hipótese com prazo de validade.
- RUCard e Jupiter são públicos e cacheáveis ⇒ podem viver em servidor hospedado.
  Moodle não ⇒ entrypoint local. Essa fronteira é o §6 do `SPEC1.md`, e é
  consequência dos Invariantes 3 e 4, não de gosto. Mover um domínio de lado
  quebra um invariante.

## Convenção de cada `docs/domains/<dominio>.md`

- **O que é**: 2-3 linhas.
- **Regras que não são óbvias pelo código** (a razão de existirem, não só o quê).
- **O que quebra junto**: outros domínios/arquivos afetados por uma mudança aqui.
- **Gate específico**, se houver.
