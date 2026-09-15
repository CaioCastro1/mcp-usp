"""A ferramenta `bandejao` — a fatia vertical do RUCard.

Responde a pergunta do §5 do SPEC1, com o vocabulário do dono:

    "O que tem no bandejão hoje, e onde vale a pena almoçar?"

São duas perguntas numa. *O que tem* é um RU e um dia; *onde vale a pena* é os
quatro lado a lado, com preço, calorias e horário — o que decide. Uma chamada de
ferramenta responde as duas (critério 2 do §5), e por isso a comparação não é uma
segunda ferramenta.

Quatro coisas que a implementação óbvia erra e que aqui estão certas de propósito:

**O dia se escolhe por data, não por índice.** A lista tem 7 posições e a semana
vira: em 31/08/2026 às 19:22 o índice 0 já era 31/08, não 24/08. Índice funciona
até segunda-feira.

**A semana é a mesma pergunta.** "Que dia tem lasanha?" não é outra ferramenta: é
`bandejao` sete vezes, uma por dia, com o `/menu` vindo do cache — 5 requisições, as
mesmas de um dia. Nome de dia ("sexta") resolve para o dia DESSA semana, porque é a
única que existe no RUCard.

**`FECHADO` não é uma coisa só.** O RU 7 devolve os 7 jantares fechados porque
**nunca** serve jantar; o RU 6 devolve sábado fechado porque não serve nesse dia;
e um feriado seria fechado num dia em que ele serve. As três leem igual no
`/menu` e se separam cruzando com o horário publicado — que é o motivo de o
catálogo ser buscado junto, e não uma otimização à parte.

**A comparação é case-insensitive.** RU 6 escreve `Fechado`, RUs 7/8/9 escrevem
`FECHADO` — estável nas duas semanas capturadas. Uma comparação exata mostraria a
palavra "FECHADO" como item de comida em três dos quatro RUs.

**A opção do dia não é chamada de vegetariana sem a marca.** 100% das refeições
abertas nas duas semanas têm uma linha `Opção: …`; só algumas trazem `(V)`.
Rotular todas de vegetarianas é afirmar o que a fonte não diz.

**Comunicado não é prato.** Em 14/09/2026 o campo de cardápio passou a terminar
com um aviso em negrito ("Tragam suas canecas") em três RUs. Ele sai da lista de
itens e volta como UM aviso na resposta, nomeando os RUs — nunca some, e nunca
aparece como comida (§9, 14/09).
"""
from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta, timezone

from . import catalogo, politica
from .cliente import semana_de
from .erros import ErroRucard, RucardIndisponivel

# Literal -3, e não fuso nomeado: é a mesma escolha da trilha do Moodle
# (`projecao.FUSO_SAO_PAULO`) — o Brasil não tem horário de verão desde 2019, e
# um banco de fusos indisponível não deve mudar em que dia o bandejão está.
FUSO_SAO_PAULO = timezone(timedelta(hours=-3))

CAMPOS_SAIDA = ("data", "dia_semana", "refeicoes", "restaurantes", "avisos")
CAMPOS_RESTAURANTE = ("id", "nome", "campus", "endereco", "refeicoes")
CAMPOS_REFEICAO = (
    "situacao", "detalhe", "itens", "opcao", "opcao_vegetariana_marcada",
    "calorias", "horario", "preco_aluno", "avisos_publicados",
)

# datetime.weekday() é 0=segunda … 6=domingo. Sem strftime("%a"): ele depende do
# locale do processo (inglês por padrão) e não deve variar entre máquinas.
_DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

_CHAVE_REFEICAO_API = {"almoco": "lunch", "jantar": "dinner"}
_REFEICOES_COM_CARDAPIO = ("almoco", "jantar")

_ROTULO_REFEICAO = {"cafe": "café da manhã", "almoco": "almoço", "jantar": "jantar"}

