import re, numpy as np, pandas as pd
from collections import Counter, defaultdict

ABBR_RE = re.compile(r'PENALTY\s+(?P<abbr>[A-Za-z&\.\'\-]+(?:\s[A-Z][A-Za-z]*)?)\s+(?P<body>.*?)(?=PENALTY\s|$)', re.S)
ESPN_RE = re.compile(r'(?P<team>[A-Z][A-Za-z&\.\'\(\) \-]+?) Penalty, (?P<body>.*?)(?=(?:[A-Z][A-Za-z&\.\'\(\) \-]+? Penalty, )|$)', re.S)
SPOT_RE = re.compile(r'from\s+([A-Za-z&\.\'\-]+?)\s?(\d{1,2})\b')

def learn_abbr_map(g, home, away):
    """Per game: map spot/penalty abbreviations -> team, using the line-of-scrimmage spot in
    'from XXnn' vs the row's YardsToGoal. nn == YardsToGoal -> XX is the defense's side."""
    votes = defaultdict(Counter)
    for _, r in g.iterrows():
        txt = str(r.PlayText)
        if pd.isna(r.YardsToGoal): continue
        for m in SPOT_RE.finditer(txt):
            pre, n = m.group(1), int(m.group(2))
            if n == 50: continue
            if n == r.YardsToGoal: votes[pre][r.Defense] += 1
            elif 100 - n == r.YardsToGoal: votes[pre][r.Offense] += 1
    return {k: v.most_common(1)[0][0] for k, v in votes.items()}

def parse_penalties(g, home, away):
    """Returns list of penalty events: dict(row_idx, team, side ('off'/'def'/None), yards, fd(bool), text)."""
    amap = learn_abbr_map(g, home, away)
    out = []
    for idx, r in g.iterrows():
        txt = str(r.PlayText)
        if 'enalty' not in txt and 'PENALTY' not in txt: continue
        evs = []
        if 'PENALTY' in txt:
            for m in ABBR_RE.finditer(txt):
                body = m.group('body'); abbr = m.group('abbr').split()[0]
                if re.search(r'declined|offsetting', body, re.I): continue
                team = amap.get(abbr)
                if team is None:
                    # fall back 1: abbreviation is a prefix of a team name
                    for tm in (home, away):
                        if tm.lower().replace(' ','').startswith(abbr.lower()): team = tm
                if team is None:
                    # fall back 2: if every learned abbreviation belongs to one team, an unknown one is the other team
                    known = set(amap.values())
                    if len(known) == 1:
                        team = away if home in known else home
                ym = re.search(r'(\d+)\s+yards?', body, re.I)
                yds = int(ym.group(1)) if ym else None
                fd = bool(re.search(r'1ST DOWN', body, re.I))
                evs.append((team, yds, fd, body[:80]))
        else:
            for m in ESPN_RE.finditer(txt):
                team = m.group('team').strip()
                # strip leading play text (team name is the trailing words that match home/away)
                tm = next((t for t in (home, away) if team.endswith(t)), None)
                body = m.group('body')
                if re.search(r'declined|offsetting', body, re.I): continue
                ym = re.search(r'\((-?\d+)\s+Yards?\)', body, re.I)
                yds = abs(int(ym.group(1))) if ym else (abs(int(r.YardsGained)) if r.PlayType == 'Penalty' and pd.notna(r.YardsGained) else None)
                fd = bool(re.search(r'1ST down', body, re.I))
                evs.append((tm, yds, fd, body[:80]))
        for team, yds, fd, body in evs:
            side = 'off' if team == r.Offense else ('def' if team == r.Defense else None)
            if fd and side == 'off': fd = False
            out.append(dict(idx=idx, team=team, side=side, yards=yds, fd=fd and side == 'def', body=body))
    return out
