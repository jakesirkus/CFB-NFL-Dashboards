import sys, json, os, pandas as pd; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
df=pd.read_pickle('prepped.pkl')
c=open('out/index.html').read()
o='<script id="drivechart-index-data" type="application/json">'; s=c.index(o)+len(o); e=c.index('</script>',s)
di=json.loads(c[s:e])
w6={k:v for k,v in di.items() if k.startswith('6_')}
assert not any(k.endswith('401856716') for k in w6)
def work(gk):
    gid=int(gk.split('_')[1]); g=df[df.GameId==gid]
    return gk,[{k:v for k,v in d.items() if not k.startswith('_')} for d in build_drives(g)]
if __name__=='__main__':
    with Pool(2) as p: res=dict(p.map(work, sorted(w6)))
    shards={}
    for gk,path in w6.items(): shards.setdefault(path,{})[gk]=res[gk]
    os.makedirs('out2/drivecharts',exist_ok=True)
    for path,obj in shards.items():
        old=json.load(open('out/'+path)); assert set(old)==set(obj), path
        json.dump(obj, open('out2/'+path,'w'), separators=(',',':'))
    json.dump(sorted(shards), open('out2/dc_files.json','w'))
    print('games',len(res),'shards',len(shards))
    for d in res['6_401869933']: print(d['n'],d['team'][:10],d['how'],'Q%d %s'%(d['q1'],d['t1']),'->','Q%d %s'%(d['q2'],d['t2']),d['result'],'%d-%d'%(d['teamScore'],d['oppScore']))
