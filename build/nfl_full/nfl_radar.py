import numpy as np
from nfl_box import line_yards
from nfl_season import conv3, conv4
def radar_raw(x, seriesRate):
    s=x[x.is_scrim]; ru=s[s.is_rush]; db=s[s.is_db]; e=s[s.down.isin([1,2])]; l=s[s.down.isin([3,4])]
    m=lambda v: float(v.mean()) if len(v) else None
    pc=lambda a,b: 100*a/b if b else None
    return {'epaPlay':m(s.epa),'earlyEpa':m(e.epa),'lateSR':pc(int(conv3(l[l.down==3]).sum()+conv4(l[l.down==4]).sum()),len(l)),'avgDist3rd':m(s[s.down==3].ydstogo),
            'rushEpa':m(ru.epa),'stuffPct':pc((ru.yds<=0).sum(),len(ru)),'lineYards':m(ru.yds.apply(line_yards)),'opportunityPct':pc((ru.yds>=4).sum(),len(ru)),
            'explosivePct':pc(s.expl.sum(),len(s)),'passExplPct':pc(db.expl_pass.sum(),len(db)),'rushExplPct':pc(ru.expl_rush.sum(),len(ru)),
            'nonExplEpa':m(s[~s.expl].epa),'passEpa':m(s[s.is_passatt].epa),'ydsPerDb':m(db.yds),'passSR':pc(db.succ.sum(),len(db)),
            'earlySR':pc(e.succ.sum(),len(e)),'seriesRate':seriesRate,'dbEpa':m(db.epa),'rushSR':pc(ru.succ.sum(),len(ru))}
