import sys,json,glob
CH={}; [CH.update(json.load(open(f))) for f in glob.glob(sys.argv[1]+'/drivecharts/*.json')]
for gk in sys.argv[2:]:
    ch=CH[gk]; lo,hi=None,None
    print('==',gk)
    for x in ch:
        print(f"{x['n']:>4} {x['team'][:12]:12} {x['how']:5} Q{x['q1']} {x['t1']:>5} {str(x['spot1']):>5} {x['plays']:>2}p {x['yards']:>4}y {x['result'][:22]:22} {x['teamScore']}-{x['oppScore']} | {x['playText'][:95]}")
