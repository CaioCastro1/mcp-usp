"""Fronteira MCP do Moodle. Entrypoint local stdio (§6 do SPEC1).

Este pacote não tem servidor na raiz de propósito: o servidor público
(RUCard/Jupiter) é outro processo, sem credencial pessoal. Este módulo é o
entrypoint LOCAL — dado autenticado do dono nunca sai desta máquina
(Invariante 4). É por isso que ele fala stdio, não HTTP hospedado.

A suíte (`tests/moodle/test_server_mcp.py`) tem só 3 testes de propósito: o
valor real está na projeção (`projecao.py`) e na política (`politica.py`),
que não têm nada a ver com protocolo MCP. Esta camada expõe duas funções
puras — `listar_ferramentas` e `chamar_ferramenta` — que qualquer adaptador
de protocolo pode chamar sem precisar do SDK instalado; `main()` é a casca
stdio por cima, e só ela importa o SDK (import de topo quebraria a suíte,
que roda sem o SDK presente).
"""
from __future__ import annotations

import os

from ..env import carregar_env
from .arquivo import baixar_arquivo
from .avisos import avisos
from .cliente import ClienteMoodle
from .diagnostico import diagnostico
from .erros import ErroMoodle
from .ja_entreguei import ja_entreguei
from .material import material
from .notas import notas
from .o_que_mudou import o_que_mudou
from .o_que_vence import o_que_vence

# URL default: mesma do §8 do SPEC1 e de scripts/ws.sh. MOODLE_URL sobrescreve
# para quem precisa apontar para outro ambiente (não há esse caso hoje, mas
# não custa não fixar o valor).
_URL_PADRAO = "https://edisciplinas.usp.br"

# Oito ferramentas (§5: crescer é decisão de §9 — a segunda entrou em 31/08, a
# terceira em 01/09, e da quarta à oitava em 14/09). Os nomes vêm das perguntas
# do dono, não das funções do Moodle por trás.
_NOME_FERRAMENTA = "o_que_vence"
_NOME_MATERIAL = "material"
_NOME_ARQUIVO = "baixar_arquivo"
_NOME_DIAGNOSTICO = "diagnostico"
_NOME_JA_ENTREGUEI = "ja_entreguei"
_NOME_NOTAS = "notas"
_NOME_AVISOS = "avisos"
_NOME_MUDOU = "o_que_mudou"


