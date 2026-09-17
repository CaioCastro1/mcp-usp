"""Casar o que a pessoa digita com o que o Moodle escreveu.

Um lugar só, porque já houve dois. `disciplinas._normalizar` nasceu para resolver
sigla e ganhou o `NFD` em 31/08, quando o dono digitou "eletronica" e o filtro
descartou a letra acentuada inteira (T83). O filtro `busca` de `material` nasceu
no mesmo dia com `filtro in nome.lower()` e **não** ganhou a correção: medido em
01/09, "formulario" não achava "Formulário Provas Substitutivas.pdf". Duas
semânticas de casamento no mesmo servidor, e a terceira estava prestes a nascer
em `arquivo.py`.

**E o caminho de volta: escrever o que a pessoa lê.** `formatar_data` chegou aqui
em 14/09 pelo mesmo motivo. Ela nasceu privada em `o_que_vence`, e
`ja_entreguei` precisa dela exatamente igual: as duas respondem a mesma véspera
— uma diz o que vence, a outra diz o que disso já foi entregue — e duas grafias
do mesmo prazo fazem quem lê as duas respostas não reconhecer que é o mesmo
prazo. J18 trava isso.

`sem_html` chegou em 14/09 pela mesma porta, com `avisos`. O Moodle guarda o
corpo de um post de fórum em HTML, e ele é a primeira resposta deste projeto em
que o texto de terceiro sai no resultado em vez de virar contagem. Mora aqui, e
não em `avisos`, porque o próximo módulo que precisar dela vai ser o que lê
`intro` de atividade — e a terceira semântica de "tirar a marcação" é como as
duas de casamento por nome nasceram.

`links` chegou em 17/09 e é a previsão acima se cumprindo: `material` precisou
ler o `description` de bloco de texto (`label`) para achar o link que o professor
deixou no meio da frase, e o título desse link é HTML que passa por `sem_html`.
O extrator mora ao lado da limpeza pelo mesmo motivo que a limpeza mora ao lado
do casamento: uma semântica de "o que é marcação e o que é texto" por servidor.
"""
from __future__ import annotations

import html as _html
import re
import unicodedata
from datetime import datetime

# Abreviação de dia da semana em português. datetime.weekday() é 0=segunda,
# ..., 6=domingo — não usamos strftime("%a") porque isso depende do locale do
# processo (em inglês por padrão) e não deve variar entre máquinas.
_DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def formatar_data(quando: datetime) -> str:
    """"dom 06/09 23:59" — curto de propósito (T39: poucos milhares de
    caracteres para dezenas de eventos)."""
    dia = _DIAS_SEMANA[quando.weekday()]
    return f"{dia} {quando.day:02d}/{quando.month:02d} {quando.hour:02d}:{quando.minute:02d}"


# O que separa parágrafo de parágrafo quando a tag some. Sem isto, "…até sexta.
# </p><p>Levem calculadora" vira "…até sexta.Levem calculadora", e duas frases
# coladas mudam onde quem lê acha que a frase termina.
_QUEBRAS = re.compile(r"(?i)</\s*(p|div|li|tr|h[1-6])\s*>|<\s*br\s*/?\s*>")
_TAGS = re.compile(r"<[^>]*>")
_ESPACOS = re.compile(r"[ \t\r\f\v]+")
_LINHAS_VAZIAS = re.compile(r"\n{2,}")


