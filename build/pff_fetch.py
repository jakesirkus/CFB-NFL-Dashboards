"""Download PFF weekly data for the OL/DL stats into build/pff/raw/{lg}/ (git-ignored cache; key from ~/.secrets/pff_key or
/home/claude/.secrets/pff_key or $PFF_KEY - never commit it).  Per week: games list + player facets
offense/pass_blocking, offense/run_blocking, defense/pass_rush, defense/run (league-wide, filtered to that week).
usage: pff_fetch.py nfl|cfb SEASON WEEK [WEEK ...]   (re-downloads the weeks given; cheap: 5 calls per week)"""
import sys, os, json, time, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
LG, SEASON = sys.argv[1], sys.argv[2]; WEEKS = sys.argv[3:]
PL = {'nfl': 'nfl', 'cfb': 'ncaa'}[LG]
KEY = os.environ.get('PFF_KEY') or next(open(p).read().strip() for p in ('/home/claude/.secrets/pff_key', os.path.expanduser('~/.secrets/pff_key')) if os.path.exists(p))
OUT = os.path.join(HERE, 'pff', 'raw', LG); os.makedirs(OUT, exist_ok=True)
FACETS = {'pass_blocking': '/v1/facet/offense/pass_blocking', 'run_blocking': '/v1/facet/offense/run_blocking',
          'pass_rush': '/v1/facet/defense/pass_rush', 'run_defense': '/v1/facet/defense/run', 'games': '/v1/games'}
def get(path, **q):
    url = 'https://api.pff.com' + path + '?' + urllib.parse.urlencode(q)
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + KEY, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)
        except Exception as e:
            if i == 3: raise
            print('  retry', path, e); time.sleep(3 * (i + 1))
for w in WEEKS:
    for name, path in FACETS.items():
        d = get(path, league=PL, season=SEASON, week=w)
        rows = next(v for v in d.values() if isinstance(v, list))
        json.dump(rows, open(os.path.join(OUT, f'w{w}_{name}.json'), 'w'))
        print(f'{LG} week {w} {name}: {len(rows)} rows')
