"""O que este servidor tem, inclusive o que está DESLIGADO, dito em prosa.

Nasceu de um defeito relatado por uso real (17/09/2026): o dono usou o
assistente, existia uma capacidade de escrita atrás de `USP_MCP_ENTREGA`, e o
assistente **não sabia que ela existe**. Não recusou — nem chegou a considerar.
Simplesmente não ofereceu, e a pessoa ficou sem saber que era possível.

A causa é de desenho, e o desenho estava certo: com a flag desligada as duas
ferramentas de escrita não entram no `tools/list`
(`docs/superpowers/specs/2026-09-15-entrega-com-confirmacao-design.md`, E14).
Ferramenta que aparece e sempre recusa ensina o modelo a insistir — ele a vê,
escolhe, gasta uma chamada, lê a negativa e procura o contorno. Só que o
`tools/list` era o ÚNICO canal pelo qual o servidor contava de si, e por isso
o preço daquela decisão acabou sendo o silêncio total.

**A saída é separar os dois canais, e o protocolo já os separa.** O `tools/list`
é a superfície de AÇÃO: o que está lá é chamável, e um item chamável que sempre
recusa é a armadilha que o desenho de 15/09 evitou. O campo `instructions` do
`initialize` é a superfície de INFORMAÇÃO: o cliente o lê uma vez, na abertura
da conexão, e não há nada ali para chamar. Uma frase em `instructions` não tem
como virar chamada gasta, nem recusa lida, nem contorno procurado — não existe o
laço que ensina a insistir, porque não existe a tentativa.

Por isso o texto daqui pode dizer o que a lista de ferramentas não pode.

**Regra que segura o crescimento deste texto:** `instructions` carrega só o que
o `tools/list` não tem como carregar. O que cada ferramenta faz e quando usá-la
já viaja na descrição dela, para o cliente que pergunta; repetir aqui seria
pagar os mesmos tokens duas vezes em toda conexão. Hoje o que sobra é um assunto
só — o estado da escrita —, e é por isso que o RUCard e o Jupiter não ganharam
`instructions` nenhuma: eles não têm escrita para ligar, e um campo com texto
que não ajuda a agir é a mesma má prática que a saída sem jargão combateu.

**Informação neutra, com o custo declarado, e nunca convite.** O padrão continua
sendo não escrever. O texto diz o que existe, o que custa (entregar não tem
desfazer) e quem liga — a pessoa dona do token, de propósito, no arquivo dela.
Diz também, com todas as letras, que ligar não é passo que o assistente dê por
conta própria. Isso não é um portão: um modelo com shell alcança o `.env` tanto
quanto alcança este arquivo, e o desenho de 15/09 já registra que o portão é
forte contra acidente e fraco contra um modelo decidido. É honestidade sobre
para quem é a decisão, no único lugar onde ela ainda pode ser lida antes de ser
tomada.

**Simétrico de propósito.** Com a flag ligada o texto muda e diz que está
ligada. Um texto que só falasse do estado desligado envelheceria calado no
servidor de quem ligou — e "o assistente sabe o que está ligado" é a mesma
pergunta, lida do outro lado.
"""
from __future__ import annotations

from .politica import NOME_DA_FLAG

# Os nomes das duas ferramentas de escrita. Escritos aqui, e não importados do
# `server`, porque é o `server` que importa este módulo: o caminho contrário
# fecharia um ciclo de import por causa de duas constantes de texto. Quem obriga
# os dois lados a concordarem é a suíte, que compara este par com o que o
# `listar_ferramentas()` anuncia quando a flag está ligada.
NOME_RASCUNHO = "salvar_rascunho"
NOME_ENTREGAR = "entregar"