def sem_html(bruto: str) -> str:
    """O corpo de um post de fórum, em texto corrido.

    Aqui e não em `avisos` porque é o mesmo caminho de volta de `formatar_data`:
    escrever o que a pessoa lê. O Moodle guarda o post em HTML, e repassá-lo cru
    faria quem pergunta receber `<p dir="ltr">` no meio da frase e pagaria o
    orçamento de texto com marcação.

    Três coisas de propósito, e as três já foram erro em algum lugar:

    1. **A entidade é traduzida antes das tags sumirem**, não depois: `at&eacute;`
       lido literalmente é uma palavra que não existe em português, e o
       e-Disciplinas escreve acento assim em post antigo.
    2. **Fecho de bloco vira quebra de linha**, senão duas frases se colam e o
       ponto final some no meio de uma palavra.
    3. **Nada de regex fazendo as vezes de parser.** Isto não interpreta HTML —
       descarta marcação de um texto que já é do aluno. Conteúdo entre `<script>`
       ou `<style>` não aparece em post de fórum do Moodle (o filtro do próprio
       Moodle já o remove na gravação), e se aparecesse o pior caso aqui é texto
       feio, nunca execução: a saída é string dentro de uma resposta MCP.
    """
    if not bruto:
        return ""
    com_quebra = _QUEBRAS.sub("\n", bruto)
    sem_tag = _TAGS.sub("", com_quebra)
    legivel = _html.unescape(sem_tag)
    # `\xa0` (nbsp) sobrevive ao unescape e imprime como espaço que não quebra
    # linha — invisível no diff e visível na conta de bytes.
    legivel = legivel.replace("\xa0", " ")
    legivel = _ESPACOS.sub(" ", legivel)
    return _LINHAS_VAZIAS.sub("\n", "\n".join(
        linha.strip() for linha in legivel.splitlines()
    )).strip()


# Uma âncora com `href`, aspas duplas ou simples, e o que houver até o fecho.
# `[^>]*?` antes do `href` não atravessa `>`, então `<a name="x">` sem `href`
# não casa com o `href` da âncora seguinte.
_ANCORAS = re.compile(
    r"""(?is)<a\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')[^>]*>(.*?)</a\s*>"""
)


def links(bruto: str) -> list[tuple[str, str]]:
    """(endereço, título) de cada `<a href>` do HTML, na ordem em que aparecem.

    O endereço passa por `unescape` porque o Moodle grava `&amp;` no `href` e a
    URL com `&amp;` literal não é a URL que o professor colou. O título passa por
    `sem_html`, que já resolve entidade e marcação — `um <b>dois</b>` vira
    `um dois`. Âncora sem `href` (`<a name=…>`) não é link e fica de fora. `src`
    de imagem também: imagem não é link, e é `href` que o professor clica.

    Mesma ressalva de `sem_html`: isto não interpreta HTML, extrai de um texto
    que o filtro do Moodle já limpou. Quem classifica o que é material e o que é
    ruído é quem chama — aqui só se separa endereço de título.
    """
    if not bruto or "href" not in bruto.lower():
        return []
    achados: list[tuple[str, str]] = []
    for m in _ANCORAS.finditer(bruto):
        endereco = m.group(1) if m.group(1) is not None else (m.group(2) or "")
        endereco = _html.unescape(endereco).strip()
        if endereco:
            achados.append((endereco, sem_html(m.group(3))))
    return achados


def normalizar(s: str) -> str:
    """"psi 3323" → "PSI3323"; "Eletrônica" → "ELETRONICA".

    O `NFD` é o que faz isso funcionar e não é decoração: ele separa "ô" em "o"
    mais a marca combinante, e aí o filtro descarta só a marca. Sem ele o filtro
    descartava o "ô" inteiro, "Eletrônica" virava "ELETRNICA", e deixava de casar
    com "eletronica". T83 fica vermelho se alguém o remover por parecer supérfluo.
    """
    decomposto = unicodedata.normalize("NFD", s or "")
    return re.sub(r"[^A-Z0-9]", "", decomposto.upper())


def casa(termo: str, alvo: str) -> bool:
    """Substring, sem acento, sem caixa, sem pontuação. Termo vazio casa com tudo.

    Termo vazio casando com tudo é o que faz `material` sem `busca` continuar
    listando o espaço inteiro — não é permissividade acidental.
    """
    return normalizar(termo) in normalizar(alvo)