def listar_ferramentas() -> list[dict]:
    """Descreve a ferramenta como o MODELO a vê: nome, descrição, parâmetros.

    A descrição usa o vocabulário de quem pergunta ("entrega", "prazo",
    "vence"), não o nome da função do Moodle por trás (T43) — é isso que faz
    o modelo escolher a ferramenta certa diante de uma pergunta em português.
    """
    return [
        {
            "name": _NOME_FERRAMENTA,
            "description": (
                "Lista o que tem prazo de entrega em breve nas disciplinas do "
                "e-Disciplinas (Moodle da USP): tarefas e questionários que "
                "vencem dentro de uma janela de dias a partir de agora. Use "
                "para responder perguntas como 'o que eu tenho para entregar', "
                "'o que vence essa semana' ou 'tem alguma tarefa vencendo'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dias": {
                        "type": "integer",
                        "description": (
                            "Tamanho da janela, em dias, a partir de agora. "
                            "Padrão 14."
                        ),
                        "default": 14,
                    },
                    "limite": {
                        "type": "integer",
                        "description": (
                            "Número máximo de vencimentos no texto de saída. "
                            "Sem padrão: se omitido, todos os vencimentos "
                            "encontrados na janela entram na resposta."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_MATERIAL,
            "description": (
                "Lista os arquivos publicados no espaço de uma disciplina no "
                "e-Disciplinas (Moodle da USP): PDFs de regras e programação da "
                "matéria, listas de exercícios, roteiros, apostilas, provas de "
                "semestres anteriores, **os arquivos de enunciado anexados às "
                "entregas e exercícios computacionais**, além dos links externos "
                "que o professor postou. Use para 'que arquivos tem em PSI3323', "
                "'cadê as regras da disciplina', 'tem prova antiga em PTC3314', "
                "'onde está a lista de exercícios', 'me dá o enunciado do EC-1'. "
                "NÃO devolve o link de download do arquivo "
                "interno — um endereço sem a credencial não abre, e um com ela "
                "exporia o token — mas diz o nome, o tipo e o tamanho de cada "
                "um. Para baixar de fato um destes arquivos, use `baixar_arquivo`."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PSI3323 ou PTC3314. Espaço e caixa não "
                            "importam. Casa também com pedaço do nome."
                        ),
                    },
                    "busca": {
                        "type": "string",
                        "description": (
                            "Filtra por pedaço do nome do arquivo — 'prova', "
                            "'lista', 'regras'. Opcional: sem ele vem tudo, e "
                            "a saída diz quantos itens ficaram de fora quando "
                            "o filtro é usado."
                        ),
                    },
                },
                "required": ["disciplina"],
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_ARQUIVO,
            "description": (
                "Baixa um arquivo publicado no espaço da disciplina no "
                "e-Disciplinas (Moodle da USP) e devolve o CAMINHO dele no disco "
                "desta máquina, para que você mesmo o abra com a sua ferramenta "
                "de leitura de arquivos. Use para 'me dá a lista 2 de PSI3323', "
                "'abre a apostila de amp op', 'pega a prova anterior', 'baixa o "
                "enunciado do EC-1'. Para saber "
                "que arquivos existem antes de escolher, use `material`."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PSI3323. Espaço e caixa não importam. Casa "
                            "também com pedaço do nome."
                        ),
                    },
                    "nome": {
                        "type": "string",
                        "description": (
                            "Pedaço do nome do arquivo, como aparece em "
                            "`material` — 'lista 2', 'apostila', 'regras'. "
                            "Acento e caixa não importam. Se casar com mais de "
                            "um, a resposta lista os candidatos em vez de "
                            "escolher por você."
                        ),
                    },
                    "todos": {
                        "type": "boolean",
                        "description": (
                            "Baixa TODOS os arquivos que casarem, em vez de "
                            "recusar a ambiguidade. Padrão falso. Há teto por "
                            "chamada, e o que ficar de fora é nomeado na saída."
                        ),
                    },
                },
                "required": ["disciplina", "nome"],
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_DIAGNOSTICO,
            "description": (
                "Diz se este servidor funciona no Moodle configurado, e o que "
                "ele alcança por lá: nome do site, versão do Moodle, quantas "
                "funções o seu token atinge e qual das ferramentas daqui está "
                "disponível. Use quando alguma ferramenta falhar sem motivo "
                "claro, ao configurar o servidor pela primeira vez, ou para "
                "responder 'isso funciona no Moodle da minha faculdade?'. "
                "Custa UMA chamada ao Moodle e não lê disciplina nem entrega "
                "nenhuma. Exige token já configurado: para checar um site ANTES "
                "de ter token, o caminho é `scripts/compatibilidade.sh`, que não "
                "usa credencial."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_JA_ENTREGUEI,
            "description": (
                "Diz o que já foi entregue e o que ainda não foi nas tarefas de "
                "uma disciplina do e-Disciplinas (Moodle da USP), e distingue "
                "RASCUNHO SALVO de ENTREGA ENVIADA — que na tela do Moodle "
                "parecem a mesma coisa. Use para 'já entreguei o EP1?', 'o que "
                "falta entregar em PTC3314', 'minha entrega foi mesmo enviada', "
                "'entreguei dentro do prazo?'. Diz também a data do envio, o "
                "nome do arquivo enviado, se já foi corrigida e se houve "
                "prorrogação de prazo para você. Cobre só TAREFA: questionário "
                "e prova presencial não passam por aqui — para o que TEM prazo, "
                "inclusive questionário, use `o_que_vence`. Não traz a nota. "
                "Custa uma chamada ao Moodle por entrega consultada, então "
                "pergunte por uma disciplina de cada vez."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PTC3314. Espaço e caixa não importam. Casa "
                            "também com pedaço do nome."
                        ),
                    },
                    "entrega": {
                        "type": "string",
                        "description": (
                            "Pedaço do nome da entrega — 'EP1', 'EC-2', "
                            "'relatório'. Opcional: sem ele vêm todas as "
                            "entregas da disciplina, e a saída diz se alguma "
                            "ficou de fora por teto de consultas."
                        ),
                    },
                },
                "required": ["disciplina"],
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_NOTAS,
            "description": (
                "Mostra as suas notas no e-Disciplinas (Moodle da USP). Sem "
                "disciplina, dá a nota final de cada uma. Com disciplina, abre "
                "item a item: cada prova, lista e exercício com a nota, de "
                "quanto ela é e quanto vale no total. Use para 'como estou de "
                "nota', 'quanto tirei no EP1', 'minhas notas em PTC3314', 'qual "
                "minha média'. Diz quando o professor lançou e ocultou a nota, "
                "em vez de fingir que não existe. Não traz o comentário escrito "
                "do professor, e não sabe de nota que ficou no papel e nunca "
                "foi lançada no sistema. Custa UMA chamada ao Moodle."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PTC3314. Espaço e caixa não importam. "
                            "Opcional: sem ela vem a nota final de todas as "
                            "disciplinas, que é a visão mais barata."
                        ),
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_AVISOS,
            "description": (
                "Mostra o que o professor e a turma escreveram nos fóruns de "
                "uma disciplina do e-Disciplinas (Moodle da USP): o mural de "
                "avisos primeiro, com o assunto, a data e o começo do texto de "
                "cada tópico. Use para 'o professor avisou alguma coisa?', 'tem "
                "recado novo em PTC3314', 'mudou alguma coisa sobre a prova', "
                "'o que foi dito no fórum'. É aqui que aparece o que o "
                "calendário não sabe — prova presencial adiada, sala trocada, "
                "lista que vai sair —, porque isso não vira prazo de atividade. "
                "Não diz QUEM escreveu: o fórum traz nome de outras pessoas e "
                "eles não saem daqui. Tópico longo sai cortado, e a resposta "
                "avisa quando cortou. Custa uma chamada ao Moodle para listar "
                "os fóruns e mais uma por fórum lido."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PTC3314. Espaço e caixa não importam. Casa "
                            "também com pedaço do nome."
                        ),
                    },
                },
                "required": ["disciplina"],
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_MUDOU,
            "description": (
                "Diz o que mexeu numa disciplina do e-Disciplinas (Moodle da "
                "USP) nos últimos dias: arquivo novo ou trocado, tópico novo no "
                "fórum, atividade com configuração ou prazo alterado, nota "
                "lançada. Use para 'mudou alguma coisa em PTC3314?', 'tem "
                "novidade desde ontem', 'o professor postou algo novo essa "
                "semana', 'vale a pena eu abrir a página da disciplina'. É uma "
                "chamada barata, feita para ser o PRIMEIRO passo: ela diz QUE "
                "mudou e nunca O QUE mudou — para ver o arquivo use `material`, "
                "para ler o que foi escrito no fórum use `avisos`, e para o que "
                "tem prazo use `o_que_vence`. A janela é em dias e a resposta "
                "repete desde quando ela olhou."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PTC3314. Espaço e caixa não importam. Casa "
                            "também com pedaço do nome."
                        ),
                    },
                    "dias": {
                        "type": "integer",
                        "description": (
                            "Tamanho da janela, em dias para trás a partir de "
                            "agora. Padrão 7. Precisa ser pelo menos 1: com "
                            "zero a resposta seria 'nada mudou' por construção."
                        ),
                        "default": 7,
                    },
                },
                "required": ["disciplina"],
                "additionalProperties": False,
            },
        },
    ]


