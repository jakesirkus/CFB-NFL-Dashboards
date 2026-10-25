import numpy as np
"""raw play-by-play -> corrected raw (combined_raw_fixed.pkl) + prepped/flagged table (prepped_to.pkl)."""
import sys, pandas as pd; sys.path.insert(0,'.')
from multiprocessing import Pool
from prep import prep
from turnovers import flag_game
from yardfix import corrected
INT={'Interception','Pass Interception Return','Interception Return Touchdown'}
def flags(p):
    with Pool(2) as pool: parts=pool.map(flag_game,[g for _,g in p.groupby('GameId')],chunksize=8)
    return pd.concat(parts).sort_values('Id')
import re as _re
_REVIEW=_re.compile(r'\.?\s*(?:The previous play is under (?:automatic )?review|CALL (?:OVERTURNED|UPHELD|STANDS|CONFIRMED)|\(Original Play:).*$', _re.I|_re.S)
def final_text(t):
    """The feed writes a reviewed play as '<final ruling>. The previous play is under review ... CALL OVERTURNED.
    (Original Play: <what was first called>)'. Only the leading part is what counted."""
    if not isinstance(t,str): return t
    head=_REVIEW.sub('', t).strip() or t
    # the try after a reviewed TD is written AFTER the '(Original Play: ...)' block
    # ('... CALL OVERTURNED. (Original Play: ...) #15 W.Hammond pass attempt failed'): keep that tail
    i=t.find('(Original Play:')
    if i>=0:
        depth=0
        for j in range(i,len(t)):
            depth+=t[j]=='('; depth-=t[j]==')'
            if depth==0:
                tail=t[j+1:].strip()
                if tail: head=head+' '+tail
                break
    return head
if __name__=='__main__':
    raw=pd.read_pickle(sys.argv[1])
    raw['PlayText']=raw.PlayText.map(final_text)
    # 'TOUCHDOWN nullified by penalty' is not a touchdown; keep the words out of every text test
    raw['PlayText']=raw.PlayText.str.replace(r'TOUCHDOWN nullified', 'SCORE NULLIFIED', case=False, regex=True)
    # missed / blocked field goals the feed types as 'Kickoff'
    _t=raw.PlayText.fillna('').str.lower()
    _fg=raw.PlayType.eq('Kickoff')&_t.str.contains('field goal attempt')&~_t.str.contains('kickoff|kicks off')
    _td=_t.str.contains(r'touchdown')&~_t.str.contains('nullified|no play')
    raw.loc[_fg,'PlayType']=np.where(_t[_fg].str.contains('blocked'), np.where(_td[_fg],'Blocked Field Goal Touchdown','Blocked Field Goal'),
                                     np.where(_td[_fg],'Missed Field Goal Return','Field Goal Missed'))
    open('fg_retyped.txt','w').write(','.join(map(str,sorted(raw[_fg].GameId.unique()))))
    fx=corrected(flags(prep(raw))); f=fx[fx.yards_fixed]
    raw.loc[f.index,'YardsGained']=f.YardsGained
    raw.loc[raw.PlayType.isin(INT),'YardsGained']=0
    import json, os
    if os.path.exists('yard_overrides.json'):          # hand-verified plays the feed gets wrong
        for pid,o in json.load(open('yard_overrides.json')).items(): raw.loc[raw.Id==int(pid),'YardsGained']=o['yards']
    raw.to_pickle('combined_raw_fixed.pkl')
    P=flags(prep(raw))
    if os.path.exists('flag_overrides.json'):         # hand-verified turnover calls the text parser can't read
        for pid,o in json.load(open('flag_overrides.json')).items():
            for k,v in o.items():
                if k!='why': P.loc[P.Id==int(pid),k]=v
        P['giveaway']=P['int']|P['fum_lost']
    P.to_pickle('prepped_to.pkl')
    print('games',raw.GameId.nunique(),'| yardage corrections',len(f))
