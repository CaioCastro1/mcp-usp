"""Anotações de protocolo: o que a MÁQUINA lê onde hoje só havia prosa.

O MCP define um bloco `annotations` por ferramenta — `readOnlyHint`,
`destructiveHint`, `idempotentHint`, `openWorldHint` — e é por ele que o cliente
decide o que pode chamar sozinho e o que precisa parar e perguntar. O Invariante
1 já dizia "read-only por padrão", e dizia **em português**: um cliente MCP não
lê português. Sem estes campos, as treze ferramentas deste projeto chegam ao
cliente indistinguíveis de uma que apaga uma entrega.

Mora num módulo só, e não copiado nos três servidores, pelo mesmo motivo do
`adaptador.py`: a razão de cada escolha é a mesma para os três, e três cópias de
uma razão são duas que envelhecem caladas.

**Nada aqui importa o SDK no topo.** `listar_ferramentas()` é função pura e roda
sem o pacote `mcp` instalado — a suíte inteira depende disso. Os descritores
carregam dicionário, e a conversão para `ToolAnnotations` acontece dentro de
`para_o_sdk`, que só `main()` chama.

## Por que `idempotentHint` não está nas doze de leitura

O protocolo diz que `idempotentHint` só tem significado quando `readOnlyHint` é
falso. Declará-lo numa ferramenta de leitura seria um campo sem referente: custa
bytes no fio, parece informação e não é nenhuma. O projeto já tem uma regra
irmã (J1) contra mandar ao cliente palavra que não ajuda a agir.

Em `baixar_arquivo` ele é o contrário disso — é exatamente o campo que diz que a
escrita dela é enchimento de cache. E lá ele não é opinião: o depósito endereça
por `<fileid>-<timemodified>` e `ja_baixado` confere tamanho, então a segunda
chamada com os mesmos argumentos não rebaixa nem cria segundo arquivo.

## Por que `openWorldHint` é verdadeiro nas treze

Este era o campo com mais chance de virar promessa vazia, e a medição resolve:
as treze, sem exceção, fazem requisição HTTP para um sistema que não é deste
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
    # Nenhuma delas chama função de escrita. No Moodle a allowlist tem cinco
    # funções, todas de leitura, e a lista de bloqueio permanente não é aberta
    # por flag nenhuma; no Jupiter e no RUCard a API só responde consulta.
    "readOnlyHint": True,
    # Redundante pela letra do protocolo — `destructiveHint` só tem significado
    # quando `readOnlyHint` é falso — e escrito assim mesmo por uma razão: o
    # DEFAULT do campo é verdadeiro. Um cliente que leia `destructiveHint`
    # sozinho, sem aplicar a regra condicional, trata as treze como destrutivas.
    # Um booleano explícito custa menos que essa leitura.
    "destructiveHint": False,
    # `idempotentHint` fica FORA de propósito. Ver a docstring do módulo.
    "openWorldHint": True,
}

# `baixar_arquivo`, a única das treze que toca o disco de quem roda o servidor.
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