# O vocabulário de quem pergunta, e o id que a allowlist entende. `politica`
# continua decidindo POR ID (§1.2: name/alias é exibição); aqui só se traduz a
# entrada do usuário antes de qualquer política. Sem acento nos nomes canônicos
# porque são valores de enum que trafegam em JSON digitado por modelo — com
# acento também são aceitos.
NOMES_RU_PARA_ID: dict[str, str] = {
    "central": "6", "prefeitura": "7", "fisica": "8", "quimicas": "9",
}
NOMES_RU: tuple[str, ...] = tuple(NOMES_RU_PARA_ID)
ALIASES_RU: dict[str, str] = {
    **NOMES_RU_PARA_ID,
    "pusp": "7", "pusp-cb": "7", "puspcb": "7", "pusp-c": "7",
    "física": "8",
    "químicas": "9", "quimica": "9", "química": "9",
}


def resolver_restaurantes(pedidos) -> list[str]:
    """Nomes e/ou ids → ids, sem repetição, na ordem pedida. Vazio → os quatro.

    Nome desconhecido é erro legível AQUI, antes da política: passar "each" adiante
    como se fosse id devolveria a mensagem de id inexistente, que é a cura errada.
    """
    if not pedidos:
        return list(politica.RUS_PERMITIDOS)
    ids: list[str] = []
    for pedido in pedidos:
        chave = str(pedido).strip().lower()
        if chave.isdigit():
            id_ = chave
        elif chave in ALIASES_RU:
            id_ = ALIASES_RU[chave]
        else:
            raise ErroRucard(
                f"não conheço o restaurante {pedido!r}. Use {', '.join(NOMES_RU)} "
                "— ou omita para comparar os quatro."
            )
        if id_ not in ids:
            ids.append(id_)
    return ids

_MARCA_VEGETARIANA = re.compile(r"\(\s*v\s*\)", re.IGNORECASE)
_PREFIXO_OPCAO = re.compile(r"^op[çc][ãa]o\s*:?\s*", re.IGNORECASE)
_TAG_HTML = re.compile(r"<[^>]+>")

# Comunicado dentro do campo de cardápio — medido em 14/09/2026 no RU 7
# (`fixtures/rucard/menu_7_semana_14-09.json`): a linha inteira vem em negrito
# markdown, separada por linha em branco, nos cinco almoços de dia útil. Duas
# regras reconhecem comunicado, e as duas são declaradas aqui: negrito de ponta
# a ponta, ou frase de 6+ palavras terminada em ponto/exclamação — nome de prato
# não termina em ponto em nenhuma das ~120 refeições de fixture.
_AVISO_NEGRITO = re.compile(r"^\*\*(.+?)\*\*$")
_FIM_DE_FRASE = (".", "!")
_MINIMO_PALAVRAS_DE_FRASE = 6


def _comunicado(linha: str) -> str | None:
    """Texto do comunicado se a linha for aviso e não prato; `None` se for prato.

    Não descarta nada: quem chama põe o texto nos avisos da resposta. A regra é
    a medida, não a imaginada — um comunicado sem negrito e sem ponto final
    passa como prato, e esse é o limite declarado.
    """
    casou = _AVISO_NEGRITO.match(linha)
    if casou:
        return casou.group(1).strip()
    if linha.endswith(_FIM_DE_FRASE) and len(linha.split()) >= _MINIMO_PALAVRAS_DE_FRASE:
        return linha
    return None


# Nome de dia da semana → datetime.weekday(). Com e sem "-feira", com e sem
# acento, e a abreviação de três letras — é assim que a pergunta chega ("na
# sexta", "sábado", "qui"). Resolve para o dia DESSA semana, passado ou futuro,
# porque é a única semana que tem cardápio.
_NOMES_DIA: dict[str, int] = {
    "segunda": 0, "segunda-feira": 0, "seg": 0,
    "terça": 1, "terca": 1, "terça-feira": 1, "terca-feira": 1, "ter": 1,
    "quarta": 2, "quarta-feira": 2, "qua": 2,
    "quinta": 3, "quinta-feira": 3, "qui": 3,
    "sexta": 4, "sexta-feira": 4, "sex": 4,
    "sábado": 5, "sabado": 5, "sáb": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}
