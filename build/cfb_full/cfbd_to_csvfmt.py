"""Convert CFBD /plays JSON to the 28-column CSV-export layout used by combined_raw_*.pkl."""
import json, sys, pandas as pd
MAP={'gameId':'GameId','driveId':'DriveId','id':'Id','driveNumber':'DriveNumber','playNumber':'PlayNumber','offense':'Offense',
 'offenseConference':'OffenseConference','offenseScore':'OffenseScore','defense':'Defense','defenseConference':'DefenseConference',
 'defenseScore':'DefenseScore','home':'Home','away':'Away','period':'Period','offenseTimeouts':'OffenseTimeouts',
 'defenseTimeouts':'DefenseTimeouts','yardline':'Yardline','yardsToGoal':'YardsToGoal','down':'Down','distance':'Distance',
 'yardsGained':'YardsGained','scoring':'Scoring','playType':'PlayType','playText':'PlayText','ppa':'Ppa','wallclock':'Wallclock'}
def convert(rows, ref):
    d=pd.DataFrame(rows)
    d['Clock Minutes']=d['clock'].map(lambda c:(c or {}).get('minutes')); d['Clock Seconds']=d['clock'].map(lambda c:(c or {}).get('seconds'))
    d=d.rename(columns=MAP)[list(ref.columns)]
    for c in ref.columns:
        if str(ref[c].dtype)=='str' or ref[c].dtype==object: d[c]=d[c].astype(ref[c].dtype)
        else: d[c]=pd.to_numeric(d[c]).astype(ref[c].dtype)
    return d
if __name__=='__main__':
    ref=pd.read_pickle(sys.argv[1]).head(0); rows=json.load(open(sys.argv[2])); convert(rows,ref).to_pickle(sys.argv[3])
