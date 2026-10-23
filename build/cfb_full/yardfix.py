"""Cross-check the feed's YardsGained against the play text and the next snap's field position."""
import re, numpy as np, pandas as pd
PAT=[(re.compile(r'for (?:a )?loss of (\d+) yards?', re.I), -1),
     (re.compile(r'for (\d+) yards? loss', re.I), -1),
     (re.compile(r'(\d+) yards? loss', re.I), -1),
     (re.compile(r'for no gain|for 0 yards?|loss of 0 yards?', re.I), 0),
     (re.compile(r'for (\d+) yards? gain', re.I), 1),
     (re.compile(r'(\d+) yards? gain', re.I), 1),
     (re.compile(r'for (\d+) yards?', re.I), 1),
     (re.compile(r'run for (\d+) yds?', re.I), 1),
     (re.compile(r'for (\d+) yds?', re.I), 1),
     (re.compile(r'for a loss of (\d+) yards?', re.I), -1)]
def text_yards(t):
    t=str(t).split('PENALTY')[0]
    if re.search(r'incomplete', t, re.I): return 0
    best=None
    for rx,sgn in PAT:
        m=rx.search(t)
        if m:
            if sgn==0: return 0
            best=sgn*int(m.group(1)); break
    return best
def check(df):
    rp=df[(df.is_rush|df.is_pass)].copy()
    rp['ty']=rp.PlayText.map(text_yards)
    return rp

def corrected(df):
    """Return a copy of df with YardsGained fixed where the feed's number is clearly wrong:
    the text and the next snap's field position agree with each other but not with the feed."""
    d=df.copy()
    d['_o']=-d['clock']
    order=d.sort_values(['GameId','DriveNumber','Period','_o','Id'])
    nxt_ytg=order.groupby(['GameId','DriveNumber','Offense']).YardsToGoal.shift(-1)
    nxt_type=order.groupby(['GameId','DriveNumber','Offense']).PlayType.shift(-1)
    d['_next_ytg']=nxt_ytg.reindex(d.index); d['_next_type']=nxt_type.reindex(d.index)
    rp=(d.is_rush|d.is_pass)
    t=d.PlayText.fillna('')
    d['_ty']=np.where(rp, t.map(text_yards), np.nan)
    delta=d.YardsToGoal-d['_next_ytg']
    pen=t.str.contains('PENALTY',case=False)|(d['_next_type']=='Penalty')
    inc=d.PlayType=='Pass Incompletion'
    fix=pd.Series(False,index=d.index); new=d.YardsGained.copy()
    # incomplete passes gain nothing (unless a penalty is involved)
    # (with a penalty on the play the feed often stores the penalty or a garbage net there, e.g. -76 on an incomplete + DPI)
    m1=rp&inc&(d.YardsGained!=0)&~d.giveaway&~t.str.contains('intercept',case=False)
    new[m1]=0; fix|=m1
    # text and ball movement agree, feed is off by 5+
    m2=rp&~inc&d['_ty'].notna()&((d.YardsGained-d['_ty']).abs()>=5)&~pen&delta.notna()&((delta-d['_ty']).abs()<=1)&~d.giveaway
    new[m2]=d.loc[m2,'_ty']; fix|=m2
    # last snap of a drive (no next snap): trust the text if the feed exceeds the distance to the goal line
    m3=rp&~inc&d['_ty'].notna()&d['_next_ytg'].isna()&((d.YardsGained-d['_ty']).abs()>=5)&(d.YardsGained>d.YardsToGoal)&~pen&~d.giveaway
    new[m3]=d.loc[m3,'_ty']; fix|=m3
    sc=d.Scoring==True
    # a sack can't gain yards
    m4=rp&d.is_sack&(d.YardsGained>0)&d['_ty'].notna()
    new[m4]=d.loc[m4,'_ty']; fix|=m4
    # feed copied the distance-to-goal into yards on a non-scoring play the text describes differently
    m5=rp&~inc&~sc&(d.YardsGained==d.YardsToGoal)&(d.YardsToGoal>0)&d['_ty'].notna()&((d.YardsGained-d['_ty']).abs()>=5)&~d.giveaway
    new[m5]=d.loc[m5,'_ty']; fix|=m5
    # penalty on a completed play / run: the feed sometimes stores a net that can't be right (2-yd catch logged as 87).
    # Trust the text when it is 15+ off, except where the feed is legitimately yards-to-spot-of-foul
    # ('gain (N)', a score nullified by penalty), intentional grounding, and lateral chains.
    odd=~t.str.contains(r'(?:gain|loss) \(-?\d+\)|score nullified|intentional grounding|lateral|no play',case=False)
    m6=rp&~inc&pen&odd&d['_ty'].notna()&((d.YardsGained-d['_ty']).abs()>=15)&~d.giveaway&~sc
    new[m6]=d.loc[m6,'_ty']; fix|=m6
    d['yards_fixed']=fix; d['YardsGained_feed']=d.YardsGained; d['YardsGained']=new
    d['yds']=np.where(d.is_penplay,0,d.YardsGained.fillna(0))
    return d.drop(columns=['_o','_next_ytg','_next_type','_ty'])
