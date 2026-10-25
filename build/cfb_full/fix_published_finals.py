"""Correct the final score of already-published games after a verified final is added to official_finals.json
(and, if needed, score_overrides.json). Regenerates each game's drive chart, refuses unless the ONLY changes
are teamScore/oppScore, then sets the box-score meta (ts/os/result) from official_finals.json.
Run sync_scores.py and add_ppo.py afterwards (game logs, W-L and points-per-opportunity follow the box/chart).
usage: fix_published_finals.py OUT WEEK_GID[,WEEK_GID...]      e.g. out6 3_401864443,4_401864509"""
import sys, json, glob, contextlib, io, pandas as pd
sys.path.insert(0, '.')
from boxscore import game_boxes
OUT, KEYS = sys.argv[1], sys.argv[2].split(',')
OF = json.load(open('official_finals.json'))
df = pd.read_pickle('prepped_to.pkl')
TAG = '<script id="dashboard-data" type="application/json">'
s = open(OUT + '/index.html').read(); a = s.index(TAG) + len(TAG); b = s.index('</script>', a); D = json.loads(s[a:b])
for gk in KEYS:
    gid = gk.split('_')[1]; fin = OF[gid]; g = df[df.GameId == int(gid)]
    with contextlib.redirect_stdout(io.StringIO()): _, _, ch = game_boxes(g, g.Home.iloc[0], g.Away.iloc[0])
    ch = json.loads(json.dumps(ch, default=float))
    f = next(f for f in glob.glob(OUT + '/drivecharts/*.json') if gk in json.load(open(f)))
    sh = json.load(open(f)); old = sh[gk]
    assert len(old) == len(ch), (gk, 'drive count changed')
    for x, y in zip(old, ch):
        bad = [k for k in set(x) | set(y) if x.get(k) != y.get(k) and k not in ('teamScore', 'oppScore')]
        assert not bad, (gk, x['n'], bad)
    last = [x for x in ch if x.get('teamScore') is not None][-1]
    assert {last['team']: last['teamScore'], last['opponent']: last['oppScore']} == fin, (gk, 'chart final != official')
    sh[gk] = ch; json.dump(sh, open(f, 'w'), separators=(',', ':'))
    for t, x in D['boxscores'][gk].items():
        if t == 'driveChart': continue
        o = x['meta']['opp']; x['meta'].update(ts=fin[t], os=fin[o], result='W' if fin[t] > fin[o] else 'L' if fin[t] < fin[o] else 'T')
    print(gk, 'final ->', fin)
js = json.dumps(D, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
open(OUT + '/index.html', 'w').write(s[:a] + js + s[b:])