# "na sexta", "no sábado", "nesta quinta": o artigo não muda o dia.
_ARTIGO_DE_DIA = re.compile(r"^(na|no|nesta|neste|nessa|nesse|esta|este|essa|esse|a|o)\s+")

# O valor de `dia` que pede os sete dias. Quem o atende é `bandejao_semana`.
SEMANA = "semana"


def segunda_da_semana(dia: date) -> date:
    """A segunda-feira da semana de `dia`. A semana do RUCard vai de seg a dom."""
    return dia - timedelta(days=dia.weekday())


def dias_da_semana(hoje: date) -> list[date]:
    """Os sete dias, segunda a domingo, da semana de `hoje`."""
    segunda = segunda_da_semana(hoje)
    return [segunda + timedelta(days=i) for i in range(7)]


def resolver_dia(bruto: str, hoje: date) -> date:
    """"hoje", "amanhã", "sexta", `DD/MM/AAAA` ou `AAAA-MM-DD` → data.

    Aceita as duas formas de data porque as duas chegam: a brasileira é a que a
    pessoa digita e a que a API publica, e a ISO é a que um modelo tende a
    normalizar sozinho. Nome de dia resolve para o dia DESSA semana, mesmo que já
    tenha passado — "o que teve na segunda" é pergunta válida na quarta, e a
    semana corrente é a única com cardápio. Aceitar só uma forma transforma
    pergunta boa em erro.
    """
    texto = _ARTIGO_DE_DIA.sub("", (bruto or "hoje").strip().lower())
    if texto in ("hoje", "hj"):
        return hoje
    if texto in ("amanhã", "amanha"):
        return hoje + timedelta(days=1)
    if texto in ("depois de amanhã", "depois de amanha"):
        return hoje + timedelta(days=2)
    if texto == "ontem":
        return hoje - timedelta(days=1)
    if texto in _NOMES_DIA:
        return segunda_da_semana(hoje) + timedelta(days=_NOMES_DIA[texto])
    if texto == SEMANA:
        raise ErroRucard(
            "'semana' cobre os sete dias e é atendido por `bandejao_semana`, "
            "não por `bandejao`. Pela ferramenta MCP, dia='semana' já faz isso."
        )
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m"):
        try:
            lido = datetime.strptime(texto, formato).date()
        except ValueError:
            continue
        return lido.replace(year=hoje.year) if formato == "%d/%m" else lido
    raise ErroRucard(
        f"não entendi o dia {bruto!r}. Use 'hoje', 'amanhã', um dia da semana "
        "como 'sexta', 'semana' para os sete dias, ou uma data como 26/08/2026. "
        "O RUCard publica só a semana corrente, então data de outra semana não "
        "tem cardápio — nem no passado, nem no futuro."
    )


def _itens_e_opcao(bruto: str) -> tuple[list[str], str | None, bool, list[str]]:
    """Texto livre do cardápio → itens, opção do dia, se a opção é marcada, e os
    comunicados que vieram misturados.

    O §1.2 registra que o texto às vezes vem com HTML e às vezes com ` - ` no
    lugar do `\\n`. Nenhuma das duas apareceu em três semanas de captura, então
    o tratamento aqui é tolerância, não teste: HTML sai, e ` - ` só é usado como
    separador quando não há quebra de linha nenhuma para usar.

    O que APARECEU, em 14/09/2026, foi comunicado em negrito no fim do cardápio
    ("Tragam suas canecas"). Ele sai da lista de itens e volta como aviso — a
    lista de pratos não pode ter um prato que não existe, e o comunicado não
    pode sumir (Invariante 7).
    """
    limpo = html.unescape(_TAG_HTML.sub(" ", bruto or ""))
    linhas = [l.strip() for l in limpo.splitlines() if l.strip()]
    if len(linhas) == 1 and " - " in linhas[0]:
        linhas = [p.strip() for p in linhas[0].split(" - ") if p.strip()]

    itens: list[str] = []
    avisos: list[str] = []
    opcao: str | None = None
    for linha in linhas:
        comunicado = _comunicado(linha)
        if comunicado is not None:
            if comunicado not in avisos:
                avisos.append(comunicado)
            continue
        if opcao is None and _PREFIXO_OPCAO.match(linha):
            opcao = _PREFIXO_OPCAO.sub("", linha).strip()
            continue
        itens.append(re.sub(r"\s{2,}", " ", linha))

    marcada = bool(opcao and _MARCA_VEGETARIANA.search(opcao))
    return itens, opcao, marcada, avisos


