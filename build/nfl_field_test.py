import sys, numpy as np, pandas as pd
sys.argv=['x','/home/claude/data/nflhist/feat_hist.pkl','/home/claude/data/nflhist/cap_hist.pkl']
exec(open('/home/claude/cfb-nfl-dashboards/build/nfl_xpts_grid.py').read().split('res = []')[0])
G='wp90_98'; lo,hi=GSPEC[G]
DEP=pd.read_pickle('/home/claude/data/nflhist/dep_hist.pkl'); DD={k:g for k,g in DEP.groupby(['game_id','posteam'],sort=False)}
didx=[DD[(r.gk,r.t)] for r in F.itertuples()]
def blend(vals, w, k=6):
    if not len(vals): return 0.0
    full=vals.mean(); W=w.sum(); comp=np.average(vals,weights=w) if W>0 else full
    return full+W/(W+k)*(comp-full)
def field(kind):
    out=np.zeros(len(F))
    for i,d in enumerate(didx):
        m=d.ytg.values>5; dd=d[m]
        if not len(dd): continue
        w=wfun(dd.wp.fillna(0.5).values,lo,hi)
        if kind=='share':  v=np.minimum(dd.c20.values/dd.ytg.values,1); out[i]=100*blend(v,w)
        elif kind=='pooled':
            yc=np.minimum(dd.c20.values,dd.ytg.values); full=yc.sum()/dd.ytg.sum(); W=(w*dd.ytg.values).sum()
            comp=(w*yc).sum()/W if W>0 else full; Wd=w.sum(); out[i]=100*(full+Wd/(Wd+6)*(comp-full))
        elif kind=='ydsPerDrive': v=np.minimum(dd.c20.values,dd.ytg.values); out[i]=blend(v,w)
        elif kind=='epProg': v=dd.ep_prog.fillna(0).values; out[i]=10*blend(v,w)
    return out
def ypp40():
    out=np.zeros(len(idx))
    for i,d in enumerate(idx):
        w=wfun(d.wp.fillna(0.5).values,lo,hi); yc=d['c40'].values; n=d.n.values
        full=yc.sum()/n.sum() if n.sum() else 0; W=(w*n).sum(); comp=(w*yc).sum()/W if W>0 else full
        out[i]=full+W/(W+40)*(comp-full)
    return out
sr=F.sr.values+F[f'{G}_ds'].fillna(0).values; ex=F.ex.values+F[f'{G}_de'].fillna(0).values; dr=F.dr.values
def X_of(fv=None, ypp=None, explosive=True):
    cols=[np.ones(len(F)), dr]
    if fv is not None: cols.append(dr*fv/100)
    cols.append(dr*sr/100)
    if explosive: cols.append(dr*ex/100)
    if ypp is not None: cols.append(dr*ypp/10)
    return np.column_stack(cols)
def run_X(X):
    y=F.pts.values.astype(float); xp=np.zeros(len(F)); s=F.season.values
    for se in np.unique(s):
        tr=s!=se; b=np.linalg.lstsq(X[tr],y[tr],rcond=None)[0]; xp[~tr]=np.maximum(0,X[~tr]@b)
    err,_=forward(xp); return xp,err,np.linalg.lstsq(X,y,rcond=None)[0]
FV={k:field(k) for k in ('share','pooled','ydsPerDrive','epProg')}; YP=ypp40()
cands={'current: share of field (per-drive average)':X_of(FV['share']),
       'A pooled share (long fields count more)':X_of(FV['pooled']),
       'B capped yards per drive (no credit for yards not available)':X_of(FV['ydsPerDrive']),
       'C expected points added per drive (field-position neutral)':X_of(FV['epProg']),
       'success + explosive only (no field term)':X_of(None),
       'C + yards/play (40-yd cap)':X_of(FV['epProg'],YP),
       'B + yards/play (40-yd cap)':X_of(FV['ydsPerDrive'],YP),
       'current + yards/play (40-yd cap)':X_of(FV['share'],YP)}
res={}
for k,X in cands.items(): res[k]=run_X(X)
e0=res['current: share of field (per-drive average)'][1]
# short-field test: games where the team had 2+ drives starting inside opp 40 after takeaways vs model bias
sf=np.array([int(((d.ytg.values<=40)).sum()) for d in didx])
for k,(xp,e,b) in res.items():
    d=e-e0; bs=[d[np.random.default_rng(j).integers(0,len(d),len(d))].mean() for j in range(1000)]
    bias_sf=np.mean((xp-F.pts.values)[sf>=2]); bias_n=np.mean((xp-F.pts.values)[sf==0])
    print(f"{k}\n    next-game miss {e.mean():.3f} ({d.mean():+.3f} vs current, better in {np.mean(np.array(bs)<0):.0%}) | fit {np.mean(np.abs(xp-F.pts.values)):.2f} | coef {np.round(b,3).tolist()}")
import pickle; pickle.dump({k:v[2] for k,v in res.items()},open('/tmp/claude-0/-home-claude/7dcaeb54-d458-5574-be7b-c323d22db574/scratchpad/field_coefs.pkl','wb'))
err,R=forward(F.pts.values.astype(float)); print('benchmark: actual points',round(err.mean(),3))
# apply to 2026 games
F=pd.read_pickle('/home/claude/data/nflhist/feat_2026b.pkl'); F=F[F.dr>0].reset_index(drop=True)
DEP=pd.read_pickle('/home/claude/data/nflhist/dep_2026.pkl'); DD={k:g for k,g in DEP.groupby(['game_id','posteam'],sort=False)}
didx=[DD[(r.gk,r.t)] for r in F.itertuples()]
sr=F.sr.values+F[f'{G}_ds'].fillna(0).values; ex=F.ex.values+F[f'{G}_de'].fillna(0).values; dr=F.dr.values
FV={k:field(k) for k in ('share','pooled','epProg')}
out={'current':np.maximum(0,X_of(FV['share'])@res['current: share of field (per-drive average)'][2]),
     'A pooled':np.maximum(0,X_of(FV['pooled'])@res['A pooled share (long fields count more)'][2]),
     'C EP added':np.maximum(0,X_of(FV['epProg'])@res['C expected points added per drive (field-position neutral)'][2])}
for gk in ('2026_09_NYJ_KC','2026_08_PHI_WAS','2026_03_LAC_BUF','2026_09_DEN_CAR'):
    for i,r in F[F.gk==gk].iterrows(): print(gk, r.t, int(r.pts), ' | '.join(f'{k} {v[i]:.1f}' for k,v in out.items()))