def chamar_ferramenta(nome: str, argumentos: dict, *, cliente=None) -> str:
    """Despacha para a ferramenta pedida pelo nome, ou levanta erro legível.

    Nome desconhecido é a fronteira do Invariante 6 (T44): não devolve lista
    vazia nem `None` silencioso — levanta `ErroMoodle` citando o nome pedido,
    porque "ferramenta não existe" e "ferramenta existe mas não achou nada"
    têm curas diferentes para quem lê o erro.
    """
    conhecidas = tuple(f["name"] for f in listar_ferramentas())
    if nome not in conhecidas:
        raise ErroMoodle(
            f"Ferramenta desconhecida: {nome!r}. As ferramentas expostas por "
            f"este servidor são {', '.join(repr(n) for n in conhecidas)}."
        )

    if cliente is None:
        # O `.env` é a única casa do token (§8, gitignorado) — decisão de
        # 31/08/2026. `carregar_env` usa `setdefault`, então o bloco `env` de um
        # cliente MCP, se existir, ganha do arquivo. Chamado aqui e não no import
        # do módulo para que importar `server` continue sendo livre de efeito
        # colateral (é o que os testes de contrato fazem).
        carregar_env()

        # Credencial só é lida aqui, na hora de montar o cliente — nunca logada
        # nem exposta (Invariante 3).
        cliente = ClienteMoodle(
            token=os.environ.get("MOODLE_TOKEN", ""),
            url=os.environ.get("MOODLE_URL", _URL_PADRAO),
        )

    if nome == _NOME_DIAGNOSTICO:
        return diagnostico(cliente)

    if nome == _NOME_NOTAS:
        return notas(cliente, disciplina=argumentos.get("disciplina")).texto

    if nome == _NOME_AVISOS:
        return avisos(cliente, argumentos["disciplina"]).texto

    if nome == _NOME_MUDOU:
        return o_que_mudou(
            cliente,
            argumentos["disciplina"],
            dias=argumentos.get("dias", 7),
        ).texto

    if nome == _NOME_JA_ENTREGUEI:
        return ja_entreguei(
            cliente,
            argumentos["disciplina"],
            entrega=argumentos.get("entrega"),
        ).texto

    if nome == _NOME_MATERIAL:
        return material(
            cliente,
            argumentos["disciplina"],
            busca=argumentos.get("busca"),
        ).texto

    if nome == _NOME_ARQUIVO:
        return baixar_arquivo(
            cliente,
            argumentos["disciplina"],
            argumentos["nome"],
            todos=bool(argumentos.get("todos")),
            raiz=argumentos.get("raiz"),
        ).texto

    return o_que_vence(
        cliente,
        dias=argumentos.get("dias", 14),
        limite=argumentos.get("limite"),
    ).texto


