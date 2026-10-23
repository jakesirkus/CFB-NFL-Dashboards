import sys, pickle; sys.path.insert(0,'.')
import pandas as pd
from nfl_season import flags2
from nfl_box import game_boxes
p=flags2(pd.read_pickle(sys.argv[1])).sort_values('play_id')
out={}
for gk,g in p.groupby('game_id'):
    out[gk]=game_boxes(g)
pickle.dump(out,open(sys.argv[2],'wb')); print(len(out))