def _esta_fechado(bruto: str) -> bool:
    """`Fechado` e `FECHADO` são a mesma coisa (§1.2: a grafia varia por RU)."""
    return (bruto or "").strip().lower() in ("", "fechado")


def _refeicao_sem_cardapio(ficha, dia: date, qual: str) -> dict:
    """Café da manhã: o serviço é publicado, o cardápio não.

    Invariante 6: a resposta honesta diz as duas coisas. Nem lista vazia (que
    leria como "não tem café"), nem cardápio inventado.
    """
    hora = catalogo.horario(ficha, dia, "cafe")
    if hora is None:
        return {
            "situacao": "nao_serve",
            "detalhe": _detalhe_nao_serve(ficha, dia, "cafe"),
        }
    return {
        "situacao": "sem_cardapio_publicado",
        "horario": hora,
        "detalhe": (
            f"{ficha.nome}: serve café da manhã das {hora}, mas o RUCard não "
            "publica cardápio de café — só almoço e jantar."
        ),
        "preco_aluno": ficha.precos_aluno.get("cafe"),
    }


def _detalhe_nao_serve(ficha, dia: date, qual: str) -> str:
    rotulo = _ROTULO_REFEICAO[qual]
    if not catalogo.serve_em_algum_dia(ficha, qual):
        return (
            f"{ficha.nome} não serve {rotulo} em dia nenhum da semana — não há "
            "horário publicado para essa refeição."
        )
    return (
        f"{ficha.nome} não serve {rotulo} no {_DIAS_SEMANA[dia.weekday()]}; "
        "há horário publicado em outros dias."
    )


def _projetar_refeicao(ficha, dia: date, qual: str, bruto_do_dia: dict) -> dict:
    if qual == "cafe":
        return _refeicao_sem_cardapio(ficha, dia, qual)

    cru = (bruto_do_dia.get(_CHAVE_REFEICAO_API[qual]) or {})
    hora = catalogo.horario(ficha, dia, qual)

    if _esta_fechado(cru.get("menu", "")):
        if hora is None:
            # As duas fontes concordam: não é dia dessa refeição neste RU.
            return {"situacao": "nao_serve", "detalhe": _detalhe_nao_serve(ficha, dia, qual)}
        # Horário publicado e cardápio fechado: feriado, greve, manutenção. É a
        # única situação em que "fechado hoje" é a informação certa.
        return {
            "situacao": "fechado",
            "horario": hora,
            "detalhe": (
                f"{ficha.nome} costuma servir {_ROTULO_REFEICAO[qual]} das "
                f"{hora} neste dia da semana, mas o cardápio de "
                f"{dia.strftime('%d/%m/%Y')} está marcado como fechado."
            ),
        }

    itens, opcao, marcada, avisos_publicados = _itens_e_opcao(cru.get("menu", ""))
    return {
        "situacao": "aberto",
        "itens": itens,
        "opcao": opcao,
        "opcao_vegetariana_marcada": marcada,
        # String como a API manda: '' e '1.065' existiriam e int() explodiria.
        "calorias": cru.get("calories"),
        "horario": hora,
        "preco_aluno": ficha.precos_aluno.get(qual),
        # Comunicado que veio dentro do cardápio (14/09/2026). Fica aqui por
        # refeição para a projeção ser fiel; quem agrega e nomeia os RUs é
        # `bandejao`, que enxerga os quatro.
        "avisos_publicados": avisos_publicados,
    }


def _dia_do_payload(payload: dict, dia: date) -> dict | None:
    alvo = dia.strftime("%d/%m/%Y")
    for bruto in payload.get("meals") or []:
        if bruto.get("date") == alvo:
            return bruto
    return None


