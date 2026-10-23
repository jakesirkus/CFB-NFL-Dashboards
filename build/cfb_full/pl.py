import sys,json,glob
CH={}; [CH.update(json.load(open(f))) for f in glob.glob('out5/drivecharts/*.json')]
for a in sys.argv[1:]:
    gk,ns=a.split(':'); 
    for n in map(int,ns.split(',')):
        x=CH[gk][n-1]; print(f"== {gk} #{x['n']} {x['team']} {x['how']} Q{x['q1']} {x['t1']} sp{x['spot1']} -> Q{x['q2']} {x['t2']} sp{x['spot2']} {x['plays']}p {x['yards']}y {x['result']} {x['teamScore']}-{x['oppScore']}")
        for p in x['playList']: print(f"     Q{p['q']} d{p['down']} yl{p['yardline100']} {'S' if p['scoring'] else ' '} | {p['text'][:170]}")
