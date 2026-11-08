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

END_X = ('End of Quarter', 'End of Half', 'End of Game', 'End of Regulation')
def _sec(t):
    try: m, s_ = str(t).split(':'); return int(m) * 60 + int(s_)
    except Exception: return None
def infer_missing_endings(gk, ch):
    """Drives labeled 'End of Quarter/Half/Game' with time still on the clock, followed by the OTHER team's drive in the same
    quarter: the feed is missing the drive-ending play (usually a punt or a failed 4th down). Infer it from where the other team
    took over (Nov 8 2026): turnover on downs if the ball changed hands at the spot after a 4th-down snap; missed FG if the other
    team started near the spot of the kick; punt if it started well downfield; otherwise leave it. Scores are never touched
    (a drive whose team scored is skipped)."""
    for i, d in enumerate(ch[:-1]):
        nx = ch[i + 1]
        if d['result'] not in END_X or (_sec(d.get('t2')) or 0) <= 30 or nx['team'] == d['team'] or nx['q1'] != d['q2']: continue
        if d.get('spot2') is None or nx.get('spot1') is None: continue
        if (nx.get('oppScore') or 0) != (d.get('teamScore') or 0): continue
        at = 100 - d['spot2']                       # where the other team would take over at the spot (its own yard line)
        last = next((q for q in reversed(d['playList']) if q.get('down')), None)
        if last and last.get('down') == 4 and abs(at - nx['spot1']) <= 10: r, h, c = 'Turnover on Downs', 'DOWNS', 'red'
        elif d['spot2'] >= 62 and abs(at + 7 - nx['spot1']) <= 8: r, h, c = 'Missed FG', 'MISS', 'red'
        elif nx['spot1'] <= at - 15: r, h, c = 'Punt', 'PUNT', 'gray'
        else: continue
        d.update({'result': r, 'color': c})
        d['playList'].append({'q': d['q2'], 'text': f"{r} (the drive-ending play is missing from the play-by-play feed; inferred from where {nx['team']} took over)",
                              'scoring': False, 'penalty': False, 'down': None, 'distance': None, 'goalToGo': False, 'yardline100': None})
        if nx.get('how') in ('KO', None): nx['how'] = h

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
    elif gk == '1_401858212':    # FSU - SMU: SMU's fumbled punt return is now its own entry (box and chart agree);
        for n in (1, 24):        # + lost fumbles the feed typed as plain runs (flag_overrides.json, Oct 25)
            x = get(ch, n)
            if x['result'] in ('End of Quarter', 'End of Game'):
                x.update({'result': 'Fumble', 'color': 'red'})
                nx = next((y for y in ch if y['n'] == n + 1), None)
                if nx is not None and nx['team'] != x['team']: nx['how'] = 'FUMB'
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
    # ---- lost fumbles the feed typed as own recoveries (flag_overrides.json, Oct 25): drive ends in a Fumble ----
    elif gk in ('1_401856667', '2_401856787'):
        for n in {'1_401856667': (12,), '2_401856787': (3,)}[gk]:
            x = get(ch, n)
            if x['result'] in ('End of Quarter', 'End of Game'):
                x.update({'result': 'Fumble', 'color': 'red'})
                nx = next((y for y in ch if y['n'] == n + 1), None)
                if nx is not None and nx['team'] != x['team']: nx['how'] = 'FUMB'
    # ---------------- Week 8 (scores come from score_overrides.json; these fix the drive labels) ----------------
    elif gk == '8_401856727':    # Texas A&M - Alabama: TAMU's 1st drive ended in D.Lee's pick-six (PAT text has a false start)
        x = get(ch, 2)
        if x['team'] == 'Texas A&M' and x['result'] == 'Touchdown' and x['oppScore'] == 7: x['result'] = 'Interception (Pick-6)'
    elif gk == '8_401861965':    # UMass - UConn: UMass punt blocked by S.Porter, recovered by UConn in the end zone (21-3 -> 28-3)
        x = get(ch, 18)
        if x['team'] == 'Massachusetts' and x['result'] == 'Punt' and x['oppScore'] == 28:
            x.update({'result': 'Blocked Punt (TD)', 'color': 'blue', 'scored': True})
    elif gk == '8_401871094':    # ULM - Troy: Troy's last play, a multi-lateral, fumbled at the goal line and recovered by ULM for the winning TD
        x = get(ch, 27)
        if x['team'] == 'Troy' and x['result'] == 'Touchdown':
            x['playList'].sort(key=lambda p: -(clk(p) or 0))
            x.update({'result': 'Fumble (Defensive TD)', 't2': '0:00', 'playText': x['playList'][-1]['text']})
    elif gk == '8_401866450':    # WMU - Toledo: J.Franklin's 92-yd return of the 2nd-half kickoff is missing from the feed
        a, t = get(ch, 16), get(ch, 17)   # (WMU recap; only the PAT row survives). Toledo kicked off; WMU then kicked off at 14:47.
        if a['result'] == 'End of Half' and t['team'] == 'Toledo' and t['result'] != 'Kickoff (Return TD)' and t['oppScore'] == 21 and a['teamScore'] == 14:
            txt = ('Kickoff returned 92 yards for a TOUCHDOWN by J.Franklin (WMU) - play missing from the data feed, '
                   'per WMU recap. #32 D.Kelly kick attempt good (H: #25 R.Millmore, LS: #46 D.Doyle)')
            kr = {'team': 'Toledo', 'opponent': 'Western Michigan', 'q1': 3, 't1': '15:00', 'spot1': 35.0, 'q2': 3, 't2': '14:47',
                  'spot2': 35, 'plays': 1, 'yards': 0, 'top': '0:13', 'result': 'Kickoff (Return TD)', 'color': 'blue',
                  'clickable': True, 'opp30': False, 'playText': txt, 'teamScore': 31, 'oppScore': 21, 'scored': True, 'how': 'KO',
                  'playList': [{'q': 3, 'text': txt, 'scoring': True, 'penalty': False, 'down': None, 'distance': None,
                                'goalToGo': False, 'yardline100': None}]}
            ch.insert(ch.index(a) + 1, kr)
    # ---------------- Week 9 ----------------
    elif gk == '9_401858278':    # SMU - Syracuse: Syracuse's 4th-qtr drive ended in an intentional-grounding safety (20-17 -> 20-19), not a TD
        x = get(ch, 18)
        if x['team'] == 'Syracuse' and x['result'] == 'Touchdown' and 'SAFETY' in x['playText']: x.update({'result': 'Safety', 'color': 'red'})
    elif gk == '9_401858281':    # Pitt - GT: GT's one-play fumble drive came after Pitt's 0:08 FG in the 3rd (feed tagged it 15:00)
        x = get(ch, 24)
        if x['team'] == 'Georgia Tech' and x['t1'] == '15:00': x['t1'] = '0:08'
    elif gk == '9_401858507':    # Michigan - Rutgers: Rutgers' punt-return fumble was wiped out by Michigan kick-catch interference
        x = get(ch, 15)
        if x['team'] == 'Michigan' and x['result'] == 'Fumble':
            x.update({'result': 'Punt', 'color': 'gray'}); nx = get(ch, 16)
            if nx['team'] == 'Rutgers' and nx['how'] == 'FUMB': nx['how'] = 'PUNT'
    elif gk in ('9_401862816', '9_401871071'):    # UAB / WKU opening drives: feed lists a later play first; start = first snap
        x = get(ch, 1)
        x['playList'].sort(key=lambda p: -(clk(p) or 0))
        y0 = x['playList'][0].get('yardline100')
        if y0 is not None: x['spot1'] = float(100 - y0)
    elif gk == '10_401858513':   # Iowa - Northwestern: Iowa's 96-yd kickoff-return TD after NU's 3rd-qtr FG (feed logged it in NU's possession)
        a = get(ch, 14)
        if a['team'] == 'Northwestern' and a['result'] == 'Field Goal' and get(ch, 15)['result'] != 'Kickoff (Return TD)':
            kt = '(04:14) #92 N.Dugandzic kickoff 61 yards to the UoI04 #22 B.Jackson return 96 yards to the NU 00 TOUCHDOWN, clock 04:03 #92 C.Buhr kick attempt good'
            ch.insert(14, {'team': 'Northwestern', 'opponent': 'Iowa', 'q1': 3, 't1': '4:14', 'spot1': 35.0, 'q2': 3, 't2': '4:03', 'spot2': 35, 'plays': 1,
                           'yards': 0, 'top': '0:00', 'result': 'Kickoff (Return TD)', 'color': 'blue', 'clickable': True, 'opp30': False, 'playText': kt,
                           'teamScore': 3, 'oppScore': 21, 'scored': True, 'n': 0, 'how': 'KO',
                           'playList': [{'q': 3, 'text': kt, 'scoring': True, 'penalty': False, 'down': None, 'distance': None, 'goalToGo': False, 'yardline100': None}]})
    elif gk == '10_401866454':   # Miami (OH) - Buffalo: Buffalo's 3rd-qtr punt was blocked and recovered in the end zone by Miami (TD)
        x = get(ch, 13)
        if x['team'] == 'Buffalo' and x['result'] == 'Punt' and 'blocked' in x['playText']: x.update({'result': 'Blocked Punt (TD)', 'color': 'blue'})
    elif gk == '10_401871076':   # WKU - MTSU: official line score 51-42; MTSU's 6-pt TD on the final play is not in the feed (feed ends 45-42 at the FG)
        x = get(ch, 26)
        if x['team'] == 'Middle Tennessee' and x['result'] == 'Field Goal' and x['teamScore'] == 51:
            x.update({'teamScore': 45, 'oppScore': 42})
            t = 'Final play (missing from the play-by-play feed): Middle Tennessee scored a touchdown on the last snap after its game-winning field goal - official final 51-42 (CFBD line score MTSU 14-7-14-16).'
            ch.insert(26, {'team': 'Western Kentucky', 'opponent': 'Middle Tennessee', 'q1': 4, 't1': '0:01', 'spot1': None, 'q2': 4, 't2': '0:00', 'spot2': None,
                           'plays': 0, 'yards': 0, 'top': '0:00', 'result': 'Defensive TD (final play)', 'color': 'red', 'clickable': True, 'opp30': False,
                           'playText': t, 'teamScore': 42, 'oppScore': 51, 'scored': False, 'n': 0, 'how': 'KO',
                           'playList': [{'q': 4, 'text': t, 'scoring': True, 'penalty': False, 'down': None, 'distance': None, 'goalToGo': False, 'yardline100': None}]})
    elif gk == '10_401858289':   # BC - FSU opening drive: feed lists three later plays first (clock 15:00); start = first snap (BC 25)
        x = get(ch, 1)
        x['playList'].sort(key=lambda p: -(clk(p) if clk(p) else 0))
        y0 = next((p.get('yardline100') for p in x['playList'] if p.get('yardline100') is not None), None)
        if y0 is not None: x['spot1'] = float(100 - y0)
    elif gk == '10_401856852':   # ASU - Colorado: ASU's TD drive began after Colorado's punt at 0:47 of the 1st (feed tagged 4:31)
        x = get(ch, 6)
        if x['team'] == 'Arizona State' and x['t1'] == '4:31': x['t1'] = '0:47'
    elif gk == '10_401871074':   # FIU - Missouri St: Kohl's sack-fumble returned for a Missouri St TD + 2-pt (17-9 -> 17-17); FIU lost fumble flagged by hand
        x = get(ch, 20)
        if x['team'] == 'Florida International' and x['result'] == 'Fumble':
            x.update({'result': 'Fumble (Defensive TD)', 'color': 'red'})
            rerun(ch, {20: (17, 17), 21: (20, 17), 22: (20, 20), 23: (23, 20)})
            nx = get(ch, 21)
            if nx['team'] == 'Florida International' and nx['how'] == 'FUMB': nx['how'] = 'KO'
    elif gk == '10_401858292':   # UConn - UNC: UConn's 4th-down punt from its 42 (UNC downed at its 3) is missing from the feed after the 3:58 incompletion
        x = get(ch, 6)
        if x['team'] == 'UConn' and x['result'] == 'End of Quarter' and x['t2'] == '3:58':
            x.update({'result': 'Punt', 'color': get(ch, 1)['color']})
            x['playList'].append({'q': 1, 'text': 'UConn punt (missing from the play-by-play feed) - North Carolina took over at its own 3 with 3:40 left in the 1st quarter.', 'scoring': False, 'penalty': False, 'down': None, 'distance': None, 'goalToGo': False, 'yardline100': None})
            nx = get(ch, 7)
            if nx['team'] == 'North Carolina' and nx['how'] == 'KO': nx['how'] = 'PUNT'
    infer_missing_endings(gk, ch)
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
