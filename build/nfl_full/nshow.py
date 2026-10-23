import sys,json
D=json.load(open(sys.argv[1]))
for a in sys.argv[2:]:
    gk,rng=a.split(':'); lo,hi=map(int,rng.split('-'))
    for x in D['boxscores'][gk]['driveChart']:
        if lo<=x['n']<=hi:
            print(f"{gk} {int(x['n']):>3} {x['team'][:14]:14} {x['how']:5} Q{x['q1']} {x['t1']:>5} sp{x['spot1']} {x['plays']}p {x['yards']}y {x['result']:16} {x['teamScore']}-{x['oppScore']} | {x['playText'][:150]}")
