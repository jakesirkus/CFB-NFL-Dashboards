"""Hand-verified drive-chart corrections for games where the play-by-play feed itself is broken
(missing PAT text, jumbled clocks, duplicated plays). Each fix was checked against the feed's own
running score / next-possession spot. Applied last, after polish_charts.
usage: chart_overrides.py OUT"""
import sys, json, glob, copy, re
OUT = sys.argv[1]

def clk(p):
    m = re.match(r'\((\d{1,2}):(\d{2})\)', p['text'])
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None

def scores(ch, pairs):
    """pairs: {n: (teamScore, oppScore)}"""
    for x in ch:
        if x['n'] in pairs: x['teamScore'], x['oppScore'] = pairs[x['n']]

def rerun(ch, pairs):
    """set the scores of the listed drives and carry the running score through every other drive"""
    cur = {}; first = min(pairs)
    for x in ch:
        t, o = x['team'], x['opponent']
        if x.get('teamScore') is None: continue
        if x['n'] < first: cur[t], cur[o] = x['teamScore'], x['oppScore']; continue
        if x['n'] in pairs: cur[t], cur[o] = pairs[x['n']]
        x['teamScore'], x['oppScore'] = cur.get(t, 0), cur.get(o, 0)

def get(ch, n): return next(x for x in ch if x['n'] == n)

def renum(ch):
    for i, x in enumerate(ch): x['n'] = i + 1
    return ch