def bandejao(dia: str = "hoje", refeicao: str = "todas", restaurantes=None, *,
             cliente, hoje: date | None = None) -> dict:
    """Cardápio de um dia nos RUs pedidos, com o que decide "vale a pena".

    `hoje` é injetável para que o teste não dependa da data em que roda — e para
    que "hoje" signifique hoje em São Paulo, não no fuso do processo.
    """
    hoje = hoje if hoje is not None else datetime.now(FUSO_SAO_PAULO).date()
    data = resolver_dia(dia, hoje)

    if refeicao == "todas":
        refeicoes = list(_REFEICOES_COM_CARDAPIO)
    elif refeicao in _ROTULO_REFEICAO:
        refeicoes = [refeicao]
    else:
        raise ErroRucard(
            f"refeição {refeicao!r} não existe aqui. Use 'almoco', 'jantar', "
            "'cafe' ou 'todas'."
        )

    ids = resolver_restaurantes(restaurantes)

    fichas = catalogo.projetar(cliente.restaurantes())

    avisos: list[str] = []
    saida: list[dict] = []
    semanas_publicadas: set[tuple[str, str]] = set()
    falhas = 0
    sem_horario: list[str] = []
    sem_o_dia: list[tuple[str, str, str]] = []
    # {texto do comunicado: [nomes dos RUs em que apareceu]} — um aviso por texto
    # distinto, e não um por RU por refeição: em 14/09 o mesmo texto veio em
    # três RUs e sairia três vezes.
    publicados: dict[str, list[str]] = {}

    for id_ru in ids:
        ficha = fichas.get(id_ru)
        if ficha is None:
            # A política do cliente é quem nega de verdade; aqui é só não
            # inventar ficha para um id que o catálogo não trouxe.
            raise ErroRucard(politica.decidir("menu", id_ru).motivo)

        if refeicoes == ["cafe"]:
            # Café não tem cardápio: não vale gastar uma chamada de /menu por RU
            # para descobrir isso (Invariante 5).
            saida.append(_ficha_para_saida(ficha, {
                "cafe": _refeicao_sem_cardapio(ficha, data, "cafe")
            }))
            continue

        try:
            payload = cliente.menu(id_ru, data)
        except ErroRucard as exc:
            falhas += 1
            avisos.append(
                f"cardápio do {ficha.nome} (RU {id_ru}) não pôde ser lido: {exc}"
            )
            saida.append(_ficha_para_saida(ficha, {
                q: {"situacao": "indisponivel",
                    "detalhe": f"o RUCard não respondeu por este restaurante."}
                for q in refeicoes
            }))
            continue

        inicio, fim = semana_de(payload)
        if inicio and fim:
            semanas_publicadas.add(
                (inicio.strftime("%d/%m/%Y"), fim.strftime("%d/%m/%Y"))
            )

        bruto_do_dia = _dia_do_payload(payload, data)
        if bruto_do_dia is None:
            # Invariante 7: o RU não entra na lista, e o motivo aparece embaixo
            # NOMEANDO o restaurante e a semana que ele publicou. Sem o nome, um
            # RU a menos entre quatro passa em branco — a forma mais difícil de
            # notar de um limite silencioso, e a que a revisão desta sessão pegou.
            sem_o_dia.append((
                ficha.nome,
                inicio.strftime("%d/%m/%Y") if inicio else "?",
                fim.strftime("%d/%m/%Y") if fim else "?",
            ))
            continue

        refeicoes_projetadas = {
            q: _projetar_refeicao(ficha, data, q, bruto_do_dia) for q in refeicoes
        }
        for q, projetada in refeicoes_projetadas.items():
            if projetada["situacao"] == "aberto" and projetada.get("horario") is None:
                sem_horario.append(f"{ficha.nome} ({_ROTULO_REFEICAO[q]})")
        for projetada in refeicoes_projetadas.values():
            for comunicado in projetada.get("avisos_publicados") or ():
                nomes = publicados.setdefault(comunicado, [])
                if ficha.nome not in nomes:
                    nomes.append(ficha.nome)
        saida.append(_ficha_para_saida(ficha, refeicoes_projetadas))

    if falhas and falhas == len(ids):
        # A distinção do §9 de 28/08: "não tem nada" e "a chamada falhou" não
        # podem ser a mesma saída. Nenhum RU respondeu não é cardápio vazio.
        raise RucardIndisponivel(
            "nenhum dos restaurantes pedidos respondeu — isto é falha de "
            f"leitura, não cardápio vazio. Pedidos: {', '.join(ids)}."
        )

    if sem_o_dia:
        # Agrupado por semana devolvida: com os quatro RUs na mesma semana (o
        # caso comum) isto é UM aviso, não quatro quase idênticos. O nome do RU
        # continua aparecendo, que é o que faltava.
        pedido = data.strftime("%d/%m/%Y")
        por_semana: dict[tuple[str, str], list[str]] = {}
        for nome, inicio, fim in sem_o_dia:
            por_semana.setdefault((inicio, fim), []).append(nome)
        for (inicio, fim), nomes in por_semana.items():
            avisos.append(
                f"sem cardápio de {pedido} em: {', '.join(nomes)}. A semana "
                f"publicada por esses restaurantes vai de {inicio} a {fim}. O "
                "RUCard publica só a semana corrente e não tem parâmetro de data "
                "— cardápio de outra semana não é consultável, nem passado nem "
                "futuro."
            )

    if "cafe" in refeicoes:
        avisos.append(
            "café da manhã: o RUCard publica o horário do serviço, mas não "
            "publica o cardápio — nenhuma ferramenta aqui sabe o que tem no café."
        )

    if sem_horario:
        avisos.append(
            "cardápio publicado sem horário publicado em: "
            f"{', '.join(sem_horario)}. Os dois vêm de rotas diferentes; "
            "considerei o cardápio, que é a evidência mais forte de que serve."
        )

    for comunicado, nomes in publicados.items():
        avisos.append(
            f"aviso publicado no cardápio de {', '.join(nomes)}: {comunicado}"
        )

    return {
        "data": data.strftime("%d/%m/%Y"),
        "dia_semana": _DIAS_SEMANA[data.weekday()],
        "refeicoes": refeicoes,
        "restaurantes": saida,
        "avisos": avisos,
    }


