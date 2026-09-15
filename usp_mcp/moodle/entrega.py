"""Salvar rascunho e entregar para correção, com confirmação humana explícita.

Este é o único módulo do projeto que ESCREVE no e-Disciplinas, e o desenho
inteiro está em `docs/superpowers/specs/2026-09-15-entrega-com-confirmacao-design.md`.
O resumo que importa para quem lê o código:

**O que este desenho protege contra: acidente e ambiguidade.** "Salva aí pra
mim" e "entrega isso" são uma palavra de distância, e a segunda não tem volta.

**O que ele NÃO protege contra:** um modelo que decidiu entregar e tem shell.
Dentro de um cliente com ferramenta de terminal, arquivo de confirmação,
variável de ambiente e marca com prazo são todos alcançáveis — não existe portão
do lado do servidor que um modelo com shell não possa abrir. Dizer isso aqui não
é derrotismo: um portão que promete mais do que cumpre é pior do que nenhum,
porque faz quem liga a flag baixar a guarda.

As cinco camadas, e o que cada uma de fato entrega:

1. **Verbos separados.** `salvar_rascunho` e `entregar` são funções e
   ferramentas distintas. Nada de `acao: "salvar" | "entregar"` — um enum põe as
   duas a uma letra de distância na cabeça de quem gera a chamada.
2. **Plano e execução em duas invocações.** A primeira chamada NUNCA escreve:
   devolve o plano e um código. A segunda só escreve se o código ainda casar
   com o estado do site. Esta é a camada que resolve o problema real — estado
   velho virando escrita errada — e é a única que funciona sem depender de
   ninguém do outro lado.
3. **Elicitação como apresentação.** `Context.elicit` é onde um cliente com
   humano na frente mostra a pergunta. O próprio protocolo diz que um cliente
   agente pode responder sozinho, então ela é a forma certa de PERGUNTAR e a
   coisa errada de ser a garantia. Cliente sem suporte não bloqueia o fluxo, e a
   saída diz qual dos dois aconteceu: "não pude perguntar" e "perguntei e
   disseram não" são coisas diferentes.
4. **A flag.** `USP_MCP_ENTREGA`, desligada por padrão, checada na política.
5. **Recusas que a flag não abre.** Entrega de grupo, entrega travada, envio já
   feito, envio não permitido pelo site e plano sem arquivo nenhum. Mais uma que
   o spec não previu, achada ao implementar: entrega CRONOMETRADA cujo relógio
   ainda não foi ligado — ver `_recusa_por_cronometro`, que explica por que a
   cura não é liberar mais uma função.

**O código não é prova de humano, e o módulo trata ele assim.** Tudo que o
servidor diz ao modelo, o modelo pode repetir na chamada seguinte sem que
ninguém tenha lido. O que o código prova é outra coisa, e é verificável: que o
plano não mudou entre a leitura e a escrita. Se alguém anexou outro arquivo, se
o prazo foi prorrogado, se a entrega já estava entregue, o código muda e a
segunda chamada é recusada com o plano novo.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from datetime import datetime

from .disciplinas import carregar, resolver
from .erros import ErroMoodle
from .projecao import FUSO_SAO_PAULO
from .texto import casa, formatar_data, sem_html

# Quantos caracteres do resumo do plano viajam como código de confirmação. Seis
# hexadecimais são 16,7 milhões de valores: o que está em jogo aqui não é um
# atacante adivinhando o código (quem tem a ferramenta tem o código inteiro na
# resposta anterior), é a colisão entre dois planos diferentes da MESMA entrega
# — e para isso seis sobram. Curto importa: é um valor que uma pessoa relê na
# tela antes de repetir.
TAMANHO_DO_CODIGO = 6

# Os nomes de função que este módulo chama para escrever. Escritos aqui, ao lado
# de quem os usa, e não espalhados no meio do fluxo.
_SALVAR = "mod_assign_save_submission"
_ENTREGAR = "mod_assign_submit_for_grading"

_LEITURA_ATIVIDADES = "mod_assign_get_assignments"
_LEITURA_STATUS = "mod_assign_get_submission_status"

# O resultado de uma pergunta feita ao cliente. Três valores, e os três
# aparecem na saída com palavras diferentes.
ACEITOU = "aceitou"
RECUSOU = "recusou"
NAO_PERGUNTOU = "nao_perguntou"


class ElicitacaoIndisponivel(Exception):
    """O cliente não sabe perguntar. NÃO é uma recusa, e não bloqueia o fluxo.

    Erro próprio, e não `None` de retorno, porque quem levanta isto é o
    adaptador do protocolo lá na borda: um retorno especial se perderia no
    caminho, e "não pude perguntar" tratado como "disseram não" cancelaria toda
    entrega feita de um cliente sem elicitação.
    """


@dataclass(frozen=True)
class Arquivo:
    nome: str
    tamanho: int


@dataclass(frozen=True)
class Atividade:
    """Um `assign` como `mod_assign_get_assignments` o descreve, nos campos que
    o plano precisa.

    `declaracao` é o texto que o professor exige que o aluno assine ao entregar
    (`submissionstatement`), e ele está aqui porque escrever sem mostrá-lo seria
    assinar em nome de alguém sem mostrar o que se assina. A entrega real de
    PTC3314 exige uma, capturada em 12/09.
    """

    assignid: int
    nome: str
    prazo: datetime | None
    aceita_envio: bool
    em_grupo: bool
    exige_declaracao: bool
    declaracao: str


@dataclass(frozen=True)
class Plano:
    """O que mudaria, montado SEM escrever nada.

    É a projeção inteira de `mod_assign_get_submission_status` para esta
    pergunta: tudo que não está aqui foi descartado de propósito.
    """

    sigla: str
    atividade: Atividade
    status: str
    timemodified: int
    arquivos: tuple[Arquivo, ...]
    em_grupo: bool
    travada: bool
    pode_enviar: bool
    pode_editar: bool
    prorrogacao: datetime | None
    tipos_de_envio: tuple[str, ...]
    # `tempo_limite` em segundos, 0 quando a entrega não é cronometrada, e
    # `comecou` diz se o cronômetro já foi ligado. Os dois existem por causa de
    # uma lacuna achada depois do spec — ver `_recusa_por_cronometro`.
    tempo_limite: int
    comecou: bool


@dataclass(frozen=True)
class RespostaEntrega:
    """`escreveu` é o campo que os testes olham, e ele existe para não precisar
    procurar a palavra certa dentro do texto."""

    texto: str
    escreveu: bool
    codigo: str | None = None
    recusa: str | None = None


def _data(carimbo) -> datetime | None:
    """Epoch positivo vira data; 0, None e não-inteiro viram "sem data".

    Mesma regra de `ja_entreguei._data`, e pelo mesmo motivo: o site devolve 0 e
    `null` no mesmo campo, e epoch 0 viraria 01/01/1970.
    """
    if isinstance(carimbo, bool) or not isinstance(carimbo, int) or carimbo <= 0:
        return None
    return datetime.fromtimestamp(carimbo, FUSO_SAO_PAULO)


def projetar_atividades(bruto) -> tuple[Atividade, ...]:
    """`mod_assign_get_assignments` → as atividades, na ordem do prazo.

    Lê sete campos das quarenta que cada `assign` traz. `intro` e
    `introattachments` são as gordas, e as duas já são resposta de `material`.
    """
    atividades = [
        Atividade(
            assignid=a.get("id"),
            nome=a.get("name") or "",
            prazo=_data(a.get("duedate")),
            aceita_envio=not a.get("nosubmissions"),
            em_grupo=bool(a.get("teamsubmission")),
            exige_declaracao=bool(a.get("requiresubmissionstatement")),
            declaracao=sem_html(a.get("submissionstatement") or ""),
        )
        for curso in (bruto or {}).get("courses") or ()
        for a in curso.get("assignments") or ()
    ]
    fim_da_fila = datetime.max.replace(tzinfo=FUSO_SAO_PAULO)
    return tuple(sorted(atividades, key=lambda a: a.prazo or fim_da_fila))


def montar_plano(bruto, atividade: Atividade, sigla: str) -> Plano:
    """`mod_assign_get_submission_status` → o `Plano`. Leitura pura.

    `teamsubmission` no retorno do site **não é um booleano**: quando a entrega
    é de grupo ele vem como o objeto da submissão do grupo, e quando não é vem
    `null`. Ler a verdade dele é o certo; comparar com `True` seria deixar
    passar exatamente o caso que a camada 5 existe para recusar.
    """
    ultima = (bruto or {}).get("lastattempt") or {}
    submissao = ultima.get("submission") or {}

    arquivos = tuple(
        Arquivo(
            nome=arquivo.get("filename") or "",
            tamanho=arquivo.get("filesize") or 0,
        )
        for plugin in submissao.get("plugins") or ()
        for area in plugin.get("fileareas") or ()
        for arquivo in area.get("files") or ()
        if arquivo.get("filename")
    )

    return Plano(
        sigla=sigla,
        atividade=atividade,
        status=submissao.get("status") or "",
        timemodified=submissao.get("timemodified") or 0,
        arquivos=arquivos,
        # A atividade pode declarar grupo mesmo antes de existir submissão de
        # grupo — as duas fontes valem, e basta uma para recusar.
        em_grupo=bool(ultima.get("teamsubmission")) or atividade.em_grupo,
        travada=bool(ultima.get("locked")),
        pode_enviar=bool(ultima.get("cansubmit")),
        pode_editar=bool(ultima.get("canedit")),
        prorrogacao=_data(ultima.get("extensionduedate")),
        tipos_de_envio=tuple(
            plugin.get("type") or ""
            for plugin in submissao.get("plugins") or ()
            if plugin.get("type")
        ),
        tempo_limite=ultima.get("timelimit") or 0,
        comecou=bool(submissao.get("timestarted")),
    )


def codigo_do_plano(plano: Plano) -> str:
    """O código de confirmação: o começo de um resumo do que mudaria.

    Entram quatro coisas, e são as quatro que mudam o significado de entregar:
    a atividade, o estado atual, o conjunto de arquivos COM tamanho, e o
    carimbo da última alteração. Arquivo trocado por outro de mesmo nome e
    tamanho diferente muda o código; arquivo novo muda o código; entrega que
    virou `submitted` entre a leitura e a escrita muda o código.

    O que ele NÃO é: prova de que um humano leu. Tudo que este servidor diz ao
    modelo, o modelo pode repetir. O que ele prova é que o plano não mudou — e
    isso é verificável de verdade.
    """
    material = json.dumps(
        [
            plano.atividade.assignid,
            plano.status,
            sorted([a.nome, a.tamanho] for a in plano.arquivos),
            plano.timemodified,
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:TAMANHO_DO_CODIGO]


# --------------------------------------------------------------------- texto


_ESTADO_LEGIVEL = {
    "": "nunca aberta",
    "new": "aberta, nada dentro",
    "draft": "rascunho salvo, ainda NÃO enviado",
    "submitted": "já entregue para correção",
    "reopened": "reaberta, nada enviado na nova tentativa",
}


def _tamanho(bytes_: int) -> str:
    if bytes_ >= 1024 * 1024:
        return f"{bytes_ / (1024 * 1024):.1f} MB"
    if bytes_ >= 1024:
        return f"{bytes_ // 1024} kB"
    return f"{bytes_} B"


def _quanto_falta(limite: datetime, agora: datetime) -> str:
    dias = (limite - agora).days
    if dias < 0:
        return "PRAZO VENCIDO"
    if dias == 0:
        return "vence hoje"
    return f"faltam {dias} dia(s)"


def texto_do_plano(
    plano: Plano, *, verbo: str, agora: datetime, com_pedido: bool = True
) -> str:
    """O plano como quem decide o lê. Uma linha por coisa que ele precisa saber.

    O prazo entra com a conta de dias já feita: "18/09 23:59" e "faltam 3 dias"
    não são a mesma informação para quem está decidindo entregar às onze da
    noite, e fazer a subtração de cabeça é onde o erro acontece.

    `com_pedido=False` corta as duas últimas linhas — o pedido de confirmação e
    a frase "nada foi escrito". Elas são verdade antes da escrita e MENTIRA
    depois dela, e o mesmo bloco é reaproveitado nos dois lugares: a resposta de
    sucesso repete o plano para dizer o que foi feito, e repetir "nada foi
    escrito" logo abaixo de "Feito" é a pior frase que este módulo poderia
    produzir.
    """
    linhas = [f"Plano de {verbo} — {plano.sigla}, {plano.atividade.nome}"]
    estado = _ESTADO_LEGIVEL.get(plano.status, plano.status)
    detalhes = [
        "editável" if plano.pode_editar else "não editável",
        "travada" if plano.travada else "não travada",
    ]
    linhas.append(f"  estado agora: {estado}, {', '.join(detalhes)}")

    limite = plano.prorrogacao or plano.atividade.prazo
    if limite is None:
        linhas.append("  prazo: sem prazo declarado")
    else:
        prorrogado = " (prazo prorrogado para você)" if plano.prorrogacao else ""
        linhas.append(
            f"  prazo: {formatar_data(limite)} "
            f"({_quanto_falta(limite, agora)}){prorrogado}"
        )

    if plano.arquivos:
        anexados = ", ".join(
            f"{a.nome} ({_tamanho(a.tamanho)})" for a in plano.arquivos
        )
    else:
        anexados = "NENHUM"
    linhas.append(f"  arquivos anexados: {anexados}")

    if verbo == "entrega":
        linhas.append(
            '  o que muda: o que está lá passa a "entregue para correção"'
        )
        linhas.append("  isto NÃO tem como ser desfeito por este servidor")
    else:
        linhas.append("  o que muda: o texto do rascunho passa a ser o que você mandou")
        linhas.append(
            "  o rascunho anterior é substituído, e o conteúdo velho não volta"
        )

    if plano.atividade.exige_declaracao and plano.atividade.declaracao:
        linhas.append("  ao confirmar, você assina esta declaração do professor:")
        linhas.append(f"    {plano.atividade.declaracao}")

    if com_pedido:
        linhas.append("")
        linhas.append(
            f'Para confirmar, chame de novo com confirmacao="'
            f'{codigo_do_plano(plano)}". Nada foi escrito no e-Disciplinas por '
            "esta chamada."
        )
    return "\n".join(linhas)


# ------------------------------------------------------------------- recusas


def _recusa_de_entrega(plano: Plano) -> str | None:
    """A camada 5 para `entregar`: cinco recusas, cinco motivos distintos.

    A ordem é a da gravidade, e ela importa para a mensagem: uma entrega já
    enviada tem `cansubmit` falso por consequência, e responder "o site não
    aceita envio seu" ali mandaria procurar um problema que não existe.
    """
    if plano.em_grupo:
        return (
            "Esta entrega é de GRUPO: enviá-la escreve em nome de outras pessoas, "
            "que não estão nesta conversa e não concordaram com nada. Este "
            "servidor não faz isso. Entregue pelo site."
        )
    if plano.travada:
        return (
            "Esta entrega está TRAVADA no e-Disciplinas: o professor fechou o "
            "envio. Não há o que este servidor possa fazer — fale com ele."
        )
    if plano.status == "submitted":
        return (
            "Esta entrega JÁ ESTÁ ENTREGUE para correção. Não há o que entregar, "
            "e reenviar não é uma coisa que exista aqui."
        )
    if not plano.pode_enviar:
        return (
            "O e-Disciplinas diz que você NÃO pode enviar esta entrega agora. O "
            "motivo está no site — prazo final passado, pré-requisito, ou "
            "matrícula. Este servidor não contorna isso."
        )
    if not plano.arquivos:
        return (
            "Não há NENHUM arquivo anexado a esta entrega. Entregar vazio é o "
            "acidente mais caro e mais silencioso que existe aqui: some o "
            "arquivo primeiro, pelo site, e pergunte de novo."
        )
    return None


def _recusa_por_cronometro(plano: Plano) -> str | None:
    """A recusa que o spec não previu, e a razão dela estar aqui e não lá.

    O spec de 15/09 tirou DUAS funções do bloqueio permanente e ficou calado
    sobre as outras duas de `mod_assign` que estavam lá. As duas caladas
    continuam bloqueadas, sem condição — na dúvida o padrão do projeto é negar —
    e uma delas cria um caminho infeliz que precisa de nome:
    `mod_assign_start_submission`.

    **O que ela é, medido contra o catálogo deste repositório e não contra
    suposição:** a descrição do core é literal — *"Start a submission for user if
    assignment has a time limit"*. Ela **não** é pré-requisito de
    `save_submission` no caso comum; ela liga o CRONÔMETRO de uma entrega
    cronometrada, e por isso o catálogo a chama de análogo exato de
    `mod_quiz_start_attempt`. Gravar rascunho numa entrega normal funciona sem
    ela, e é por isso que o spec segue válido.

    **O caso que sobra**, e que sem esta recusa chegaria como erro cru do site:
    entrega com `timelimit` maior que zero cujo cronômetro ainda não foi ligado.
    Ali gravar exigiria ligar o relógio, e ligar o relógio é a ação irreversível
    que continua bloqueada. Os dois campos que respondem isso sem chamar nada
    estão na captura de 15/09: `lastattempt.timelimit` e
    `lastattempt.submission.timestarted`.
    """
    if plano.tempo_limite > 0 and not plano.comecou:
        minutos = plano.tempo_limite // 60
        return (
            f"Esta entrega é CRONOMETRADA ({minutos} minuto(s)) e o relógio dela "
            "ainda não foi ligado. Gravar qualquer coisa aqui ligaria o relógio, "
            "e uma vez ligado ele não para nem volta. Este servidor não liga "
            "cronômetro de entrega em nome de ninguém: abra a entrega pelo site, "
            "quando estiver pronto para usar o tempo."
        )
    return None


def _recusa_de_rascunho(plano: Plano) -> str | None:
    """A camada 5 para `salvar_rascunho`, que é mais curta e não é a mesma.

    Não tem a recusa de "já entregue" (entrega enviada chega aqui com
    `canedit` falso, e é essa a mensagem certa) nem a de arquivo nenhum — este
    verbo grava TEXTO, e texto vazio não é acidente caro, é um rascunho vazio.
    """
    if (cronometro := _recusa_por_cronometro(plano)) is not None:
        return cronometro
    if plano.em_grupo:
        return (
            "Esta entrega é de GRUPO: o rascunho é do grupo inteiro, e salvá-lo "
            "sobrescreve o que outras pessoas escreveram. Este servidor não faz "
            "isso. Use o site."
        )
    if plano.travada:
        return (
            "Esta entrega está TRAVADA no e-Disciplinas: o professor fechou o "
            "envio, e nem o rascunho aceita mudança."
        )
    if not plano.pode_editar:
        return (
            "O e-Disciplinas diz que esta entrega NÃO é editável agora — o caso "
            "mais comum é ela já ter sido enviada para correção."
        )
    if plano.tipos_de_envio and "onlinetext" not in plano.tipos_de_envio:
        return (
            "Esta entrega é por ARQUIVO, e este servidor só sabe gravar texto "
            "online. Enviar arquivo exige subir o arquivo ao e-Disciplinas, que "
            "é coisa que nenhuma ferramenta daqui faz. Use o site."
        )
    return None


# -------------------------------------------------------------------- o fluxo


def _localizar(cliente, disciplina: str, entrega: str):
    """Sigla e nome de entrega viram `(sigla, rotulo, Atividade, bruto_status)`.

    Sigla que não resolve e nome que não casa levantam erro legível **antes**
    de qualquer consulta de status: perguntar ao e-Disciplinas para descobrir
    que a pergunta estava errada é gastar chamada da conta do dono à toa.
    """
    resolucao = resolver(carregar(cliente), disciplina)
    if resolucao.disciplina is None:
        raise ErroMoodle(resolucao.motivo)
    alvo = resolucao.disciplina

    bruto = cliente.chamar(
        _LEITURA_ATIVIDADES, **{"courseids[0]": alvo.courseid}
    )
    todas = projetar_atividades(bruto)
    if not todas:
        raise ErroMoodle(
            f"{alvo.sigla} não tem nenhuma tarefa de entrega no e-Disciplinas."
        )

    filtro = (entrega or "").strip()
    candidatas = [a for a in todas if casa(filtro, a.nome)]
    if not candidatas:
        raise ErroMoodle(
            f"Nenhuma entrega com {entrega!r} no nome em {alvo.sigla}. As "
            f"entregas da disciplina são: {', '.join(a.nome for a in todas)}."
        )
    if len(candidatas) > 1:
        # Escolher por você é o erro caro aqui: o verbo seguinte não tem volta.
        raise ErroMoodle(
            f"{entrega!r} casa com mais de uma entrega em {alvo.sigla}: "
            f"{', '.join(a.nome for a in candidatas)}. Diga qual — escrever na "
            "errada não tem desfazer."
        )

    atividade = candidatas[0]
    if not atividade.aceita_envio:
        raise ErroMoodle(
            f"{atividade.nome} não aceita envio pelo e-Disciplinas — é uma "
            "atividade que existe só para ter data."
        )

    bruto_status = cliente.chamar(_LEITURA_STATUS, assignid=atividade.assignid)
    return alvo.sigla, atividade, bruto_status


async def _perguntar_ao_cliente(perguntar, mensagem: str) -> str:
    """Faz a pergunta e classifica a resposta em um dos três valores.

    `perguntar` pode ser síncrona ou assíncrona: quem a fornece na produção é o
    adaptador do protocolo, e lá ela é uma corrotina; nos testes ela é uma
    função comum. Aceitar as duas evita um dublê assíncrono que não prova nada
    além de si mesmo.
    """
    if perguntar is None:
        return NAO_PERGUNTOU
    try:
        resultado = perguntar(mensagem)
        if inspect.isawaitable(resultado):
            resultado = await resultado
    except ElicitacaoIndisponivel:
        return NAO_PERGUNTOU
    return ACEITOU if resultado else RECUSOU


_AVISO_NAO_PERGUNTOU = (
    "Não foi possível perguntar: este cliente não sabe abrir uma pergunta de "
    "confirmação. Isto NÃO é o mesmo que alguém ter confirmado — o que "
    "autorizou a escrita foi o código do plano, e ele diz que o plano não "
    "mudou, nunca que uma pessoa leu."
)

_AVISO_RECUSOU = (
    "A pergunta foi feita e a resposta foi NÃO. Nada foi escrito no "
    "e-Disciplinas."
)


async def _executar(
    cliente,
    disciplina: str,
    entrega: str,
    *,
    verbo: str,
    acao: str,
    confirmacao: str | None,
    perguntar,
    agora: datetime | None,
    escrever,
    recusar,
) -> RespostaEntrega:
    """O fluxo das cinco camadas, um só para os dois verbos.

    Dois fluxos separados seriam duas cópias da camada 2, e a segunda é a que
    alguém esquece de atualizar no dia em que o formato do código mudar.
    """
    agora = agora if agora is not None else datetime.now(FUSO_SAO_PAULO)
    sigla, atividade, bruto_status = _localizar(cliente, disciplina, entrega)
    plano = montar_plano(bruto_status, atividade, sigla)

    if (motivo := recusar(plano)) is not None:
        return RespostaEntrega(
            texto=f"Não dá para {acao} — {plano.sigla}, "
            f"{atividade.nome}\n\n{motivo}",
            escreveu=False,
            recusa=motivo,
        )

    codigo = codigo_do_plano(plano)
    plano_escrito = texto_do_plano(plano, verbo=verbo, agora=agora)

    if not confirmacao:
        # A primeira chamada NUNCA escreve. Este retorno é a camada 2 inteira.
        return RespostaEntrega(texto=plano_escrito, escreveu=False, codigo=codigo)

    if confirmacao.strip().lower() != codigo:
        return RespostaEntrega(
            texto=(
                f"Confirmação não confere: você mandou {confirmacao!r} e o plano "
                f"de agora pede {codigo!r}. Alguma coisa mudou no e-Disciplinas "
                "entre a leitura e esta chamada, ou o código veio de outra "
                "entrega. Nada foi escrito. Este é o plano de AGORA:\n\n"
                f"{plano_escrito}"
            ),
            escreveu=False,
            codigo=codigo,
            recusa="codigo_velho",
        )

    # A pergunta mostra o plano SEM o pedido de confirmação: quem está lendo
    # esta caixa é justamente quem vai responder agora, e mandá-lo "chamar de
    # novo" ali é instrução para a pessoa errada.
    resposta_da_pergunta = await _perguntar_ao_cliente(
        perguntar, texto_do_plano(plano, verbo=verbo, agora=agora, com_pedido=False)
    )
    if resposta_da_pergunta == RECUSOU:
        return RespostaEntrega(
            texto=f"Cancelado, sem {acao}.\n\n{_AVISO_RECUSOU}",
            escreveu=False,
            codigo=codigo,
            recusa="recusada_na_pergunta",
        )

    escrever(cliente, plano)

    # O plano SEM o pedido de confirmação: depois da escrita ele vira o recibo
    # do que foi feito, e as duas linhas do pedido passariam a mentir.
    linhas = [
        f"Feito — {plano.sigla}, {atividade.nome}. Foi isto que foi escrito:",
        "",
        texto_do_plano(plano, verbo=verbo, agora=agora, com_pedido=False),
    ]
    if resposta_da_pergunta == NAO_PERGUNTOU:
        linhas.append("")
        linhas.append(f"⚠ {_AVISO_NAO_PERGUNTOU}")
    return RespostaEntrega(
        texto="\n".join(linhas), escreveu=True, codigo=codigo
    )


def _escrever_entrega(cliente, plano: Plano) -> None:
    """A escrita irreversível, numa função de três linhas e com nome próprio.

    `acceptsubmissionstatement` vai como 1 porque o plano mostrou a declaração
    do professor antes de pedir a confirmação: mandar 0 faria o site recusar, e
    mandar 1 sem ter mostrado seria assinar em nome de alguém às escuras.
    """
    cliente.escrever(
        _ENTREGAR,
        assignid=plano.atividade.assignid,
        acceptsubmissionstatement=1 if plano.atividade.exige_declaracao else 0,
    )


async def entregar(
    cliente,
    disciplina: str,
    entrega: str,
    *,
    confirmacao: str | None = None,
    perguntar=None,
    agora: datetime | None = None,
) -> RespostaEntrega:
    """Entrega uma atividade para correção. NÃO tem desfazer.

    Duas invocações: a primeira devolve o plano e o código, sem tocar em
    escrita nenhuma; a segunda, com o código, escreve.
    """
    return await _executar(
        cliente,
        disciplina,
        entrega,
        verbo="entrega",
        acao="entregar",
        confirmacao=confirmacao,
        perguntar=perguntar,
        agora=agora,
        escrever=_escrever_entrega,
        recusar=_recusa_de_entrega,
    )


async def salvar_rascunho(
    cliente,
    disciplina: str,
    entrega: str,
    texto: str,
    *,
    confirmacao: str | None = None,
    perguntar=None,
    agora: datetime | None = None,
) -> RespostaEntrega:
    """Salva o texto do rascunho de uma entrega. NÃO envia para correção.

    Só TEXTO online. Entrega por arquivo é recusada com esse motivo escrito:
    subir arquivo ao e-Disciplinas é coisa que nenhuma ferramenta deste projeto
    faz, e fingir que salva o rascunho de uma entrega por arquivo produziria um
    rascunho vazio com cara de rascunho salvo.
    """

    def _escrever_rascunho(cliente_, plano: Plano) -> None:
        cliente_.escrever(
            _SALVAR,
            assignid=plano.atividade.assignid,
            **{
                "plugindata[onlinetext_editor][text]": texto,
                "plugindata[onlinetext_editor][format]": 1,
                "plugindata[onlinetext_editor][itemid]": 0,
            },
        )

    return await _executar(
        cliente,
        disciplina,
        entrega,
        verbo="rascunho",
        acao="salvar o rascunho",
        confirmacao=confirmacao,
        perguntar=perguntar,
        agora=agora,
        escrever=_escrever_rascunho,
        recusar=_recusa_de_rascunho,
    )