def main() -> None:  # pragma: no cover — casca stdio; ver nota abaixo.
    """Adaptador stdio real. Import do SDK fica AQUI dentro, não no topo do
    módulo: os testes de contrato importam `usp_mcp.moodle.server` sem o SDK
    do MCP instalado, e um import de topo quebraria a coleta inteira da
    suíte por causa de uma dependência que as funções puras nem chegam a usar.

    **Tem teste, por dois caminhos que não se substituem.** T78-T81
    (`tests/moodle/test_server_stdio.py`) rodam isto em processo, substituindo só
    `run()`, e alcançam o que o processo esconde: o dicionário montado para
    `chamar_ferramenta` e a mensagem de SDK ausente. `tests/handshake/` sobe o
    processo de verdade e compara o que sai NO FIO com o declarado — foi lá que
    apareceu o schema mais pobre que o `inputSchema`. Antes de 31/08/2026 esta
    docstring dizia "sem teste automático de propósito", com a justificativa de
    que exercitá-lo testaria o SDK; as duas metades estavam erradas, e foi este
    buraco que escondeu um `main()` falando a API antiga com a suíte 99/99 verde.

    **E por um terceiro desde 10/09/2026.** E1-E4
    (`tests/moodle/test_erro_no_fio.py`) olham a MENSAGEM DE ERRO no fio, que
    nenhum dos dois alcançava — os dois exercitam o caminho feliz e o handshake,
    e a fronteira ficou muda por uma versão inteira do SDK sem ninguém ver.
    """
    try:
        from mcp.server import MCPServer
        # `ToolError` existe no 2.0.0 e no 2.2.0, e entra no MESMO try: sem o
        # SDK, quem responde é a mensagem legível abaixo, não um traceback.
        from mcp.server.mcpserver.exceptions import ToolError
    except ImportError as exc:
        raise SystemExit(
            "O SDK do MCP (pacote `mcp`) não está instalado. Rode "
            "`.venv/bin/python -m pip install -r requirements.txt`. As funções "
            "`listar_ferramentas` e `chamar_ferramenta` funcionam sem ele."
        ) from exc

    from usp_mcp.adaptador import anotar

    # Indexado por NOME, e não desempacotado por posição. O desempacotamento
    # posicional já matou este servidor uma vez: em 14/09 `main()` abria três
    # descritores, `listar_ferramentas` passou a devolver quatro, e o processo
    # morreu antes do handshake com a suíte verde em tudo que não fosse o T78.
    # Um dicionário não tem essa forma de falhar — ferramenta nova só precisa
    # ser registrada, nunca contada.
    portas = {f["name"]: f for f in listar_ferramentas()}
    porta_material = portas[_NOME_MATERIAL]
    porta_arquivo = portas[_NOME_ARQUIVO]
    porta_diagnostico = portas[_NOME_DIAGNOSTICO]
    porta_ja_entreguei = portas[_NOME_JA_ENTREGUEI]
    porta_notas = portas[_NOME_NOTAS]
    porta_avisos = portas[_NOME_AVISOS]
    porta_mudou = portas[_NOME_MUDOU]
    descritor = portas[_NOME_FERRAMENTA]
    servidor = MCPServer(name="usp-mcp-moodle", version="0.1.0")

    def _chamar(nome: str, argumentos: dict) -> str:
        """A tradução do erro do domínio para o canal que o modelo lê.

        Um ponto só para as três ferramentas: repetir o `try` em cada closure
        seria a terceira cópia da mesma regra, e a que alguém esquece de pôr na
        quarta ferramenta. `ToolError` é o canal que o SDK define para "falha
        prevista, a mensagem é para o modelo ler" — sem isto, o 2.2.0 classifica
        `ErroMoodle` como crash e entrega 32 bytes de `Error executing tool
        o_que_vence`, com a cura ("configure o MOODLE_TOKEN no .env") presa no
        stderr (medido em 10/09/2026).

        Só `ErroMoodle` é traduzido. `except Exception` aqui seria pior do que o
        silêncio: este é o entrypoint com credencial pessoal (Invariante 4), e o
        texto de uma exceção imprevista deste processo não tem por que viajar.
        """
        try:
            return chamar_ferramenta(nome, argumentos)
        except ErroMoodle as exc:
            raise ToolError(str(exc)) from exc

    def _o_que_vence(dias=14, limite=None) -> str:
        # Assinatura explícita em vez de `**kwargs`: o SDK deriva o schema que
        # o modelo vê a partir dela, e um `**kwargs` produziria uma ferramenta
        # sem parâmetro nenhum. Mantida em sincronia com o `inputSchema` de
        # `listar_ferramentas` — `_auto_verificar` compara os dois.
        return _chamar(descritor["name"], {"dias": dias, "limite": limite})

    # O SDK lê a ASSINATURA, não o inputSchema declarado (§9, 31/08/2026). Sem
    # isto, "Padrão 14" e a explicação de `limite` não chegam ao modelo.
    anotar(_o_que_vence, descritor["inputSchema"], {"dias": int, "limite": int | None})
    servidor.tool(name=descritor["name"], description=descritor["description"])(_o_que_vence)

    def _material(disciplina, busca=None) -> str:
        # `disciplina` SEM default de propósito: no SDK é a ausência de default
        # que torna o parâmetro obrigatório no fio, e o `inputSchema` a declara
        # em `required`. Com `=None` os dois divergiam e o modelo via uma
        # ferramenta que aceita ser chamada sem disciplina — H6 pegou.
        return _chamar(
            porta_material["name"], {"disciplina": disciplina, "busca": busca}
        )

    # Mesmo motivo: sem `anotar`, "Espaço e caixa não importam" e a explicação de
    # `busca` não chegam ao modelo — ele veria só {"title": "Disciplina"}.
    anotar(_material, porta_material["inputSchema"], {"disciplina": str, "busca": str | None})
    servidor.tool(name=porta_material["name"], description=porta_material["description"])(_material)

    def _baixar_arquivo(disciplina, nome, todos=False) -> str:
        # `disciplina` e `nome` SEM default: no SDK é a ausência de default que
        # torna o parâmetro obrigatório no fio, e o `inputSchema` os declara em
        # `required`. Com `=None` os dois divergiriam — foi assim que H6 pegou
        # `material` em 31/08.
        return _chamar(
            porta_arquivo["name"],
            {"disciplina": disciplina, "nome": nome, "todos": todos},
        )

    anotar(
        _baixar_arquivo,
        porta_arquivo["inputSchema"],
        {"disciplina": str, "nome": str, "todos": bool},
    )
    servidor.tool(
        name=porta_arquivo["name"], description=porta_arquivo["description"]
    )(_baixar_arquivo)

    def _diagnostico() -> str:
        # Sem parâmetro nenhum, e é de propósito: a pergunta é sobre o site
        # inteiro. `anotar` ainda é chamado para manter uma porta só de entrada
        # do schema declarado — com `properties` vazio ele só fixa o retorno.
        try:
            return chamar_ferramenta(porta_diagnostico["name"], {})
        except ErroMoodle as exc:
            raise ToolError(str(exc)) from exc

    anotar(_diagnostico, porta_diagnostico["inputSchema"], {})
    servidor.tool(
        name=porta_diagnostico["name"], description=porta_diagnostico["description"]
    )(_diagnostico)

    def _ja_entreguei(disciplina, entrega=None) -> str:
        # `disciplina` SEM default: é a ausência de default que torna o
        # parâmetro obrigatório no fio, e o `inputSchema` a declara em
        # `required`. Com `=None` os dois divergiriam (H6, 31/08).
        return _chamar(
            porta_ja_entreguei["name"],
            {"disciplina": disciplina, "entrega": entrega},
        )

    anotar(
        _ja_entreguei,
        porta_ja_entreguei["inputSchema"],
        {"disciplina": str, "entrega": str | None},
    )
    servidor.tool(
        name=porta_ja_entreguei["name"], description=porta_ja_entreguei["description"]
    )(_ja_entreguei)

    def _notas(disciplina=None) -> str:
        # `disciplina` COM default, ao contrário das outras três: aqui ela é
        # opcional de verdade, e o `inputSchema` a declara fora de `required`.
        # É a mesma regra de H6 lida ao contrário — o que não pode é divergir.
        return _chamar(porta_notas["name"], {"disciplina": disciplina})

    anotar(_notas, porta_notas["inputSchema"], {"disciplina": str | None})
    servidor.tool(
        name=porta_notas["name"], description=porta_notas["description"]
    )(_notas)

    def _avisos(disciplina) -> str:
        # `disciplina` SEM default, como em `material` e `ja_entreguei`: é a
        # ausência de default que torna o parâmetro obrigatório no fio, e o
        # `inputSchema` a declara em `required` (H6, 31/08). Aqui ela é mesmo
        # obrigatória — sem escopo, `courseids` vazio traria as 74 matrículas.
        return _chamar(porta_avisos["name"], {"disciplina": disciplina})

    anotar(_avisos, porta_avisos["inputSchema"], {"disciplina": str})
    servidor.tool(
        name=porta_avisos["name"], description=porta_avisos["description"]
    )(_avisos)

    def _o_que_mudou(disciplina, dias=7) -> str:
        # `disciplina` SEM default e `dias` COM: é a assinatura que o SDK lê para
        # decidir o que é obrigatório no fio, e o `inputSchema` declara os dois
        # do mesmo jeito. O default 7 aparece nos dois lugares de propósito —
        # divergir é o que H6 pegou em 31/08.
        return _chamar(porta_mudou["name"], {"disciplina": disciplina, "dias": dias})

    anotar(
        _o_que_mudou, porta_mudou["inputSchema"], {"disciplina": str, "dias": int}
    )
    servidor.tool(
        name=porta_mudou["name"], description=porta_mudou["description"]
    )(_o_que_mudou)

    servidor.run(transport="stdio")


