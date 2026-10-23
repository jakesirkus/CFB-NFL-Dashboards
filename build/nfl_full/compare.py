import json, collections, math
def num(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool)
def close(a,b):
    if a is None or b is None: return a is None and b is None
    if not (num(a) and num(b)): return a==b
    # tolerance = half a unit in the last decimal place of the published value
    s=repr(float(b)); dec=len(s.split('.')[1]) if '.' in s else 0
    return abs(a-b) <= max(0.51*10**(-min(dec,3)), 1e-9) or abs(a-b)<=0.0011*max(1,abs(b))*0
def walk(mine, live, path, stats, bad):
    if isinstance(live, dict):
        for k,v in live.items():
            if k=='pct': continue
            walk(mine.get(k) if isinstance(mine,dict) else None, v, path+(k,), stats, bad)
    else:
        ok=close(mine, live); key='.'.join(p for p in path[1:] if p not in('value',))
        stats[key][ok]+=1
        if not ok: bad[key].append((path[0],mine,live))
def report(pairs, sections=None, show=3):
    stats=collections.defaultdict(lambda:[0,0]); bad=collections.defaultdict(list)
    for tag, mine, live in pairs: walk(mine, live, (tag,), stats, bad)
    out=[]
    for k,(f,t) in sorted(stats.items()):
        if f: out.append(f'{k:45s} {t}/{t+f}  e.g. {bad[k][:show]}')
    print('\n'.join(out) if out else 'ALL MATCH'); return stats
