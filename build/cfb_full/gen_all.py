import sys,json,time,pickle,pandas as pd; sys.path.insert(0,'.')
from boxscore import game_boxes
from multiprocessing import Pool
df=pd.read_pickle('prepped.pkl')
FBS=set(json.load(open('../nfl_rebuild/cfb_team_list.json')))
wk6=set(pd.read_csv('/root/.claude/uploads/b24cbaad-1fd0-50eb-9ab4-9c0e1d6593f3/4adf5572-download_19.csv',usecols=['GameId'])['GameId'])-{401856716}
meta=df.groupby('GameId').agg(home=('Home','first'),away=('Away','first'))
games=[gid for gid,r in meta.iterrows() if r.home in FBS or r.away in FBS]
groups={gid:g for gid,g in df[df.GameId.isin(games)].groupby('GameId')}
def work(gid):
    try:
        r=meta.loc[gid]; return gid, game_boxes(groups[gid], r.home, r.away)
    except Exception as e:
        return gid, ('ERR', repr(e))
if __name__=='__main__':
    t=time.time()
    with Pool(8) as p: res=dict(p.map(work, games, chunksize=4))
    errs={k:v for k,v in res.items() if v[0]=='ERR'}
    print('games',len(res),'errors',len(errs), list(errs.items())[:3], 'secs',round(time.time()-t))
    pickle.dump({'res':res,'wk6':wk6}, open('all_boxes.pkl','wb'))