CAMPOS_SEMANA = ("inicio", "fim", "refeicoes", "dias", "avisos")


def bandejao_semana(refeicao: str = "todas", restaurantes=None, *, cliente,
                    hoje: date | None = None) -> dict:
    """Os sete dias da semana corrente, segunda a domingo, numa resposta só.

    É a mesma pergunta do §5 ("o que tem, e onde vale a pena") com outro recorte
    de tempo — "que dia tem lasanha?" — e por isso não é outra ferramenta. Chama
    `bandejao` uma vez por dia; o cliente cacheia o `/menu` por RU, então a semana
    inteira custa as mesmas 5 requisições de um dia (há teste que trava isso).
    Avisos iguais entre dias saem uma vez.
    """
    hoje = hoje if hoje is not None else datetime.now(FUSO_SAO_PAULO).date()
    respostas = [
        bandejao(
            dia=d.strftime("%d/%m/%Y"), refeicao=refeicao, restaurantes=restaurantes,
            cliente=cliente, hoje=hoje,
        )
        for d in dias_da_semana(hoje)
    ]

    avisos: list[str] = []
    for resposta in respostas:
        for aviso in resposta["avisos"]:
            if aviso not in avisos:
                avisos.append(aviso)

    return {
        "inicio": respostas[0]["data"],
        "fim": respostas[-1]["data"],
        "refeicoes": respostas[0]["refeicoes"],
        "dias": [
            {k: r[k] for k in ("data", "dia_semana", "restaurantes")} for r in respostas
        ],
        "avisos": avisos,
    }


def _ficha_para_saida(ficha, refeicoes: dict) -> dict:
    return {
        "id": ficha.id,
        "nome": ficha.nome,
        "campus": ficha.campus,
        "endereco": ficha.endereco,
        "refeicoes": refeicoes,
    }
