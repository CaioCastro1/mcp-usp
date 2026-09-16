#!/usr/bin/env python3
"""Higienização do §3.3 do SPEC1 em código.

Troca dado pessoal por valor sintético **estável** (mesmo valor de entrada →
mesmo valor falso, sempre) para que uma fixture do Moodle possa entrar no git.

Duas propriedades, e a segunda não está no §3.3 — é requisito do teste de custo:

1. **Preserva a forma.** Mesmas chaves, mesma ordem, mesmos tipos, mesma
   contagem de itens. A forma é o que interessa para teste (§3.3).
2. **Preserva o comprimento.** Texto substituído tem o mesmo número de bytes do
   original; número substituído tem a mesma quantidade de dígitos. Sem isso a
   fixture não sustenta a asserção de bytes/evento, porque trocar um `summary`
   de 9 kB por uma frase curta apagaria justamente o custo que a projeção
   existe para resolver.

Uso:
    python3 scripts/higienizar.py <entrada.json> <saida.json>
    python3 scripts/higienizar.py --verificar <arquivo.json> [...]

Como a regra decide o que é dado pessoal (16/09/2026)
-----------------------------------------------------
Até 15/09 a decisão era uma lista de nomes exatos de campo, e ela envelheceu a
cada função nova do Moodle: `usermodifiedfullname` (fórum) e `useridnumber`
(nota) escaparam primeiro; depois `percentageformatted` (o percentual real ao
lado da nota trocada), `filename` (Número USP de um colega no nome do arquivo
de uma entrega em grupo) e `userpictureurl` (contexto de usuário de um
professor, estável e único por pessoa) chegaram à `main`. O buraco não era
nenhum dos três campos: era decidir por igualdade de nome. Agora são três
camadas, e a ordem importa:

1. **Família pela chave, por rede de prefixo/sufixo.** `*fullname` é nome,
   `*email` é e-mail, `*pictureurl` é imagem de pessoa, `*filename`/`*fileurl`
   são arquivo, `grade*`/`percentage*`/`rank*` são nota (menos os sufixos que
   descrevem a FORMA da nota: `format`, `max`, `hidden`...), `*accesskey`/
   `*token` são credencial, `lastaccess`/`gradedate*` e todo `time*` debaixo
   de `submission` são instante de atividade do dono. Campo novo de família
   conhecida cai na rede sem ninguém escrever o nome dele aqui.
2. **Conteúdo, independente da chave.** E-mail, URL de contexto de usuário
   (`pluginfile.php/<n>/user/`), token de 32 hex, `wstoken=` em query, e nome
   depois de honorífico ("Prof. Fulano"). É a rede para o que chega em campo
   que família nenhuma prevê — `name` de módulo e `shortname` de turma, que
   são o produto e por isso NÃO são trocados por inteiro.
3. **Tipo.** O substituto tem o tipo do original: `int` continua `int` com a
   mesma quantidade de dígitos, `float` continua `float`, string continua com
   os mesmos bytes. Epoch vira epoch deslocado, não número aleatório.

Marca reconhecível: run de dígitos trocado dentro de texto começa com `0`, e
credencial sintética começa com `0000`. Id real do Moodle nunca tem zero à
esquerda, então `alertas()` — a varredura por conteúdo que roda sobre toda
fixture publicada — consegue acusar o real sem acusar a própria saída.

O que fica de fora de propósito, e por quê: `id`, `courseid`, `cmid`,
`contextid` e o contexto de curso nas `fileurl` (os testes de download usam os
reais, e não identificam pessoa); `name`/`shortname` fora da rede de
honorífico (rótulo é o produto); `timemodified` de material (não é atividade
do dono); `enrolledusercount` e `grademax` (forma do curso, não do dono).
Errar para o lado seguro tem limite: trocá-los faria a fixture mentir sobre a
disciplina, que é o que ela existe para descrever.

Limitação declarada: a substituição é derivada de hash do valor original. Ela
não é reversível a partir da saída, mas também não é prova contra quem já tenha
uma lista de candidatos e queira testar qual bate. Serve para o que o §3.3 pede
— não publicar nome, e-mail, userid e nota do dono — e não é anonimização forte.
Nome de pessoa em texto livre SEM honorífico (um `name` de módulo "Relatório da
Fulana") continua passando: a rede de conteúdo só sabe reconhecer o que tem
marca. Isso está no BACKLOG de 15/09.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from itertools import islice
from typing import Any, Iterator

# --------------------------------------------------------------- famílias
# Cada família tem um conjunto exato (o que já foi visto) e uma rede por
# prefixo/sufixo (o que ainda não foi). O conjunto exato existe para registrar
# a história e para os poucos nomes que a rede não alcança.

CAMPOS_IDENTIFICADOR = {
    "userid", "userrole", "usermodified",
    # 15/09/2026: `useridnumber` é o NÚMERO USP, e chega em
    # `gradereport_user_get_grade_items` como string de dígitos. É identificador
    # mais forte que o `userid` interno, porque vale fora do Moodle.
    "useridnumber",
    # 16/09/2026: quem corrigiu, e a lista de colegas que ainda não entregaram.
    "grader", "relateduserid", "modifierid",
    "submissiongroupmemberswhoneedtosubmit",
}
SUFIXOS_IDENTIFICADOR = ("userid", "useridnumber")
# Dentro destes pais, `id` é id de pessoa (o `author` de `get_discussion_posts`
# é um dicionário com `id`, `fullname` e `urls.profileimage`).
CONTEXTOS_DE_PESSOA = {"author", "user", "userdata", "usermodifieduser", "grader"}

CAMPOS_NOME = {
    "fullname", "fullnamedisplay", "firstname", "lastname", "username",
    "displayname", "author", "authorfullname", "userfullname",
    # 15/09/2026: `usermodifiedfullname` chega em `mod_forum_get_forum_discussions`
    # e ficava de fora, porque a lista era escrita nome a nome e ninguém tinha
    # capturado fórum ainda. Vazou o nome real de um professor para a fixture.
    "usermodifiedfullname",
}
SUFIXOS_NOME = ("fullname", "firstname", "lastname", "username", "displayname")

CAMPOS_EMAIL = {"email", "useremail"}
SUFIXOS_EMAIL = ("email",)

# Foto de pessoa: a URL carrega o contexto de usuário, estável e único.
SUFIXOS_IMAGEM = ("pictureurl", "imageurl", "imageurlsmall", "profileimage")

# Credencial: `userprivateaccesskey` de `core_webservice_get_site_info` é a
# chave do RSS da conta — vale tanto quanto um token.
CAMPOS_CREDENCIAL = {
    "userprivateaccesskey", "token", "wstoken", "sesskey", "privatetoken",
    "password", "secret", "apikey",
}
SUFIXOS_CREDENCIAL = ("accesskey", "token", "sesskey", "secret", "password", "privatekey", "apikey")

# Campos que são esvaziados em vez de substituídos: blob serializado do PHP que
# consumidor nenhum lê e que carrega o que o Moodle quiser pôr lá dentro. Em
# 15/09/2026 o `customdata` de PTC3314 guardava o nome de um professor 50 vezes,
# e a projeção do projeto já o descartava — ninguém perde nada esvaziando.
CAMPOS_OPACOS = {"customdata"}

SUFIXOS_ARQUIVO = ("filename",)
SUFIXOS_URL_ARQUIVO = ("fileurl",)

CAMPOS_NOTA = {
    "grade", "rawgrade", "gradeformatted", "graderaw", "finalgrade",
    # 16/09/2026: os três primeiros estavam na captura de 15/09 ao lado de
    # `graderaw` e `gradeformatted` trocados, e diziam a nota do mesmo jeito.
    "percentageformatted", "percentageraw", "lettergradeformatted", "rank",
    "gradefordisplay",
}
PREFIXOS_NOTA = ("grade", "percentage", "lettergrade", "rank", "finalgrade", "rawgrade")
# Debaixo do prefixo de nota, o que descreve a forma do item e não o valor do
# dono: `feedbackformat`, `grademax`, `gradeishidden`, `gradetype`, `grade_forum`.
SUFIXOS_ESTRUTURAIS = (
    "format", "type", "status", "enabled", "hidden", "hiddenbydate", "locked",
    "overridden", "needsupdate", "id", "url", "count", "max", "min", "pass",
    "items", "method", "penalty", "penalties", "visible", "forum", "notify",
    "duedate", "scale", "outcome",
)

# Instante de atividade do dono. `timemodified` de arquivo ou de curso não entra:
# é do material. O que entra é quando o dono acessou, entregou, foi corrigido.
CAMPOS_INSTANTE = {
    "lastaccess", "lastlogin", "currentlogin", "firstaccess", "lastcourseaccess",
    "timesubmitted", "timegraded", "gradeddate",
}
PREFIXOS_INSTANTE = ("gradedate", "lastaccess", "lastlogin", "firstaccess")
# Dentro destes pais, todo `time*` é atividade do dono (quando entregou).
CONTEXTOS_DE_ENTREGA = {"submission", "teamsubmission"}

# Texto escrito por pessoa: pode nomear professor, sala, colega, turma.
CAMPOS_TEXTO_LIVRE = {
    "summary", "description", "location", "formattedlocation", "activitystr",
    "message", "subject", "intro",
    # 16/09/2026: entrega em texto (`editorfields[].text`), comentário do
    # corretor (`feedback`), rótulo de evento (`activity`) e a condição de
    # acesso que nomeia a turma do dono (`availabilityinfo`).
    "text", "feedback", "activity", "availabilityinfo", "comment", "commenttext",
    "note", "notes",
}
# `text` fica fora da rede de sufixo de propósito: `context` termina em `text`.
SUFIXOS_TEXTO = ("description", "summary", "message", "intro", "comment", "notes")

_ALFABETO = "abcdefghijklmnopqrstuvwxyz"
_SILABAS = ["ba", "ce", "di", "fo", "gu", "la", "me", "ni", "ro", "su", "ta", "vi"]
_HEX = "0123456789abcdef"
_ALFANUMERICO = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _semente(valor: Any) -> int:
    """Inteiro estável derivado do valor. Mesmo valor → mesma semente."""
    bruto = json.dumps(valor, ensure_ascii=False, sort_keys=True)
    return int.from_bytes(hashlib.sha256(bruto.encode()).digest()[:8], "big")


def _fluxo(valor: Any) -> Iterator[int]:
    """Bytes pseudoaleatórios estáveis, sem fim, derivados do valor."""
    bruto = json.dumps(valor, ensure_ascii=False, sort_keys=True).encode()
    i = 0
    while True:
        yield from hashlib.sha256(bruto + i.to_bytes(4, "big")).digest()
        i += 1


def _nome_sintetico(original: str, sal: str = "") -> str:
    """Nome falso estável com o MESMO comprimento em bytes do original. `sal`
    muda só a semente, para quem precisa de uma segunda tentativa."""
    alvo = len(original.encode())
    if alvo == 0:
        return ""
    s = _semente(original + sal)
    partes, acumulado = [], 0
    while acumulado < alvo:
        p = _SILABAS[s % len(_SILABAS)].capitalize()
        partes.append(p)
        acumulado += len(p) + 1
        s //= len(_SILABAS)
        if s == 0:
            s = _semente(str(acumulado))
    return " ".join(partes)[:alvo].ljust(alvo, "o")


def _texto_sintetico(original: str) -> str:
    """Texto falso estável, mesmo comprimento em bytes.

    Mantém a aparência de HTML quando o original tinha tag, porque o §1.2 e a
    linha 3 do Moodle registram HTML embutido em campo de descrição e a camada
    de projeção precisa continuar vendo isso.
    """
    alvo = len(original.encode())
    if alvo == 0:
        return ""
    tinha_html = "<" in original and ">" in original
    s = _semente(original)
    corpo, acumulado = [], 0
    while acumulado < alvo + 8:
        p = _SILABAS[s % len(_SILABAS)] + _ALFABETO[s % 26]
        corpo.append(p)
        acumulado += len(p) + 1
        s = s // len(_SILABAS) or _semente(str(acumulado))
    texto = " ".join(corpo)
    if tinha_html:
        texto = f"<p>{texto}</p>"
    b = texto.encode()[:alvo]
    # corta em fronteira de caractere sem mudar o número de bytes
    while True:
        try:
            b.decode()
            break
        except UnicodeDecodeError:
            b = b[:-1] + b"x"
    return b.decode()


def _email_sintetico(original: str) -> str:
    alvo = len(original.encode())
    base = f"pessoa{_semente(original) % 10**6:06d}"
    dominio = "@exemplo.invalid"
    montado = (base + dominio)[:alvo] if alvo else ""
    return montado.ljust(alvo, "x") if alvo else ""


def _id_sintetico(original: int) -> int:
    """Id falso estável com o mesmo número de dígitos e o mesmo sinal. Zero
    fica zero: em `teamsubmission.userid` ele significa "é do grupo"."""
    if original == 0:
        return 0
    digitos = len(str(abs(original)))
    piso = 10 ** (digitos - 1)
    falso = piso + (_semente(original) % (10 * piso - piso))
    return -falso if original < 0 else falso


def _instante_sintetico(epoch: int) -> int:
    """Epoch deslocado de até ±30 dias, estável. Continua sendo um instante
    plausível do mesmo semestre, e deixa de ser o segundo exato em que o dono
    fez alguma coisa."""
    return epoch - 30 * 86400 + _semente(epoch) % (60 * 86400)


def _numero_sintetico(n: int | float) -> int | float:
    """Mesmo tipo, mesma ordem de grandeza. Epoch (≥ 1e9) vira epoch."""
    if isinstance(n, float):
        if n == 0:
            return 0.0
        inteiro = int(abs(n))
        digitos = len(str(inteiro)) if inteiro else 1
        piso = 10 ** (digitos - 1) if inteiro else 0
        teto = 10 ** digitos
        valor = piso + (_semente(n) % ((teto - piso) * 100)) / 100
        return round(math.copysign(valor, n), 2)
    if abs(n) >= 10**9:
        return _instante_sintetico(n)
    return _id_sintetico(n)


_RE_DIGITOS = re.compile(r"\d+")


def _trocar_digitos(texto: str, minimo: int, marcar: bool = True) -> str:
    """Troca cada run de ≥ `minimo` dígitos por um run sintético do MESMO
    tamanho. Com `marcar`, o run começa com `0` — id real nunca começa assim,
    e é o que deixa `alertas()` distinguir a saída deste script do dado cru."""
    def sub(m: re.Match) -> str:
        run = m.group()
        if len(run) < minimo:
            return run
        corpo = "".join(str(b % 10) for b in islice(_fluxo(run), len(run)))
        if marcar and len(run) >= 2:
            return "0" + corpo[1:]
        return corpo
    return _RE_DIGITOS.sub(sub, texto)


def _formatado_sintetico(valor: str) -> str:
    """Nota em texto: `"6,19"`, `"20,00 %"`, `"<div>7,50</div>"`, `"A"`.

    Se tem dígito, troca só os dígitos e mantém vírgula, símbolo e HTML — a
    forma que a projeção lê. Marcador de "sem nota" (`"-"`, vazio) fica como
    está: ele é forma, não valor. Escala verbal ("Satisfatório") vira nome
    sintético do mesmo tamanho.
    """
    if not any(ch.isalnum() for ch in valor):
        return valor
    if any(ch.isdigit() for ch in valor):
        return _trocar_digitos(valor, 1, marcar=False)
    # Conceito de uma letra ("C"): a sílaba sorteada começa com a mesma letra
    # uma vez em doze. Tenta de novo até sair diferente — nota é valor do dono.
    for tentativa in range(16):
        falso = _nome_sintetico(valor, sal=str(tentativa) if tentativa else "")
        if falso != valor:
            return falso
    return falso


def _credencial_sintetica(original: str) -> str:
    """Mesmo comprimento, mesma classe de caracteres, prefixo `0000`."""
    alvo = len(original.encode())
    if alvo == 0:
        return ""
    hexa = all(c in _HEX for c in original.lower())
    alfabeto = _HEX if hexa else _ALFANUMERICO
    corpo = "".join(alfabeto[b % len(alfabeto)] for b in islice(_fluxo(original), alvo))
    return ("0000" + corpo[4:])[:alvo]


_RE_ESCAPE_URL = re.compile(r"(%[0-9A-Fa-f]{2})")


def _url_de_arquivo_sintetica(url: str) -> str:
    """Só o nome do arquivo no fim do caminho é trocado. O contexto
    (`pluginfile.php/<n>/`) é do curso, e os testes de download dependem dele.

    O nome vem percent-encoded, e `%20` seguido de `2026` pareceria um run de
    seis dígitos: os escapes são separados antes e ficam como estão."""
    caminho, sep, query = url.partition("?")
    pasta, barra, base = caminho.rpartition("/")
    pedacos = _RE_ESCAPE_URL.split(base)
    base = "".join(
        p if _RE_ESCAPE_URL.fullmatch(p) else _trocar_digitos(p, 5) for p in pedacos
    )
    return pasta + barra + base + sep + query


# ------------------------------------------------ redes por conteúdo
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_RE_CONTEXTO_USUARIO = re.compile(r"(pluginfile\.php/)(\d+)(/user/)")
_RE_HEX32 = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])")
_RE_PARAM_SEGREDO = re.compile(r"((?:wstoken|token|sesskey|privatetoken)=)([^&\s\"'<>]+)")
_RE_HONORIFICO = re.compile(
    r"(\b(?:Prof|Profa|Professor|Professora|Dr|Dra)\.?\s+)"
    r"((?:[A-ZÀ-Ý]\.\s*)*[A-ZÀ-Ý][A-Za-zÀ-ÿ'-]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][A-Za-zÀ-ÿ'-]+)*)"
)


def _conteudo(texto: str) -> str:
    """As redes que valem para QUALQUER string, seja qual for a chave."""
    # O teste barato do "@" vem antes de propósito: o regex faz backtracking
    # quadrático em texto longo sem arroba, e um `summary` de 9 kB é esse caso.
    if "@" in texto and _RE_EMAIL.search(texto):
        texto = _RE_EMAIL.sub(lambda m: _email_sintetico(m.group()), texto)
    if "/user/" in texto:
        texto = _RE_CONTEXTO_USUARIO.sub(
            lambda m: m.group(1) + _trocar_digitos(m.group(2), 1) + m.group(3), texto
        )
    if "=" in texto:
        texto = _RE_PARAM_SEGREDO.sub(
            lambda m: m.group(1) + _credencial_sintetica(m.group(2)), texto
        )
    if len(texto) >= 32:
        texto = _RE_HEX32.sub(lambda m: _credencial_sintetica(m.group()), texto)
    if "Prof" in texto or "Dr" in texto:
        texto = _RE_HONORIFICO.sub(
            lambda m: m.group(1) + _nome_sintetico(m.group(2)), texto
        )
    return texto


# --------------------------------------------------------- a decisão
def _familia(k: str, trilha: tuple[str, ...]) -> str | None:
    """Família de uma chave (já em minúsculas). A ordem resolve os empates:
    `usermodifiedpictureurl` é imagem antes de ser nome, `gradedategraded` é
    instante antes de ser nota."""
    if k in CAMPOS_OPACOS:
        return "opaco"
    if k in CAMPOS_CREDENCIAL or k.endswith(SUFIXOS_CREDENCIAL):
        return "credencial"
    if k in CAMPOS_EMAIL or k.endswith(SUFIXOS_EMAIL):
        return "email"
    if k.endswith(SUFIXOS_IMAGEM):
        return "imagem"
    if k in CAMPOS_NOME or k.endswith(SUFIXOS_NOME):
        return "nome"
    if k in CAMPOS_IDENTIFICADOR or k.endswith(SUFIXOS_IDENTIFICADOR):
        return "identificador"
    if k == "id" and trilha and trilha[-1] in CONTEXTOS_DE_PESSOA:
        return "identificador"
    if k.endswith(SUFIXOS_ARQUIVO):
        return "arquivo"
    if k.endswith(SUFIXOS_URL_ARQUIVO):
        return "url_arquivo"
    if k in CAMPOS_INSTANTE or k.startswith(PREFIXOS_INSTANTE):
        return "instante"
    if k.startswith("time") and any(p in CONTEXTOS_DE_ENTREGA for p in trilha):
        return "instante"
    if k in CAMPOS_NOTA:
        return "nota"
    if k.startswith(PREFIXOS_NOTA) and not k.endswith(SUFIXOS_ESTRUTURAIS):
        return "nota"
    if k in CAMPOS_TEXTO_LIVRE or k.endswith(SUFIXOS_TEXTO):
        return "texto"
    return None


def _string(valor: str, familia: str | None) -> str:
    if familia == "opaco":
        return ""
    if familia == "credencial":
        return _credencial_sintetica(valor)
    if familia == "email":
        return _email_sintetico(valor)
    if familia == "imagem":
        return _trocar_digitos(valor, 4)
    if familia == "nome":
        return _nome_sintetico(valor)
    if familia == "identificador":
        # Preserva o número de dígitos, para a fixture continuar parecendo o que
        # é — e sai com a marca de zero à esquerda, para a varredura saber que
        # este `useridnumber` de 8 dígitos não é um Número USP.
        return _trocar_digitos(valor, 1) if valor.isdigit() else _nome_sintetico(valor)
    if familia == "arquivo":
        return _conteudo(_trocar_digitos(valor, 5))
    if familia == "url_arquivo":
        return _conteudo(_url_de_arquivo_sintetica(valor))
    if familia == "nota":
        return _formatado_sintetico(valor)
    if familia == "texto":
        return _texto_sintetico(valor)
    if familia == "instante":
        return _trocar_digitos(valor, 1, marcar=False)
    return _conteudo(valor)


def _numero(valor: int | float, familia: str | None) -> int | float:
    if familia == "identificador" and isinstance(valor, int):
        return _id_sintetico(valor)
    if familia in ("identificador", "nota", "instante", "credencial"):
        return _numero_sintetico(valor)
    return valor


def higienizar(no: Any, chave: str | None = None, trilha: tuple[str, ...] = ()) -> Any:
    """Mesma forma, valores pessoais trocados. `trilha` são as chaves dos
    dicionários acima deste nó (lista não conta), para as regras de contexto."""
    if isinstance(no, dict):
        abaixo = trilha + (chave.lower(),) if chave is not None else trilha
        return {k: higienizar(v, k, abaixo) for k, v in no.items()}
    if isinstance(no, list):
        return [higienizar(v, chave, trilha) for v in no]
    if chave is None or no is None or isinstance(no, bool):
        return no
    familia = _familia(chave.lower(), trilha)
    if isinstance(no, str):
        return _string(no, familia)
    if isinstance(no, (int, float)):
        return _numero(no, familia)
    return no


# ------------------------------------------------------- a varredura
_RE_NUSP_SOLTO = re.compile(r"(?<![A-Za-z0-9/=.])[1-9]\d{7}(?!\d)")
_RE_CONTEXTO_USUARIO_REAL = re.compile(r"pluginfile\.php/[1-9]\d*/user/")
_RE_PALAVRA_SINTETICA = re.compile("(?:" + "|".join(_SILABAS) + ")+o*")


def _nome_e_sintetico(nome: str) -> bool:
    """`_nome_sintetico` só produz sílabas de `_SILABAS` e `o` de enchimento."""
    palavras = [p.strip(".").lower() for p in nome.split()]
    return all(len(p) <= 1 or _RE_PALAVRA_SINTETICA.fullmatch(p) for p in palavras)


def alertas(no: Any, caminho: str = "") -> list[str]:
    """Varredura por CONTEÚDO, cega para o nome da chave: o que ainda tem cara
    de dado pessoal depois da higienização. Devolve `caminho: motivo`, nunca o
    valor — a saída disto vai para terminal e para relatório de teste.

    É a rede de baixo. A regra por família troca o que ela reconhece; isto
    acusa o que chegou por chave que família nenhuma previa.
    """
    achados: list[str] = []
    if isinstance(no, dict):
        for k, v in no.items():
            achados += alertas(v, f"{caminho}.{k}" if caminho else k)
        return achados
    if isinstance(no, list):
        for i, v in enumerate(no):
            achados += alertas(v, f"{caminho}[{i}]")
        return achados
    if not isinstance(no, str):
        return achados

    if "@" in no:
        for m in _RE_EMAIL.findall(no):
            if not m.endswith("exemplo.invalid"):
                achados.append(f"{caminho}: e-mail fora de exemplo.invalid")
                break
    if "/user/" in no and _RE_CONTEXTO_USUARIO_REAL.search(no):
        achados.append(f"{caminho}: URL com contexto de usuário real (pluginfile.php/<n>/user/)")
    if len(no) >= 32:
        for m in _RE_HEX32.findall(no):
            if not m.startswith("0000"):
                achados.append(f"{caminho}: string de 32 hex (forma de token)")
                break
    if "=" in no:
        for _, valor in _RE_PARAM_SEGREDO.findall(no):
            if not valor.startswith("0000"):
                achados.append(f"{caminho}: credencial em parâmetro de URL")
                break
    # Tamanho em bytes ("10485760" em `configs[].value` de mod_assign) é o
    # único inteiro de 8 dígitos que chega como string inteira e não é gente:
    # múltiplo exato de 1024. Um Número USP é múltiplo de 1024 uma vez em mil.
    tamanho_em_bytes = no.isdigit() and int(no) % 1024 == 0
    if not no.startswith("data:") and not tamanho_em_bytes and _RE_NUSP_SOLTO.search(no):
        achados.append(f"{caminho}: run de 8 dígitos solto (forma de Número USP)")
    if "Prof" in no or "Dr" in no:
        for _, nome in _RE_HONORIFICO.findall(no):
            if not _nome_e_sintetico(nome):
                achados.append(f"{caminho}: nome depois de honorífico")
                break
    return achados


# --------------------------------------------------------------- CLI
def _verificar(caminhos: list[str]) -> int:
    sujos = 0
    for caminho in caminhos:
        with open(caminho, encoding="utf-8") as fh:
            achados = alertas(json.load(fh))
        if achados:
            sujos += 1
            print(f"{caminho}: {len(achados)} alerta(s)")
            for a in achados:
                print(f"  {a}")
        else:
            print(f"{caminho}: limpo")
    return 1 if sujos else 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "--verificar":
        return _verificar(argv[2:])
    if len(argv) != 3:
        print(
            f"uso: {argv[0]} <entrada.json> <saida.json>\n"
            f"     {argv[0]} --verificar <arquivo.json> [...]",
            file=sys.stderr,
        )
        return 2
    entrada, saida = argv[1], argv[2]
    with open(entrada, encoding="utf-8") as fh:
        cru = json.load(fh)
    limpo = higienizar(cru)
    restos = alertas(limpo)
    if restos:
        # Não grava: o que a família não trocou e a varredura ainda vê é
        # justamente o que não pode entrar no git. Sai o caminho, nunca o valor.
        print(f"{entrada}: {len(restos)} alerta(s) depois da higienização — NÃO gravei {saida}", file=sys.stderr)
        for a in restos:
            print(f"  {a}", file=sys.stderr)
        return 1
    with open(saida, "w", encoding="utf-8") as fh:
        json.dump(limpo, fh, ensure_ascii=False, separators=(",", ":"))
    import os
    print(
        f"{saida}: {os.path.getsize(saida)} B "
        f"(cru {os.path.getsize(entrada)} B) — forma e comprimento preservados, "
        "varredura de conteúdo limpa"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