def fix(gk, ch):
    ch = copy.deepcopy(ch)
    if gk == '1_401856668':      # Texas A&M - Missouri State: punt-return fumble out the back = TAMU safety (7-0 -> 9-0)
        x = get(ch, 6)
        if x['result'] == 'Safety': x['teamScore'] = 9; x['oppScore'] = 0; x['color'] = 'blue'; x['scored'] = True
    elif gk == '1_401862694':    # Charlotte - Citadel: Charlotte's 3rd-qtr PAT is missing from the text (feed score 21-14)
        if get(ch, 15)['teamScore'] == 20:
            rerun(ch, {15: (21, 14), 16: (21, 21), 18: (28, 21), 21: (28, 28), 23: (35, 28), 24: (35, 35), 25: (41, 35), 26: (41, 41), 27: (43, 41)})
    elif gk == '2_401864505':    # UTEP: completion fumbled at the 2, recovered by UTEP in the end zone = TD (21-10 -> 28-10)
        x = get(ch, 12)
        if x['result'] == 'Fumble': x['result'] = 'Touchdown'; x['color'] = 'blue'; x['scored'] = True
    elif gk == '4_401867909':    # FIU: own fumble recovered in the end zone = TD
        x = get(ch, 5)
        if x['result'] == 'Fumble': x['result'] = 'Touchdown'; x['color'] = 'blue'; x['scored'] = True
    elif gk == '2_401858221':    # ODU - VT: the garbled duplicate sack line + the real sack/scoop-and-score are one ODU drive
        a, b = get(ch, 4), get(ch, 5)
        if a['team'] == b['team'] == 'Old Dominion' and b['result'] == 'Fumble (Defensive TD)':
            m = copy.deepcopy(b)
            m.update({k: a[k] for k in ('how', 'q1', 't1', 'spot1')})
            m['playList'] = [a['playList'][0]] + b['playList']; m['plays'] = 2; m['yards'] = 21 - 6; m['spot2'] = 14
            ch = [x for x in ch if x['n'] not in (4, 5)]
            ch.insert(3, m)
    elif gk == '1_401866411':    # Sac State: first play logged twice (9 and 8 yds from the 2); drive = 98 yds from the SAC2
        x = get(ch, 21)
        if x['yards'] == 107:
            x['playList'] = x['playList'][1:]; x['plays'] = 8; x['yards'] = 98; x['spot1'] = 2.0
    elif gk == '3_401860889':    # Texas State: 1+0+11+1+57 = 70 play yards
        x = get(ch, 19)
        if x['yards'] == 118: x['yards'] = 70
    elif gk == '5_401858252':    # UConn: 5+0+7-13+0+2 = 1 yd, punted from the 8
        x = get(ch, 7)
        if x['yards'] == 99: x['yards'] = 1; x['spot2'] = 8
    elif gk == '5_401860899':    # Oregon State's last drive is logged twice; Colorado State's punt drive starts at its 25
        a, b = get(ch, 20), get(ch, 21)
        if a['team'] == b['team'] == 'Oregon State' and a['spot1'] is None:
            ch = [x for x in ch if x['n'] != 20]
            c = get(ch, 19)
            if c['spot1'] is None: c['spot1'] = 25.0; c['spot2'] = 37
            for p in c['playList']:
                if p['yardline100'] == 0: p['yardline100'] = None
    elif gk == '1_401858209':    # Duke - Tulane: feed clocks jumbled in the 3rd quarter
        t14, d15, t16 = get(ch, 14), get(ch, 15), get(ch, 16)
        if d15['result'] == 'End of Quarter':
            mv = [p for p in t14['playList'] if p['text'].startswith('(04:46)')]
            t14['playList'] = [p for p in t14['playList'] if not p['text'].startswith('(04:46)')]
            t14['playList'].sort(key=lambda p: -(clk(p) or 0))
            t14.update({'plays': t14['plays'] - 1, 'yards': t14['yards'] - 6, 't2': '7:02', 'playText': next(p['text'] for p in t14['playList'] if 'punt' in p['text'])})
            pl = d15['playList']; d15['playList'] = [pl[-1]] + pl[:-1]
            d15.update({'t1': '7:02', 'spot1': 50.0, 't2': '4:57', 'spot2': 82, 'q2': 3, 'result': 'Turnover on Downs', 'color': 'red',
                        'playText': d15['playList'][-1]['text']})
            t16['playList'] = sorted(t16['playList'] + mv, key=lambda p: -(clk(p) or 0))
            t16.update({'how': 'DOWNS', 't1': '4:57', 'spot1': 18.0, 'plays': t16['plays'] + 1, 'yards': t16['yards'] + 6})
    elif gk == '1_401858212':    # FSU - SMU: SMU's fumbled punt return is now its own entry (box and chart agree)
        pass
    elif gk == '2_401866414':    # Buffalo - FIU: feed clocks wrong after FIU's 3:37 TD
        b5, f6, b7 = get(ch, 5), get(ch, 6), get(ch, 7)
        if f6['result'] == 'End of Quarter':
            b5.update({'t1': '3:37', 't2': '2:23'})
            pl = f6['playList']; f6['playList'] = [pl[3], pl[0], pl[1], pl[2]]
            f6.update({'t1': '2:23', 'q2': 1, 't2': '1:45', 'spot1': 70.0, 'spot2': 79, 'result': 'Turnover on Downs', 'color': 'red',
                       'playText': f6['playList'][-1]['text']})
            pl = b7['playList']; b7['playList'] = [pl[1], pl[2], pl[0], pl[3]]
            for p in b7['playList'][:2]: p['q'] = 1
            b7.update({'q1': 1, 't1': '1:45', 'how': 'DOWNS', 'spot1': 21.0})
    elif gk == '2_401868326':    # Troy - Alabama State: ASU's 5:00 drive ended on downs at 0:42 (feed tagged it 15:00)
        a, t = get(ch, 19), get(ch, 20)
        if a['result'] == 'End of Quarter':
            pl = [p for p in a['playList'] if not p['text'].startswith('(15:00)')]
            a['playList'] = sorted(pl, key=lambda p: -(clk(p) or 0))
            a.update({'t1': '5:00', 'spot1': 25.0, 't2': '0:42', 'spot2': 72, 'result': 'Turnover on Downs', 'color': 'red',
                      'plays': sum(1 for p in a['playList'] if 'punt' not in p['text']), 'yards': 42,
                      'playText': a['playList'][-1]['text']})
            t.update({'how': 'DOWNS', 't1': '0:42'})
    elif gk == '5_401869842':    # Army - La Tech: La Tech's turnover-on-downs drive came before Army's 1:20 drive
        a, l = get(ch, 3), get(ch, 4)
        if a['team'] == 'Army' and l['result'] == 'Turnover on Downs':
            l.update({'t1': '1:20', 't2': '1:20'}); a.update({'how': 'DOWNS'})
            get(ch, 5).update({'how': 'PUNT'})
            ch[2], ch[3] = l, a
    return renum(ch)

if __name__ == '__main__':
    n = 0
    for f in glob.glob(OUT + '/drivecharts/*.json'):
        d = json.load(open(f)); ch_ = False
        for gk in list(d):
            try: new = fix(gk, d[gk])
            except StopIteration: continue       # already applied (entries merged / renumbered)
            if new != d[gk]: d[gk] = new; ch_ = True; n += 1
        if ch_: json.dump(d, open(f, 'w'), separators=(',', ':'))
    print('charts corrected', n)
