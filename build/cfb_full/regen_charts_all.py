import sys, json, glob, pandas as pd, collections; sys.path.insert(0,'.')
from boxscore import build_drives
from multiprocessing import Pool
import contextlib, io
df=pd.read_pickle('prepped_to.pkl')
gids=set(df.GameId.unique())
files=sorted(glob.glob('out4/drivecharts/*.json'))
def work(gk):
    g=df[df.GameId==int(gk.split('_')[1])]
    with contextlib.redirect_stdout(io.StringIO()):
        return gk,[{k:v for k,v in x.items() if not k.startswith('_')} for x in build_drives(g)]
if __name__=='__main__':
    allc={}; where={}
    for f in files:
        for gk,v in json.load(open(f)).items(): allc[gk]=v; where[gk]=f
    todo=[gk for gk in allc if int(gk.split('_')[1]) in gids]
    with Pool(4) as p: res=dict(p.map(work,todo,chunksize=20))
    json.dump(res,open('regen_all.json','w'))
    print(len(res))
