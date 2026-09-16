"""Moodle (e-Disciplinas). Dado autenticado: só entrypoint local (§6, Invariante 4).

Um módulo por ferramenta (`o_que_vence`, `material`, `arquivo`, `diagnostico`,
`ja_entreguei`, `notas`, `avisos`, `o_que_mudou`, `disciplinas`, `atrasadas`,
`entrega`), sobre `politica` (allowlist e bloqueio permanente), `cliente` (o fio)
e `projecao` (o que sai do payload cru). `server` é a casca stdio. A suíte em
`tests/moodle/` é a especificação executável de cada um.
"""
