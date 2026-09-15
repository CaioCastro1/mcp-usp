"""Anotações de protocolo: o que a MÁQUINA lê onde hoje só havia prosa.

O MCP define um bloco `annotations` por ferramenta — `readOnlyHint`,
`destructiveHint`, `idempotentHint`, `openWorldHint` — e é por ele que o cliente
decide o que pode chamar sozinho e o que precisa parar e perguntar. O Invariante
1 já dizia "read-only por padrão", e dizia **em português**: um cliente MCP não
lê português. Sem estes campos, as ferramentas deste projeto chegariam ao
cliente indistinguíveis de uma que apaga uma entrega — e desde 15/09/2026 duas
delas de fato entregam.

Desde 15/09/2026 há duas ferramentas a mais, e só com `USP_MCP_ENTREGA=1`:
`salvar_rascunho` e `entregar`. Elas são as primeiras do projeto a escrever no
e-Disciplinas, e por isso as primeiras a declarar `destructiveHint` verdadeiro —
a razão de cada campo delas está ao lado do bloco, lá embaixo.

Mora num módulo só, e não copiado nos três servidores, pelo mesmo motivo do
`adaptador.py`: a razão de cada escolha é a mesma para os três, e três cópias de
uma razão são duas que envelhecem caladas.

**Nada aqui importa o SDK no topo.** `listar_ferramentas()` é função pura e roda
sem o pacote `mcp` instalado — a suíte inteira depende disso. Os descritores
carregam dicionário, e a conversão para `ToolAnnotations` acontece dentro de
`para_o_sdk`, que só `main()` chama.

## Por que `idempotentHint` não está nas de leitura

O protocolo diz que `idempotentHint` só tem significado quando `readOnlyHint` é
falso. Declará-lo numa das doze de leitura seria um campo sem referente: custa
bytes no fio, parece informação e não é nenhuma. O projeto já tem uma regra
irmã (J1) contra mandar ao cliente palavra que não ajuda a agir.

Em `baixar_arquivo` ele é o contrário disso — é exatamente o campo que diz que a
escrita dela é enchimento de cache. E lá ele não é opinião: o depósito endereça
por `<fileid>-<timemodified>` e `ja_baixado` confere tamanho, então a segunda
chamada com os mesmos argumentos não rebaixa nem cria segundo arquivo.

## Por que `openWorldHint` é verdadeiro em todas

Este era o campo com mais chance de virar promessa vazia, e a medição resolve:
todas, sem exceção, fazem requisição HTTP para um sistema que não é deste
repositório — e-Disciplinas, JupiterWeb, RUCard. O domínio **não** é fechado.
Quais disciplinas existem, que arquivo o professor publicou hoje e o que o RU
serve amanhã não estão enumerados em lugar nenhum daqui e mudam sem aviso; a
allowlist limita QUAIS funções chamamos, nunca que entidades existem do outro
lado.

O default do protocolo para este campo já é verdadeiro, então declarar não muda
o comportamento de cliente nenhum. Declarar mesmo assim resolve a ambiguidade
que a ausência cria: campo ausente lê-se tanto como "verdadeiro por omissão"
quanto como "ninguém olhou". Aqui olhou-se, e o dia em que um quarto servidor
responder de cache local é o dia em que este campo tem de mudar — e ele existir
é o que faz alguém lembrar.
"""
from __future__ import annotations

# As doze de leitura: o_que_vence, material, diagnostico, ja_entreguei, notas,
# avisos, o_que_mudou, disciplinas, atrasadas (Moodle), disciplina e requisitos
# (Jupiter), bandejao (RUCard).
SO_LEITURA = {
    # Nenhuma delas chama função de escrita. No Moodle a allowlist é inteira de
    # leitura, e continua sendo depois de 15/09: as duas funções de escrita que
    # existem hoje NÃO entraram nela — moram num conjunto próprio, governado por
    # flag e por confirmação, e só as duas ferramentas de entrega as alcançam.
    # No Jupiter e no RUCard a API só responde consulta.
    "readOnlyHint": True,
    # Redundante pela letra do protocolo — `destructiveHint` só tem significado
    # quando `readOnlyHint` é falso — e escrito assim mesmo por uma razão: o
    # DEFAULT do campo é verdadeiro. Um cliente que leia `destructiveHint`
    # sozinho, sem aplicar a regra condicional, trataria todas como destrutivas.
    # Um booleano explícito custa menos que essa leitura.
    "destructiveHint": False,
    # `idempotentHint` fica FORA de propósito. Ver a docstring do módulo.
    "openWorldHint": True,
}

