import sys, json, pandas as pd; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
df=pd.read_pickle('prepped_to.pkl')
wk6=set(pd.read_csv('/root/.claude/uploads/b24cbaad-1fd0-50eb-9ab4-9c0e1d6593f3/c2146c95-download_20.csv',usecols=['GameId'])['GameId'])
data=json.load(open('data_new.json'))
def t2s(t): m,s=t.split(':'); return int(m)*60+int(s)
def check(gid):
    g=df[df.GameId==gid]; issues=[]
    dr=build_drives(g)
    mx={}
    for _,r in g.iterrows():
        mx[r.Offense]=max(mx.get(r.Offense,0),r.OffenseScore if pd.notna(r.OffenseScore) else 0)
        mx[r.Defense]=max(mx.get(r.Defense,0),r.DefenseScore if pd.notna(r.DefenseScore) else 0)
    last=dr[-1]; fin={last['team']:last['teamScore'], last['opponent']:last['oppScore']}
    if any(int(mx.get(t,0))!=v for t,v in fin.items()): issues.append(f'final tally {fin} vs feed max {dict((k,int(v)) for k,v in mx.items())}')
    for a,b in zip(dr,dr[1:]):
        if (b['q1'],-t2s(b['t1'])) < (a['q1'],-t2s(a['t1'])): issues.append(f"order: #{a['n']} Q{a['q1']} {a['t1']} before #{b['n']} Q{b['q1']} {b['t1']}")
        if a['team']==b['team'] and a['result'] not in ('Touchdown','Field Goal','Safety','Interception (Pick-6)','Fumble (Defensive TD)','Punt (Return TD)','Blocked Punt (TD)','Blocked FG (TD)','Kickoff (Return TD)','End of Half','Muffed Punt') and not (a['q2']==2 and b['q1']==3):
            issues.append(f"same team twice: #{a['n']} {a['team']} {a['result']} -> #{b['n']}")
    return gid, g.Home.iloc[0], g.Away.iloc[0], issues, fin, {k:int(v) for k,v in mx.items()}
if __name__=='__main__':
    with Pool(2) as p: res=p.map(check, sorted(wk6))
    bad=[r for r in res if r[3]]
    print('week 6 games checked', len(res), '| games with issues', len(bad))
    for r in bad: print(r[0], r[1], 'vs', r[2]); [print('   ',i) for i in r[3][:6]]
    # published game-log scores vs true final
    wrong=[]
    for gid,h,a,iss,fin,mx in res:
        for t,o in ((h,a),(a,h)):
            for gm in data['games'].get(t,[]):
                if gm['week']==6 and gm['opp']==o and (gm['ts'],gm['os'])!=(mx.get(t),mx.get(o)): wrong.append((t,o,gm['ts'],gm['os'],mx.get(t),mx.get(o)))
    print('published week-6 game-log scores that differ from the true final:', len(wrong)); [print('   ',w) for w in wrong[:20]]
