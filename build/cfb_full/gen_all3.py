import sys,json,time,pickle,pandas as pd; sys.path.insert(0,'.')
from boxscore import game_boxes
from multiprocessing import Pool
df=pd.read_pickle('prepped_to.pkl')
live=json.load(open('live/data.json'))['boxscores']
wk6=set(pd.read_csv('/root/.claude/uploads/b24cbaad-1fd0-50eb-9ab4-9c0e1d6593f3/c2146c95-download_20.csv',usecols=['GameId'])['GameId'])
want=sorted(set(int(k.split('_')[1]) for k in live) | wk6)
meta=df.groupby('GameId').agg(home=('Home','first'),away=('Away','first'))
groups={gid:g for gid,g in df[df.GameId.isin(want)].groupby('GameId')}

def work(gid):
    try:
        r=meta.loc[gid]; return gid, game_boxes(groups[gid], r.home, r.away)
    except Exception as e:
        import traceback; return gid, ('ERR', traceback.format_exc()[-400:])
if __name__=='__main__':
    t=time.time()
    with Pool(2) as p: res=dict(p.map(work, want, chunksize=4))
    errs={k:v for k,v in res.items() if v[0]=='ERR'}
    print('games',len(res),'errors',len(errs), list(errs.items())[:2], 'secs',round(time.time()-t))
    pickle.dump({'res':res,'wk6':wk6}, open('all_boxes3.pkl','wb'))
