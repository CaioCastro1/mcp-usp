#!/usr/bin/env python3
"""Mede quanto de cada resposta é resposta e quanto é transporte.

Não é higienização (§3.3, que é privacidade). É projeção: manter só os campos que
respondem à pergunta da linha do §3.2. O número que sai daqui decide se a Fase 2
pode devolver cru ou tem que resumir no servidor.
"""
import json, os, re, datetime as dt

R = 'fixtures/moodle/raw/'
ATUAIS = {142259,143454,142323,142478,142033,143374,143352,142358,142036,142979}
def kb(n): return f'{n/1024:,.1f} kB'.replace(',', '.')
def tok(n): return f'~{n//4:,}'.replace(',', '.')

def limpa(h):
    """tira HTML e espaço morto de campo de texto livre"""
    if not h: return ''
    t = re.sub(r'<[^>]+>', ' ', h)
    t = re.sub(r'&nbsp;|&#160;', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

linhas = []
def mede(rotulo, origem, projetado):
    a = os.path.getsize(R + origem)
    b = len(json.dumps(projetado, ensure_ascii=False).encode())
    linhas.append((rotulo, a, b))
    return projetado

# --- "o que vence" -----------------------------------------------------------
ev = json.load(open(R + 'action_events.json'))['events']
mede('o que vence (35 eventos)', 'action_events.json', [
    {'quando': dt.datetime.fromtimestamp(e['timesort']).strftime('%d/%m %H:%M'),
     'disciplina': e['course']['shortname'] if e.get('course') else None,
     'o_que': e['name'], 'tipo': e.get('modulename'), 'url': e.get('url')}
    for e in ev])

# --- "minhas disciplinas" ----------------------------------------------------
cur = json.load(open(R + 'users_courses.json'))
mede('minhas disciplinas (10 de 74)', 'users_courses.json', [
    {'id': c['id'], 'codigo': c['shortname'], 'nome': c['fullname'],
     'fim': dt.datetime.fromtimestamp(c['enddate']).strftime('%d/%m/%Y') if c['enddate'] else None}
    for c in cur if c['id'] in ATUAIS])

# --- "o que tem na disciplina / onde está o PDF" -----------------------------
sec = json.load(open(R + 'course_contents_142033.json'))
mat = []
for s in sec:
    for m in s.get('modules', []):
        arqs = [c['fileurl'] for c in m.get('contents', []) if c.get('type') == 'file']
        mat.append({'secao': s['name'], 'item': m['name'], 'tipo': m['modname'],
                    'arquivos': arqs or None})
mede('conteudo de 1 disciplina', 'course_contents_142033.json', mat)

# --- "o que eu tenho que entregar" -------------------------------------------
ass = json.load(open(R + 'assignments_semestre.json'))['courses']
mede('entregas do semestre', 'assignments_semestre.json', [
    {'id': a['id'], 'disciplina': c['shortname'], 'o_que': a['name'],
     'prazo': dt.datetime.fromtimestamp(a['duedate']).strftime('%d/%m/%Y %H:%M') if a['duedate'] else None}
    for c in ass for a in c.get('assignments', [])])

# --- "o professor avisou algo" -----------------------------------------------
dis = json.load(open(R + 'forum_discussions.json'))['discussions']
mede('avisos de 1 forum', 'forum_discussions.json', [
    {'quando': dt.datetime.fromtimestamp(d['created']).strftime('%d/%m/%Y'),
     'titulo': d['name'], 'texto': limpa(d.get('message'))}
    for d in dis])

# --- quem sou eu -------------------------------------------------------------
si = json.load(open(R + 'site_info.json'))
mede('site_info (so o util)', 'site_info.json',
     {'userid': si['userid'], 'sitename': si['sitename'], 'release': si['release']})

print(f"{'':<34}{'cru':>12}{'projetado':>12}{'sobra':>8}{'tokens depois':>15}")
ta = tb = 0
for rot, a, b in linhas:
    ta += a; tb += b
    print(f'{rot:<34}{kb(a):>12}{kb(b):>12}{b/a:>7.1%}{tok(b):>15}')
print('-' * 81)
print(f"{'TOTAL':<34}{kb(ta):>12}{kb(tb):>12}{tb/ta:>7.1%}{tok(tb):>15}")
print(f'\ncru: {tok(ta)} tokens   ->   projetado: {tok(tb)} tokens')
