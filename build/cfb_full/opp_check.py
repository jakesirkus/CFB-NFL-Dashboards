import sys, json, pandas as pd; sys.path.insert(0,'.')
from boxscore import build_drives, pat_points
from multiprocessing import Pool
df=pd.read_pickle('prepped.pkl')
live=json.load(open('live/data.json'))['boxscores']
def snaps(d):
    r=d['_rows']; b=r[r.Offense==d['team']]
    kneel=(b.PlayType=='Rush')&b.PlayText.fillna('').str.contains('kneel',case=False)
    return b[b.is_scrim&~kneel&~b.PlayText.fillna('').str.contains('NO PLAY')]
def pts(d):
    if d['result']=='Touchdown':
        r=d['_rows']; t=r[(r.Scoring==True)&(r.Offense==d['team'])]
        return 6+pat_points(t.iloc[-1].PlayText if len(t) else '')
    return 3 if d['result']=='Field Goal' else 0
def work(gk):
    gid=int(gk.split('_')[1]); g=df[df.GameId==gid]; dr=build_drives(g); out=[]
    for team,b in live[gk].items():
        o=b.get('opportunities');
        if not o: continue
        mine=[d for d in dr if d['team']==team]
        A=[d for d in mine if len(snaps(d)) and snaps(d).YardsToGoal.min()<=30]
        B=[d for d in mine if d['_min_ytg']<=40 and d['_scrim']>0]
        out.append(dict(gk=gk,team=team,old=o['trips'],A=len(A),B=len(B),old_pts=o['points'],A_pts=sum(pts(d) for d in A),A_pts7=sum(7 if d['result']=='Touchdown' else 3 if d['result']=='Field Goal' else 0 for d in A)))
    return out
if __name__=='__main__':
    keys=[k for k in live if not k.startswith('6_')]
    with Pool(2) as p: res=[x for r in p.map(work, keys, chunksize=8) for x in r]
    r=pd.DataFrame(res); r.to_pickle('opp_cmp.pkl')
    print('team-games',len(r))
    print('trips: opp-30 snap rule exact %.1f%% | opp-40 rule (what Week 6 used) exact %.1f%%'%(100*(r.A==r.old).mean(),100*(r.B==r.old).mean()))
    print('points (opp-30 trips): actual PAT exact %.1f%% | flat 7 per TD exact %.1f%%'%(100*(r.A_pts==r.old_pts).mean(),100*(r.A_pts7==r.old_pts).mean()))
    print(r[r.A!=r.old].head(10).to_string())