def _auto_verificar() -> int:  # pragma: no cover — utilitário de linha de comando
    """`python -m usp_mcp.moodle.server --auto-verificar`: o que dá para
    checar sem tocar a rede da USP nem gastar uma chamada da conta.

    Nasceu porque `main()` não tinha teste. Desde 31/08/2026 tem
    (`tests/handshake/`), e isto continua útil por outro motivo: roda em um
    comando, imprime o diagnóstico de configuração (`.env`, token, SDK) que um
    teste não imprime, e responde "por que o servidor não sobe aqui" mais rápido
    do que uma suíte.
    """
    from .. import env as _env

    print("ferramentas expostas :", [f["name"] for f in listar_ferramentas()])

    arquivo = _env.achar_env()
    print(".env encontrado      :", arquivo or "NÃO — copie .env.example")
    _env.carregar_env()
    # Forma, nunca valor (Invariante 3).
    token = os.environ.get("MOODLE_TOKEN") or ""
    print(
        "MOODLE_TOKEN         :",
        f"presente, {len(token)} chars" if token else "AUSENTE",
    )
    print("MOODLE_URL           :", os.environ.get("MOODLE_URL", _URL_PADRAO))

    try:
        from mcp.server import MCPServer  # noqa: F401
    except ImportError:
        print("SDK do MCP           : AUSENTE — pip install -r requirements.txt")
        return 1
    print("SDK do MCP           : presente")

    # O schema que o modelo vê tem de casar com a assinatura que o adaptador
    # registra. Isto checava a PRIMEIRA ferramenta e imprimia "OK" como se
    # falasse pelas duas — meia checagem com cara de checagem inteira, que é o
    # Invariante 7 quebrado dentro da própria ferramenta de verificação.
    # Corrigido em 31/08; a cobertura de verdade está em T79.
    import inspect

    from mcp.server import MCPServer as _M

    servidor = _M(name="verificacao", version="0.0.0")

    @servidor.tool(name="o_que_vence", description="verificação")
    def _sonda_vence(dias: int = 14, limite: int | None = None) -> str:
        return ""

    @servidor.tool(name="material", description="verificação")
    def _sonda_material(disciplina: str, busca: str | None = None) -> str:
        return ""

    @servidor.tool(name="baixar_arquivo", description="verificação")
    def _sonda_arquivo(disciplina: str, nome: str, todos: bool = False) -> str:
        return ""

    @servidor.tool(name="diagnostico", description="verificação")
    def _sonda_diagnostico() -> str:
        return ""

    @servidor.tool(name="ja_entreguei", description="verificação")
    def _sonda_ja_entreguei(disciplina: str, entrega: str | None = None) -> str:
        return ""

    @servidor.tool(name="notas", description="verificação")
    def _sonda_notas(disciplina: str | None = None) -> str:
        return ""

    @servidor.tool(name="avisos", description="verificação")
    def _sonda_avisos(disciplina: str) -> str:
        return ""

    @servidor.tool(name="o_que_mudou", description="verificação")
    def _sonda_mudou(disciplina: str, dias: int = 7) -> str:
        return ""

    sondas = {
        "o_que_vence": _sonda_vence,
        "material": _sonda_material,
        "baixar_arquivo": _sonda_arquivo,
        "diagnostico": _sonda_diagnostico,
        "ja_entreguei": _sonda_ja_entreguei,
        "notas": _sonda_notas,
        "avisos": _sonda_avisos,
        "o_que_mudou": _sonda_mudou,
    }
    divergiu = False
    for ferramenta in listar_ferramentas():
        nome = ferramenta["name"]
        declarados = set(ferramenta["inputSchema"]["properties"])
        sonda = sondas.get(nome)
        if sonda is None:
            print(f"schema x assinatura  : {nome}: SEM SONDA — acrescente uma aqui")
            divergiu = True
            continue
        reais = set(inspect.signature(sonda).parameters)
        estado = "OK" if declarados == reais else f"DIVERGEM {declarados ^ reais}"
        print(f"schema x assinatura  : {nome}: {estado}")
        divergiu = divergiu or declarados != reais
    if divergiu:
        return 1

    print()
    print("Nada acima tocou a rede da USP. A suíte já cobre a fronteira MCP")
    print("offline (T78-T81); o que falta é a rede — plugar e perguntar.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    if "--auto-verificar" in sys.argv:
        raise SystemExit(_auto_verificar())
    main()
