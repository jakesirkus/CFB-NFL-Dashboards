import sys,contextlib,io,pandas as pd; sys.path.insert(0,'.')
from boxscore import build_drives
df=pd.read_pickle('prepped_to.pkl')
for a in sys.argv[1:]:
    gid=int(a.split('_')[-1])
    with contextlib.redirect_stdout(io.StringIO()): ch=build_drives(df[df.GameId==gid])
    print('==',a)
    for i,x in enumerate(ch): print(f"{i+1:>3} {x['team'][:12]:12} {x['how']:5} Q{x['q1']} {x['t1']:>5} {str(x['spot1']):>5} {x['plays']:>2}p {x['yards']:>4}y {x['result'][:20]:20} {x['teamScore']}-{x['oppScore']} | {x['playText'][:80]}")
