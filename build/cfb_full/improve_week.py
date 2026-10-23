"""Regenerate a week's drive charts with the current builder; keep each new chart only if its check issues are a subset (fewer, no new kinds)."""
import sys, json, glob, subprocess, shutil, os
WEEK=sys.argv[1]; D=sys.argv[2]
shutil.rmtree(D+'_old',ignore_errors=True); shutil.copytree(D,D+'_old')
subprocess.run(['python3','-I','regen_week_charts.py',WEEK,D,D],check=True)
shutil.copy(D+f'/added_week{WEEK}.json',D+'_old/')
for x in (D+'_old',D): subprocess.run(['python3','-I','check_week.py',x,WEEK],check=True,capture_output=True)
old=json.load(open(D+f'_old/issues_week{WEEK}.json')); new=json.load(open(D+f'/issues_week{WEEK}.json'))
revert=[g for g in json.load(open(D+f'/added_week{WEEK}.json')) if (lambda o,n: len(n)>len(o) or (len(n)==len(o) and ({x[0] for x in n}-{x[0] for x in o})))(set(map(tuple,old.get(g,[]))),set(map(tuple,new.get(g,[]))))]
for f in glob.glob(D+'/drivecharts/*.json'):
    d=json.load(open(f)); o=json.load(open(f.replace(D+'/',D+'_old/'))); ch=False
    for g in revert:
        if g in d and d[g]!=o[g]: d[g]=o[g]; ch=True
    if ch: json.dump(d,open(f,'w'),separators=(',',':'))
print('week',WEEK,'kept old chart for',len(revert),revert[:10])
