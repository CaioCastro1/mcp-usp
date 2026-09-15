"""Responde "isto funciona no Moodle da minha faculdade?" com dado, não com fé.

O projeto nasceu contra o e-Disciplinas, mas quase nada do servidor do Moodle é
da USP: as funções da allowlist são Moodle core, o `MOODLE_URL` é configurável, e
`resolver` casa sigla sem formato fixo. O que **não** era possível até aqui era
descobrir isso sem ler o código — nem para outra faculdade, nem para a própria
USP no dia em que a instalação mudar.

`core_webservice_get_site_info` devolve, além do `userid` que `disciplinas` já
usa, a lista de **todas as funções que o token alcança** (447 no e-Disciplinas em
14/09/2026). Confrontar essa lista com o que cada ferramenta precisa transforma
"deve funcionar" em "funciona, e estas são as que faltam".

Uma chamada, a mesma que a resolução de disciplina já faz. Não é de graça — é
barata, e o custo está declarado na descrição que o modelo lê.

**Isto é o segundo passo, não o primeiro.** `scripts/compatibilidade.sh` responde
antes e **sem credencial nenhuma** se o site é um Moodle com o serviço mobile
ligado — a `notas/portabilidade-moodle.md` mediu 17 instituições assim, e achou
uma (Monash) com o serviço desligado, onde nada aqui funciona e não há o que
consertar do nosso lado. A mesma nota diz, com todas as letras, que verde lá
**não promete que as ferramentas respondem bem**: é exatamente essa distância que
este módulo cobre, e ele só pode cobri-la porque tem token. Quem não tem token
ainda não chegou aqui — usa o script.
"""
from __future__ import annotations

from . import politica

# O que cada ferramenta exposta por este servidor precisa que o site tenha.
#
# Escrito à mão, e não derivado da allowlist inteira, porque a pergunta é POR
# FERRAMENTA: um site sem `mod_assign_get_assignments` ainda responde
# `o_que_vence`, e dizer "não funciona" seria mentir sobre duas das três. O teste
# D4 trava a união disto contra a allowlist, que é o que impede a tabela de
# envelhecer calada quando uma função nova entrar.
FUNCOES_POR_FERRAMENTA: dict[str, tuple[str, ...]] = {
    "o_que_vence": ("core_calendar_get_action_events_by_timesort",),
    "material": (
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "core_course_get_contents",
        "mod_assign_get_assignments",
    ),
    "baixar_arquivo": (
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "core_course_get_contents",
        "mod_assign_get_assignments",
    ),
}


def funcoes_do_site(info) -> frozenset[str]:
    """Os nomes de função que o token alcança, a partir do `site_info`.

    Forma inesperada devolve conjunto VAZIO em vez de levantar: o diagnóstico
    existe justamente para o caso em que o site não é o esperado, e explodir
    aqui trocaria a resposta útil ("este site não expôs a lista") por um
    traceback. Quem decide o que isso significa é `formatar`, que diz em voz
    alta que não conseguiu ler — nunca finge que a lista veio vazia de verdade.
    """
    if not isinstance(info, dict):
        return frozenset()
    cruas = info.get("functions")
    if not isinstance(cruas, list):
        return frozenset()
    return frozenset(
        f["name"] for f in cruas if isinstance(f, dict) and isinstance(f.get("name"), str)
    )


def formatar(info, disponiveis: frozenset[str]) -> str:
    linhas = []
    sitename = (info or {}).get("sitename") if isinstance(info, dict) else None
    release = (info or {}).get("release") if isinstance(info, dict) else None
    linhas.append(f"Diagnóstico — {sitename or 'site sem nome declarado'}")
    if release:
        linhas.append(f"Release {release}")

    if not disponiveis:
        # Invariante 6: "não consegui ler" e "o site não tem nada" são coisas
        # diferentes, e confundi-las aqui faria o diagnóstico reprovar um site
        # que está bom.
        linhas.append(
            "\n⚠ Este site não devolveu a lista de funções no `site_info`. Sem "
            "ela não dá para dizer quais ferramentas funcionam aqui — o que NÃO "
            "significa que não funcionam. Tente uma pergunta de verdade: o erro "
            "dela vai ser mais específico do que este aviso."
        )
        return "\n".join(linhas)

    linhas.append(f"O seu token alcança {len(disponiveis)} funções neste site.")
    linhas.append("\nFerramentas deste servidor:")
    for ferramenta, exigidas in FUNCOES_POR_FERRAMENTA.items():
        faltando = sorted(f for f in exigidas if f not in disponiveis)
        if faltando:
            linhas.append(f"  {ferramenta:16} NÃO — faltam: {', '.join(faltando)}")
        else:
            linhas.append(f"  {ferramenta:16} OK")

    vivas = sorted(politica.BLOQUEIO_PERMANENTE & disponiveis)
    if vivas:
        # O número, não a lista: nomear 40 funções perigosas num texto que um
        # modelo lê é dar a ele o vocabulário exato que a política existe para
        # negar. A contagem já diz o que importa.
        linhas.append(
            f"\n⚠ {len(vivas)} das {len(politica.BLOQUEIO_PERMANENTE)} funções do "
            "bloqueio permanente existem neste site e são alcançáveis por este "
            "token. Elas não são chamadas — a lista de permitidas nega por "
            "omissão e o bloqueio permanente nega de novo — e é justamente esse "
            "número que faz as duas camadas valerem a pena."
        )

    return "\n".join(linhas)


def diagnostico(cliente) -> str:
    """Uma chamada, e a resposta para "isto funciona no meu Moodle?"."""
    info = cliente.chamar("core_webservice_get_site_info")
    return formatar(info, funcoes_do_site(info))
