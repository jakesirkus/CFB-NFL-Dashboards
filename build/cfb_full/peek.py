import json,glob,sys
CH={}; [CH.update(json.load(open(f))) for f in glob.glob('out5/drivecharts/*.json')]
for spec in sys.argv[1:]:
    g,a,b=spec.split(':'); a=int(a); b=int(b)
    print('=====',g)
    for x in CH[g]:
        if a<=x['n']<=b:
            print(f"  #{x['n']} {x['team'][:14]} Q{x['q1']} {x['t1']} sp{x['spot1']}->{x['spot2']} {x['plays']}p {x['yards']}y {x['result']} {x['teamScore']}-{x['oppScore']}")
            for p in x['playList'][-3:]: print('       ',p['text'][:230])
