"""Turnover flags that don't trust the feed's play-type label alone.
The feed often tags a LOST fumble as 'Fumble Recovery (Own)' (and sometimes as a pass/rush/
'Uncategorized'), including scoop-and-score touchdowns. We read who recovered from the play
text and cross-check it against who had the ball next."""
import re, pandas as pd, numpy as np
from penalties import learn_abbr_map
REC=re.compile(r'recovered by\s+([A-Za-z&\.\'\-]+)')
KICK={'Kickoff','Punt','Punt Return','Kickoff Return (Offense)','Field Goal Missed','Blocked Punt','Blocked Field Goal','Punt Return Touchdown','Kickoff Return Touchdown','Blocked Punt Touchdown','Blocked Field Goal Touchdown'}
INT_T={'Interception','Pass Interception Return','Interception Return Touchdown'}
def flag_game(g):
    g=g.copy(); amap=learn_abbr_map(g,None,None)
    snaps=g[g.is_scrim].sort_values(['DriveNumber','Period','clock','Id'],ascending=[True,True,False,True])
    dn_off={}
    for dn,grp in snaps.groupby('DriveNumber'): dn_off[dn]=grp.Offense.mode().iloc[0]
    dns=sorted(dn_off)
    lost=np.zeros(len(g),bool); ftd=np.zeros(len(g),bool); itd=np.zeros(len(g),bool); intr=np.zeros(len(g),bool); st=np.zeros(len(g),bool)
    keys_=[None]*len(g)
    for k,(ix,r) in enumerate(g.iterrows()):
        t=str(r.PlayText); tl=t.lower()
        if 'no play' in tl: continue
        # the feed sometimes logs the same play twice (once typed 'Penalty'); count it once
        keys_[k]=(r.Period, re.sub(r'\s+',' ',tl.split('penalty')[0])[:80]) if ('intercept' in tl or 'fumbl' in tl) else None
        # kick rows only; a scrimmage TD row whose text runs on into the next kickoff is NOT a kick play
        if r.PlayType in KICK or ((not r.is_rp) and ('kickoff' in tl or re.search(r'\bpunt(s|ed)?\b', tl))):
            # special teams: returner fumbles/muffs and the KICKING team (row Offense) recovers -> receiving team's giveaway
            if ('fumble' in tl or 'muff' in tl) and not re.search(r'call overturned|is reversed', tl):
                recs=REC.findall(t)
                if recs and amap.get(recs[-1])==r.Offense: st[k]=True
            continue
        if re.search(r'call overturned|ruling .{0,40}reversed|is reversed', tl) and re.search(r'fumble|intercept', tl): continue   # turnover wiped out on review
        td=('touchdown' in tl) or ('for a td' in tl)
        if r.PlayType in INT_T or ('intercepted' in tl):
            intr[k]=True; itd[k]= r.PlayType=='Interception Return Touchdown' or (td and 'intercepted' in tl)
            # the interceptor fumbles on the return and the passing team gets it back: a giveaway for each side
            back=REC.findall(t.split('intercepted',1)[-1]) if 'fumbl' in tl.split('intercepted',1)[-1] else []
            if back and amap.get(back[-1])==r.Offense: st[k]=True
            continue
        if 'fumbl' not in tl: continue          # the play type alone isn't enough (2-pt tries get typed as fumble recoveries)
        # a fumble on the extra-point / 2-pt return isn't a turnover of the scrimmage play
        pre=re.split(r'kick attempt|two[- ]point|pass attempt|rush attempt', tl)[0]
        if 'fumbl' not in pre: continue
        recs=REC.findall(t); T=None
        if recs:
            tm=amap.get(recs[-1]); T=('lost' if tm==r.Defense else 'own') if tm else None
        else:
            m=re.search(r'recovered by ([A-Z][A-Za-z\.\' &\(\)]+)', t)
            if m:
                if m.group(1).startswith(r.Defense): T='lost'
                elif m.group(1).startswith(r.Offense): T='own'
        later=[d for d in dns if d>r.DriveNumber]
        P=None if not later else ('changed' if dn_off[later[0]]!=r.Offense else 'same')
        L='opp' if r.PlayType in ('Fumble Recovery (Opponent)','Fumble Return Touchdown') else 'other'
        # double turnover: the defense recovers, then fumbles it back to the offense -> a giveaway for each side
        if len(recs)>=2 and amap.get(recs[0])==r.Defense and amap.get(recs[-1])==r.Offense:
            lost[k]=True; st[k]=True; continue
        if T=='lost': is_lost = (P!='same') or L=='opp' or td
        elif T=='own': is_lost = (L=='opp' and P=='changed') and not td      # own recovery in the end zone is a TD, not a turnover
        else: is_lost = (L=='opp')
        if is_lost:
            lost[k]=True; ftd[k]= td or r.PlayType=='Fumble Return Touchdown'
    # the feed sometimes logs the same play twice (once typed 'Penalty'): keep one flag per play
    seen=set()
    for k in range(len(g)):
        if keys_[k] is None or not (lost[k] or intr[k] or st[k]): continue
        if keys_[k] in seen: lost[k]=intr[k]=st[k]=ftd[k]=itd[k]=False
        else: seen.add(keys_[k])
    g['fum_lost']=lost; g['fum_td']=ftd; g['int']=intr; g['int_td']=itd; g['st_lost']=st
    g['giveaway']=g['int']|g['fum_lost']
    return g
