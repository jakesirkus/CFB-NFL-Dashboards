"""Generic clean-ups on published drive charts (any week). Applied per game only if the game's check flags go down."""
import sys, json, glob, re, copy, subprocess, shutil
OUT=sys.argv[1]; WEEKS=sys.argv[2].split(',')
def polish(ch):
    ch=copy.deepcopy(ch); run={}
    out=[]
    for i,x in enumerate(ch):
        t=x['team']; o=x['opponent']; txt=(x.get('playText') or '')
        # duplicate entry (same team, same last play) -> keep the later one
        if i+1<len(ch) and ch[i+1]['team']==t and (ch[i+1].get('playText') or '')==txt and txt: continue
        gn=(x['teamScore']-run.get(t,0)) if x.get('teamScore') is not None else 0
        # 2-point-only overtime periods (3rd OT on): a single conversion try, not a touchdown drive
        if x['q1']>=7 and x['plays']<=1 and x['result'] in ('Touchdown','End of Game','Turnover on Downs','Incomplete'):
            x['result']='2-Pt Good' if gn>=2 else '2-Pt Failed'; x['color']='blue' if gn>=2 else 'red'; x['scored']=gn>=2; x['yards']=0
        # scoring-summary line "N Yd Fumble Recovery (kick)" = the offense's own fumble recovered for a TD
        if x['result']=='Fumble' and re.search(r'\d+ yd fumble recovery \(', txt.lower()) and gn>=6:
            x['result']='Touchdown'; x['color']='blue'; x['scored']=True
        # kneel-downs end the half/game, they are not punts
        if x['result']=='Punt' and 'kneel' in txt.lower():
            x['result']='End of Game' if x['q2']>=4 else 'End of Half'; x['color']='gray'
        if x.get('teamScore') is not None: run[t]=x['teamScore']; run[o]=x['oppScore']
        out.append(x)
    for i,x in enumerate(out): x['n']=i+1
    return out
if __name__=='__main__':
    shutil.rmtree(OUT+'_pre',ignore_errors=True); shutil.copytree(OUT,OUT+'_pre')
    for f in glob.glob(OUT+'/drivecharts/*.json'):
        d=json.load(open(f))
        for g in d:
            if g.split('_')[0] in WEEKS: d[g]=polish(d[g])
        json.dump(d,open(f,'w'),separators=(',',':'))
    for w in WEEKS:
        for x in (OUT+'_pre',OUT):
            shutil.copy(OUT+f'/added_week{w}.json',x+'/') if x!=OUT else None
            subprocess.run(['python3','-I','check_week.py',x,w],check=True,capture_output=True)
        old=json.load(open(OUT+f'_pre/issues_week{w}.json')); new=json.load(open(OUT+f'/issues_week{w}.json'))
        bad=[g for g in set(old)|set(new) if len(new.get(g,[]))>len(old.get(g,[]))]
        for f in glob.glob(OUT+'/drivecharts/*.json'):
            d=json.load(open(f)); o=json.load(open(f.replace(OUT+'/',OUT+'_pre/'))); c=False
            for g in d:
                if g.split('_')[0]==w and (g in bad or len(new.get(g,[]))==len(old.get(g,[]))) and d[g]!=o[g]: d[g]=o[g]; c=True
            if c: json.dump(d,open(f,'w'),separators=(',',':'))
        subprocess.run(['python3','-I','check_week.py',OUT,w],check=True,capture_output=True)
        print('week',w,'flags',sum(len(v) for v in old.values()),'->',sum(len(v) for v in json.load(open(OUT+f'/issues_week{w}.json')).values()))