# O fato nu, na versão que cabe em qualquer lugar: o diagnóstico usa esta, e as
# instruções usam esta MAIS o parágrafo seguinte. Duas versões do mesmo fato,
# uma contida na outra, e não dois textos que se parecem — foi assim que este
# projeto aprendeu que a segunda cópia é a que envelhece calada.
_DESLIGADA = (
    f"Escrita: DESLIGADA. Este servidor só lê o e-Disciplinas agora. Existe uma "
    f"capacidade de escrita neste projeto — salvar o texto do rascunho de uma "
    f"entrega, e enviar uma entrega para correção — e ela está desligada, por "
    f"isso as duas ferramentas dela não estão nesta conexão. Quem liga é a "
    f"pessoa dona do token, pondo {NOME_DA_FLAG}=1 no arquivo .env do servidor e "
    f"subindo o servidor de novo. Enviar uma entrega para correção NÃO tem "
    f"desfazer, nem por aqui nem pela API do Moodle."
)

_DESLIGADA_RESTO = (
    "Conte isso a quem perguntar o que dá para fazer por aqui, ou a quem pedir "
    "para entregar alguma coisa: que a capacidade existe, que está desligada, o "
    "que ela custa, e que ligar é decisão de quem responde pela conta — não sua, "
    "e não deste processo. Ligar por conta própria não é o caminho, e insistir "
    "também não: enquanto a variável não estiver no ambiente do servidor não há "
    "ferramenta nenhuma para chamar, e não há o que tentar. Com a escrita "
    "ligada, cada uma das duas ainda pede duas chamadas — a primeira mostra o "
    "plano do que mudaria e não escreve nada."
)

_LIGADA = (
    f"Escrita: LIGADA, por {NOME_DA_FLAG}=1 no ambiente deste servidor. As "
    f"ferramentas `{NOME_RASCUNHO}` e `{NOME_ENTREGAR}` estão nesta conexão e "
    f"escrevem no e-Disciplinas em nome de quem é dono do token. Cada uma pede "
    f"duas chamadas: a primeira devolve o plano do que mudaria e um código, e só "
    f"a segunda, repetindo o código, escreve. Enviar uma entrega para correção "
    f"NÃO tem desfazer, nem por aqui nem pela API do Moodle."
)

_LIGADA_RESTO = (
    "Diga que a escrita está ligada quando ela for relevante para a conversa: "
    "quem ligou pode ter esquecido, e o custo de descobrir depois de enviar é o "
    "que não tem volta. Quem desliga é a mesma pessoa que ligou, tirando a "
    "variável do .env — não é passo seu."
)

# A primeira coisa que o cliente lê, e a razão de o resto existir. Ela diz o que
# este texto NÃO é, para que ninguém o encha com o que já viaja na descrição de
# cada ferramenta.
_ABERTURA = (
    "Ferramentas de consulta ao e-Disciplinas (Moodle da USP). O que cada uma "
    "faz e quando usá-la está na descrição dela; aqui vai só o que a lista de "
    "ferramentas não tem como dizer."
)


def escrita_ligada() -> bool:
    """A capacidade de escrita está ligada NESTE processo?

    Delega para a política, que é quem lê o ambiente, para que não existam dois
    lugares respondendo a mesma pergunta. Lido a cada chamada pelo mesmo motivo
    de lá: o `.env` é carregado depois do import.
    """
    from .politica import entrega_habilitada

    return entrega_habilitada()


def estado_da_escrita(*, curto: bool = False) -> str:
    """O estado da escrita em prosa, na versão curta ou na inteira.

    `curto=True` devolve exatamente o primeiro parágrafo da versão inteira — não
    um resumo parecido. É o que garante que o diagnóstico e o `initialize` não
    digam coisas diferentes sobre o mesmo servidor.
    """
    base, resto = (_LIGADA, _LIGADA_RESTO) if escrita_ligada() else (
        _DESLIGADA,
        _DESLIGADA_RESTO,
    )
    return base if curto else f"{base}\n\n{resto}"


def instrucoes() -> str:
    """O texto do campo `instructions` do `initialize`.

    Montado a cada subida do processo, e não constante de módulo, porque ele
    depende do ambiente: o servidor que sobe com a flag ligada diz outra coisa.
    """
    return f"{_ABERTURA}\n\n{estado_da_escrita()}"
