# Os PDFs presos dentro das entregas — design

> 12/09/2026. Fecha o achado do conector: `material` lista 53 itens de PTC3314 e
> **nenhum** deles é o enunciado do EC-1, que existe e é um PDF.

## O que foi medido, antes de qualquer desenho

Sonda única e à mão (Regra de Ouro §3.1), contra PTC3314 (`courseid` 142036):

| chamada | resultado |
|---|---|
| `core_course_get_contents` | 106.121 B. 4 módulos `assign`, **os 4 com `contents` vazio** |
| `description` do assign | 529 B no EC-1 — datas de abertura e vencimento, **zero `href`, zero `pluginfile`** |
| `mod_assign_get_assignments` (`courseids[0]=142036`) | 8.651 B / ~2.162 tokens |

O que a terceira linha traz e as duas primeiras não:

```
EC-1 - Transitórios em LT   → EP1-2026.odt (150.693 B), EP1-2026.pdf (218.344 B)
EC - 2 - Linhas em RPS      → EP2-2026.odt ( 94.931 B), EP2-2026.pdf (215.809 B)
Prova Presencial - 1 e 2    → sem anexo
```

Mais **dois `warnings`** que hoje ninguém veria: `{"item":"module","itemid":6372370,
"warningcode":"1","message":"No access rights in module context"}` — duas atividades
do curso que o token não consegue ler.

**O achado que decide o desenho:** cada anexo chega com `filename`, `filesize`,
`mimetype`, `timemodified` e `fileurl` — **os mesmos nomes de campo** que
`projetar_material` já lê de `contents`. A `fileurl` é
`…/webservice/pluginfile.php/9599969/mod_assign/introattachment/0/EP1-2026.pdf`,
ou seja passa pela allowlist de download do cliente e pelo `_fileid` existente
sem exceção nenhuma (9599969 é o `contextid` do módulo).

Logo: o anexo vira um `Item` igual aos outros, e `baixar_arquivo` — que já opera
sobre `projetar_material` — passa a achá-lo **sem uma linha de mudança**.

## O que muda

1. **`politica.ALLOWLIST` cresce de 4 para 5**, com `mod_assign_get_assignments`.
   É leitura, e o prefixo `mod_assign_get_` entra junto no P5 de
   `tests/moodle/test_politica.py`. `mod_assign_save_*`, `submit_*`, `start_*` e
   `remove_*` seguem no bloqueio permanente do §2.2 — o prefixo não os alcança.
2. **`projetar_material` registra os módulos `assign`** (cmid, seção, nome) num
   campo novo de `Conteudo`. É esse registro que diz se a segunda chamada vale:
   **disciplina sem `assign` não paga nada.**
3. **Uma função nova converte os anexos em `Item`**, na seção do próprio módulo,
   com o nome do assign como `modulo` — é ele que diz "EC-1", e é o que
   `rotulo_do_modulo` já imprime.
4. **Os `warnings` saem no bloco ⚠** (Invariantes 6 e 7): "N atividades não
   puderam ser lidas com esta credencial". Engolir isso seria a lista vazia que
   parece completa.
5. **O aviso "não estão nesta lista: assign, forum, quiz" é corrigido** — deixa
   de ser verdade para `assign` com anexo.

## O que NÃO muda (decisão do dono, 12/09)

O `intro` do assign — o enunciado em texto, 498 B no EC-1 — **fica de fora**.
`material` é lista de arquivos; enunciado, prazo, "já entreguei" e nota são
outra pergunta, e o §5 pede que ferramenta nasça de pergunta registrada, não do
que a resposta da API por acaso contém. Vai para o `BACKLOG-correcoes.md` como
candidata própria.

## Custo, e por que ele é aceitável

+8.651 B sobre os 106.121 B de `get_contents` na mesma disciplina: **8%**, e só
onde há `assign`. O Invariante 5 não é tocado — é chamada sob demanda, uma por
pergunta, nunca varredura. O que ela evita é pior: hoje o dono lê a lista de 53
itens, não acha o enunciado, e conclui que ele não existe.

## Testes

Camada de contrato, com dublê (offline, entra no gate):

- a projeção registra os `assign` do `get_contents`, com seção e cmid;
- anexo vira `Item` com nome, tipo, tamanho e o assign como módulo;
- `material` **manda `courseids[0]`** — asserção sobre o parâmetro ENVIADO, não
  sobre a saída (item 11 do `CLAUDE.md`: o dublê devolve o que o teste mandou);
- disciplina sem `assign` **não chama** `mod_assign_get_assignments`;
- `warning` da resposta aparece no texto;
- `baixar_arquivo` acha e baixa um anexo de entrega pelo nome;
- a allowlist segue negando `mod_assign_submit_for_grading`.

Camada live (atrás de `USP_MCP_LIVE=1`): `EP1-2026.pdf` aparece em `material` de
PTC3314 e baixa.
