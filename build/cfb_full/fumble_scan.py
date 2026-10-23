import re, sys, json, pandas as pd; sys.path.insert(0,'.')
from penalties import learn_abbr_map
from multiprocessing import Pool
df=pd.read_pickle('prepped.pkl')
REC=re.compile(r'recovered by\s+([A-Za-z&\.\'\-]+)')
KICK={'Kickoff','Punt','Punt Return','Kickoff Return (Offense)','Field Goal Missed','Blocked Punt','Blocked Field Goal'}
def work(item):
    gid,g=item; amap=learn_abbr_map(g,None,None); out=[]
    for _,r in g.iterrows():
        t=str(r.PlayText); tl=t.lower()
        if 'fumble' not in tl or 'no play' in tl: continue
        recs=REC.findall(t)
        if not recs: 
            # ESPN-style text: "... fumbled, recovered by <Team Name> <player>"
            m=re.search(r'recovered by ([A-Z][A-Za-z\.\' &]+?)(?: [A-Z]\.|,| at | for |$)', t)
            team=None
            if m:
                for tm in (r.Offense, r.Defense):
                    if m.group(1).startswith(tm) or tm.startswith(m.group(1)): team=tm
        else:
            team=amap.get(recs[-1])
        lost = team is not None and team==r.Defense
        td = 'touchdown' in tl or 'for a td' in tl
        out.append(dict(GameId=gid, Id=r.Id, PlayType=r.PlayType, kick=r.PlayType in KICK, lost=lost, rec_team=team, td=td, text=t[:160]))
    return out
if __name__=='__main__':
    with Pool(2) as p: res=[x for y in p.map(work, list(df.groupby('GameId')), chunksize=8) for x in y]
    f=pd.DataFrame(res); f.to_pickle('fumble_scan.pkl')
    s=f[~f.kick]
    print('scrimmage fumble rows:',len(s),'| recovering team unresolved:',int(s.rec_team.isna().sum()))
    lost=s[s.lost]
    print('\\nLOST fumbles by how the feed labels them:'); print(lost.PlayType.value_counts().to_string())
    print('\\nfumble-return TDs by the defense, by feed label:'); print(lost[lost.td].PlayType.value_counts().to_string())
    print('\\nlost fumbles the current turnover counter would MISS:', int((~lost.PlayType.isin(['Fumble Recovery (Opponent)','Fumble Return Touchdown'])).sum()), 'of', len(lost))
    own=s[(~s.lost)&s.rec_team.notna()]
    print('rows labeled as LOST but text says offense recovered:', int(own.PlayType.isin(['Fumble Recovery (Opponent)','Fumble Return Touchdown']).sum()))
