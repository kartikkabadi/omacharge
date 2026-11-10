import json
from pathlib import Path
import sys
p=Path(__file__).with_name('mock-state.json')
state=json.loads(p.read_text())
if sys.argv[1] == 'set':
    _, id, end, *start = sys.argv[1:]
    ctl=next(c for c in state['controls'] if c['id']==id)
    ctl['end']=int(end)
    ctl['start']=int(start[0]) if start else (75 if end=='80' else 100) if ctl['driver']=='apple' else None
    ctl['persisted']=True
    p.write_text(json.dumps(state))
print(json.dumps(state))
