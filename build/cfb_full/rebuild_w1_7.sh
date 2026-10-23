#!/bin/bash
# Full Weeks 1-7 rebuild from out4 (published Weeks 1-6 base) into out5.
set -e
cd "$(dirname "$0")"
python3 -I full_pipeline.py >/dev/null && python3 -I winloss_and_radar.py >/dev/null && python3 -I finalize_radar.py >/dev/null
python3 -I build_week.py 7 w7_gids.txt out4 out5 | tail -1
for w in 1 2 3 4 5 6; do cp out4/added_week$w.json out5/ 2>/dev/null || cp out5_old/added_week$w.json out5/; done
TOG=$(cat fg_retyped.txt),$(cat to_changed.txt),$(cat to_changed2.txt),$(cat to_changed3.txt),$(cat to_changed4.txt),401858212,401864424,401869150,401856782,401858246,401858262,401858455,401867840,401867989,401868792
python3 -I patch_turnovers.py out5 $TOG > /dev/null
python3 -I regen_boxes.py out5 $(cat yds_changed.txt),$(cat fg_retyped.txt)
for w in 1 2 3 4 5 6; do python3 -I improve_week.py $w out5 | grep "kept old"; done
python3 -I fix_week_opps.py 6 out5 | tail -1
python3 - "$TOG" << 'PY'
import json,subprocess,sys
ch=sys.argv[1].split(',')+['401856767','401862699','401858487']
T='<script id="dashboard-data" type="application/json">'
s=open('out5/index.html').read(); a=s.index(T)+len(T); b=s.index('</script>',a); D=json.loads(s[a:b])
by={}
for k in D['boxscores']:
    w,g=k.split('_')
    if g in ch and w not in ('6','7'): by.setdefault(w,[]).append(k)
for w,ks in sorted(by.items()): print(subprocess.run(['python3','-I','fix_week_opps.py',w,'out5',','.join(ks)],capture_output=True,text=True).stdout.strip())
PY
python3 -I polish_charts.py out5 1,2,3,4,5,6,7
python3 -I chart_overrides.py out5
for w in 1 2 3 4 5 6 7; do python3 -I check_week.py out5 $w > /dev/null; done
python3 -I ../add_ppo.py out5/index.html out5/index.html
