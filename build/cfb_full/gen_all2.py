import sys,json,time,pickle,pandas as pd; sys.path.insert(0,'.')
from boxscore import game_boxes
from multiprocessing import Pool
df=pd.read_pickle('prepped2.pkl'); EV=pd.read_pickle('pen_events.pkl')
live=json.load(open('live/data.json'))['boxscores']
wk6=set(pd.read_csv('/root/.claude/uploads/b24cbaad-1fd0-50eb-9ab4-9c0e1d6593f3/4adf5572-download_19.csv',usecols=['GameId'])['GameId'])-{401856716}
want=sorted(set(int(k.split('_')[1]) for k in live) | wk6)
meta=df.groupby('GameId').agg(home=('Home','first'),away=('Away','first'))
groups={gid:g for gid,g in df[df.GameId.isin(want)].groupby('GameId')}
evg={gid:e for gid,e in EV[EV.GameId.isin(want)].groupby('GameId')}
def work(gid):
    try:
        r=meta.loc[gid]; return gid, game_boxes(groups[gid], r.home, r.away, evg.get(gid, EV.iloc[0:0]))
    except Exception as e:
        import traceback; return gid, ('ERR', traceback.format_exc()[-400:])
if __name__=='__main__':
    t=time.time()
    with Pool(2) as p: res=dict(p.map(work, want, chunksize=4))
    errs={k:v for k,v in res.items() if v[0]=='ERR'}
    print('games',len(res),'errors',len(errs), list(errs.items())[:2], 'secs',round(time.time()-t))
    pickle.dump({'res':res,'wk6':wk6}, open('all_boxes2.pkl','wb'))
