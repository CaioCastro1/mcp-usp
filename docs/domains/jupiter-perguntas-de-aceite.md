# Perguntas de aceite — Jupiter

> Para rodar **numa sessão com o `usp-jupiter` conectado**, em linguagem natural,
> como um aluno perguntaria. A suíte prova que o código faz o que o teste diz; esta
> lista prova outra coisa — que o **modelo escolhe a ferramenta certa** e que a
> resposta que chega a uma pessoa está certa.
>
> Cada linha traz o que a resposta precisa conter e, principalmente, **o que ela
> nunca pode dizer**. Essa segunda coluna é a que importa: as três falhas achadas em
> 14/09 eram todas respostas *plausíveis* e erradas, não erros visíveis.

## Como rodar

Pergunte em conversa, sem citar nome de ferramenta. Se o modelo pedir o código do
curso, **já falhou** a P1 — a fatia existe para isso não acontecer.

## O caminho feliz

| # | Pergunta | Tem que aparecer | Não pode aparecer |
|---|---|---|---|
| P1 | "o que eu preciso ter feito antes de PTC3314?" | PTC3213 e PSI3213, currículo 3032, 6º período | pedido de `codcur`; "nenhum pré-requisito" |
| P2 | "posso pegar PSI3323 junto com PSI3322?" | **sim** — correquisito, cursa junto | "PSI3322 é pré-requisito" |
| P3 | "quantos créditos tem PME3344 e qual a ementa?" | **2+0, 30 h** (medido 14/09), ementa | 0 h (é o campo `cgahoreto`, que vale zero) |
| P4 | "dá pra me matricular em MAT2455 devendo Cálculo II?" | **depende do currículo**: fraco em 3032, duro em 3250 | uma resposta única para os dois |

## Os casos que quebram implementação ingênua

| # | Pergunta | Tem que aparecer | Não pode aparecer |
|---|---|---|---|
| P5 | "quais os pré-requisitos de MAT2455?" | 23 currículos, com os de ingresso marcados | lista achatada; só o primeiro currículo |
| P6 | "sou da turma nova de Civil, o que preciso pra MAT2455?" | `2000101` Fundamentos Científicos e Modelagem | "não há requisito cadastrado" (foi meu erro de 14/09) |
| P7 | "o que preciso pra PTC3313?" | que o JupiterWeb **não registra** e que isso ≠ ausência | "não precisa de nada"; lista vazia sem explicação |
| P8 | "preciso de algo pra MAT2453?" | as **duas** causas do silêncio, sem escolher uma | "da ênfase em diante não tem registro" — absurdo para Cálculo I |
| P9 | "o que preciso pra PTC9999?" | erro legível dizendo que a sigla não existe | lista vazia; stack trace do Tomcat |

## O que nenhuma delas pode provocar

| Pergunta | Resposta correta |
|---|---|
| "que horas é a aula de PTC3314?" / "em que sala?" / "tem vaga?" | a ferramenta diz que **não sabe** — horário, sala e vaga ficaram fora da fatia |
| "qual a grade completa da Elétrica?" | ainda não existe; é a fatia `curso`, aberta no backlog |

## Por que estas e não outras

O §5 do `SPEC1.md` pede que ferramenta nasça de pergunta real. P1, P2 e P3 são as do
dono; P4 a P9 saíram da medição de 14/09 (§9) e existem porque **cada uma delas já
produziu uma resposta errada** em algum ponto do dia:

- **P2** era o bug: correquisito anunciado como exigência prévia, na `main` desde 31/08.
- **P4** era invisível: `stamtrrcp` descartado, "fraco" e "duro" iguais na saída.
- **P6** era o meu erro de medição — parser cego a código só de dígitos.
- **P7 e P8 são a mesma saída**, e é assim de propósito: a página devolve zero
  currículo para as duas, e daqui não dá para saber se a disciplina não exige nada
  (Cálculo I) ou se a exigência existe e não está registrada (ênfase). A primeira
  versão ranqueava a segunda causa — e entregava a explicação sobre 7º semestre para
  uma disciplina de 1º. **Foi a P8 que pegou**, depois da suíte inteira verde: é o
  tipo de erro que só aparece quando alguém faz a pergunta como gente.
