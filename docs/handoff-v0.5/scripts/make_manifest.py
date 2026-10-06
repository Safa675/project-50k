"""Generate file inventory and hashes after validation; excludes itself by output path."""
from pathlib import Path
from hashlib import sha256
import json
P=Path(__file__).resolve().parents[1]
files=[]
for f in sorted(P.rglob('*')):
    if not f.is_file() or '__pycache__' in f.parts or f.name in {'MANIFEST.json'}:continue
    files.append({'path':str(f.relative_to(P)),'bytes':f.stat().st_size,'sha256':sha256(f.read_bytes()).hexdigest()})
(P/'MANIFEST.json').write_text(json.dumps({'version':'0.5-research','excluded':['MANIFEST.json','__pycache__/*'],'files':files},ensure_ascii=False,indent=2)+'\n')
print(f'Manifest: {len(files)} files')
