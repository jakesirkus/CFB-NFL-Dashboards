import sys, json, pandas as pd, collections, contextlib, io; sys.path.insert(0,'.')
from boxscore import score_events
from penalties import learn_abbr_map
from multiprocessing import Pool
df=pd.read_pickle('prepped_to.pkl'); fbs=set(json.load(open('../nfl_rebuild/cfb_team_list.json')))
w7=set(pd.read_csv('../cfb_week7/download_21.csv',usecols=['GameId']).GameId)-{401871054}
def work(gid):
    g=df[df.GameId==gid].copy(); g['_oc']=-g['clock']; order=g.sort_values(['DriveNumber','Period','_oc','Id'])
    h,a=g.Home.iloc[0],g.Away.iloc[0]
    with contextlib.redirect_stdout(io.StringIO()): ev=score_events(order, learn_abbr_map(g,None,None))
    t=collections.Counter(); [t.update({e[1]:e[2]}) for e in ev if e[1] is not None]
    tim=g[g.OffenseScore.notna()&g.DefenseScore.notna()].sort_values(['Period','_oc','Id'])
    mx={h:0,a:0}
    for r in tim.itertuples(): mx[r.Offense]=max(mx.get(r.Offense,0),int(r.OffenseScore)); mx[r.Defense]=max(mx.get(r.Defense,0),int(r.DefenseScore))
    l=tim.iloc[-1]; last={l.Offense:int(l.OffenseScore),l.Defense:int(l.DefenseScore)}
    txt=' '.join(g.sort_values(['Period','_oc','Id']).PlayText.fillna('').tail(4)).lower()
    return gid,h,a,{h:t.get(h,0),a:t.get(a,0)},{h:mx.get(h,0),a:mx.get(a,0)},{h:last.get(h),a:last.get(a)},int(g.Period.max()),('end of' in txt)
if __name__=='__main__':
    ids=[gid for gid in w7 if (df[df.GameId==gid].Home.iloc[0] in fbs) or (df[df.GameId==gid].Away.iloc[0] in fbs)]
    with Pool(4) as p: res=p.map(work,ids)
    json.dump([[r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7]] for r in res],open('w7_finals_raw.json','w'))
    agree=[r for r in res if r[3]==r[4]==r[5]]; dis=[r for r in res if not (r[3]==r[4]==r[5])]
    print(len(res),'FBS-involved games;',len(agree),'tally=max=last;',len(dis),'disagree')
    for r in dis: print(r[0],r[2],'at',r[1],'| tally',r[3],'| max',r[4],'| last',r[5],'| Q',r[6])
