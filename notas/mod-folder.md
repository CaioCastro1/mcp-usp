# `mod_folder`: a pergunta aberta desde 31/08, fechada com medição

> 15/09/2026. Medido no checkout principal, contra a conta real, com o token do
> dono. Duas chamadas, escolhidas à mão, uma função por invocação.

## A pergunta

O backlog registra desde 31/08/2026 que **não se sabia** se
`core_course_get_contents` expande o conteúdo de um `mod_folder`. Três
disciplinas amostradas naquele dia não tinham pasta nenhuma, e três amostras sem
pasta não provam ausência: provam que a amostra foi pequena.

A dúvida importava porque uma disciplina que agrupe as listas numa Pasta é
justamente o caso que `material` precisa acertar, e onde ele poderia estar
errando calado.

## Como achei uma disciplina com pasta

`mod_folder_get_folders_by_courses` aceita vários `courseids` de uma vez. Uma
chamada com as doze matrículas de 2026 devolveu 5.372 B, sem aviso, e **dez
pastas**, todas no curso 138864 (`PEA3301_2026_1sem`). As outras onze
disciplinas do semestre não têm pasta nenhuma, o que explica a amostra vazia de
31/08: pasta é recurso de minoria, e cair fora dela por acaso é fácil.

Chaves de uma pasta nessa resposta: `course`, `coursemodule`, `display`,
`forcedownload`, `groupingid`, `groupmode`, `id`, `intro`, `introfiles`,
`introformat`, `lang`, `name`, `revision`, `section`, `showdownloadfolder`,
`showexpanded`, `timemodified`, `visible`. Note o que **não** está aí: a lista
de arquivos. Esta função descreve a pasta, não o conteúdo dela.

## A resposta

`core_course_get_contents` no curso 138864 devolveu 124.868 B, 10 seções e 79
módulos. Os dez `folder` chegam **com `contents` preenchido**, nenhum vazio:

| | módulos | arquivos dentro |
|---|---|---|
| `folder` | 10 | 48 |
| `resource` | 40 | 41 |

**Sim, expande.** E o número que muda a leitura da questão: nesta disciplina
**54% dos arquivos moram dentro de pasta**, não soltos. Se a expansão não
acontecesse, `material` estaria escondendo mais da metade do material e
parecendo completo.

As dez pastas custam 32.807 B dos 127.163 B da resposta, ou 26%.

## `material` de fato mostra esses arquivos

Expandir na API não basta; era preciso conferir que a ferramenta não filtra a
pasta no caminho. `material` itera o `contents` de **todo** módulo, e não só dos
`resource`, então os arquivos de dentro da pasta entram como qualquer outro.

Conferido ao vivo: `material` na disciplina 138864 devolve 101 itens, e três
arquivos que só existem dentro de pasta (`Manual completo HP 50g.pdf`,
`emulador-HP50g.zip`, `Números complexos, matrizes e variáveis (HP 50g).pdf`)
aparecem todos.

## Conclusão

**Nada a consertar, e uma função a menos para escrever.** O item do roadmap
propunha avaliar `mod_folder_get_folders_by_courses` e `core_files_get_files`
como candidatas à lista de permitidas. Nenhuma das duas precisa entrar: a
primeira descreve pastas sem listar arquivo, o que é menos do que já temos, e a
segunda resolveria um problema que não existe.

A pergunta fechou pelo lado bom, que é o mais barato: o comportamento já estava
certo, e agora está **medido** em vez de suposto.

## O que esta medição não alcança

Uma disciplina, dez pastas, um semestre. O que foi provado é que a expansão
acontece e que `material` a preserva; não foi provado que ela acontece em toda
instalação nem com pasta aninhada, que esta amostra não tem. Se um dia aparecer
pasta dentro de pasta, isto aqui não diz nada sobre ela.