# `baixar_arquivo`, a única de leitura que toca o disco de quem roda o servidor.
ESCREVE_NO_DEPOSITO = {
    # FALSO, e a decisão é essa depois de ler a ferramenta. Ela grava bytes em
    # `~/.cache/usp-mcp/moodle/<courseid>/<fileid>-<timemodified>/<nome>` —
    # `deposito.gravar` faz `mkdir` e `write_bytes`. O campo do protocolo não
    # pergunta "escreve no Moodle?", pergunta "modifica o seu ambiente?", e o
    # disco de quem chama é ambiente. Dizer verdadeiro aqui seria usar o campo
    # para descrever o Moodle e deixar o cliente descobrir o arquivo sozinho —
    # exatamente a promessa em prosa que estas anotações vieram substituir.
    #
    # A leitura tentadora e errada seria: "ela não muda nada lá, logo é de
    # leitura". Ela cabe na política read-only do projeto (não escreve no
    # e-Disciplinas, não entrega trabalho, não muda nota) e mesmo assim não é
    # read-only no sentido do protocolo. As duas coisas convivem: os outros três
    # campos abaixo é que dizem o quanto essa escrita é inofensiva.
    "readOnlyHint": False,
    # Só CRIA, e em caminho endereçado pelo conteúdo. Nunca sobrescreve arquivo
    # de terceiro, nunca apaga, nunca sai do depósito (`caminho_para` reprova o
    # caminho que escapar da raiz). Nada que o dono tenha posto ali é tocado.
    "destructiveHint": False,
    # Medido, não prometido: `ja_baixado` devolve verdadeiro para arquivo já
    # presente com o tamanho certo, e `_baixar_um` reusa em vez de rebaixar.
    # Arquivo alterado no Moodle ganha `timemodified` novo, e portanto diretório
    # novo — a segunda chamada com os mesmos argumentos não tem efeito adicional.
    "idempotentHint": True,
    "openWorldHint": True,
}


# --------------------------------------------------------------------------
# As duas que ESCREVEM NO MOODLE, e só existem com `USP_MCP_ENTREGA=1`
# (15/09/2026). São o primeiro caso do projeto em que `destructiveHint` é
# verdadeiro, e a decisão é essa depois de ler o campo pelo que ele pergunta.
#
# **Por que verdadeiro, e por que isso é a resposta útil.** O protocolo define
# `destructiveHint` como "pode fazer atualização destrutiva no ambiente", em
# oposição a "só faz acréscimo". Nenhuma das duas acrescenta: `salvar_rascunho`
# SUBSTITUI o texto que estava lá, e `entregar` muda um estado que a API não
# sabe voltar. E o campo tem um uso concreto do outro lado — é por ele que um
# cliente decide o que chama sozinho e o que para e pergunta. Declarar falso
# aqui seria pedir ao cliente que tratasse uma entrega irreversível como uma
# consulta, que é exatamente o teatro que este desenho recusa: um portão que
# promete mais do que cumpre é pior do que nenhum.
#
# A leitura tentadora e errada seria a simétrica da de `baixar_arquivo`: "o
# desenho tem confirmação em duas etapas, logo o risco já está tratado, logo
# não é destrutiva". A confirmação trata o ACIDENTE; ela não torna a escrita
# reversível, e é a reversibilidade que este campo descreve.
#
# `tests/test_anotacoes.py` (A3) proibia QUALQUER ferramenta de se declarar
# destrutiva. A regra mudou junto com esta decisão, e mudou para mais estreita,
# não para mais frouxa: agora só estas duas podem, elas são nomeadas lá, e
# qualquer outra que apareça destrutiva continua reprovando.

ESCREVE_RASCUNHO = {
    # Escreve no e-Disciplinas: o rascunho da entrega passa a ter outro texto.
    "readOnlyHint": False,
    # VERDADEIRO. O rascunho anterior é substituído, e a API não devolve o que
    # estava lá. "Dá para salvar de novo" não é desfazer — é escrever outra
    # coisa por cima, com o conteúdo velho já perdido.
    "destructiveHint": True,
    # VERDADEIRO, e medido contra o próprio desenho: a segunda chamada com os
    # mesmos argumentos não chega a escrever. O código de confirmação carrega o
    # `timemodified`, que a primeira escrita muda, então a repetição é recusada
    # antes do transporte com o plano novo na mão. Mesmo que chegasse, o
    # rascunho ficaria com exatamente o mesmo conteúdo — o texto é substituído,
    # nunca acrescentado.
    "idempotentHint": True,
    "openWorldHint": True,
}

ENTREGA_SEM_DESFAZER = {
    "readOnlyHint": False,
    # VERDADEIRO, e este é o campo mais importante do arquivo inteiro. Não há
    # função no e-Disciplinas que desfaça uma entrega enviada para correção.
    "destructiveHint": True,
    # FALSO, ao contrário da irmã acima. A segunda chamada não é "o mesmo de
    # novo": a primeira deixou a entrega em `submitted`, e é isso que a torna
    # uma ação de uma vez só. O que a repetição encontra é uma recusa — do
    # código de confirmação, que mudou, e depois do próprio site.
    "idempotentHint": False,
    "openWorldHint": True,
}


def para_o_sdk(descritor: dict):
    """As anotações deste descritor como o `ToolAnnotations` do SDK, ou `None`.

    Recebe o descritor inteiro, e não o dicionário de anotações, para que o
    ponto de registro em `main()` seja uma linha por ferramenta e não duas.

    Descritor sem anotação devolve `None` — que é o que o SDK já faz com uma
    ferramenta registrada sem o argumento. NÃO levanta de propósito: matar o
    servidor na subida por causa de um campo de metadado faltando seria trocar
    uma degradação pequena (o cliente fica sem a dica) por um servidor que não
    sobe, e é justamente a forma de falha que `main()` já pagou uma vez. Quem
    guarda essa porta é `tests/test_anotacoes.py`, que reprova antes do commit.
    """
    anotacoes = descritor.get("annotations")
    if not anotacoes:
        return None

    from mcp.types import ToolAnnotations

    return ToolAnnotations(**anotacoes)
