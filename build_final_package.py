"""Package the current coursework files without archived versions."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parent
guide=ROOT/'defense_guide.tex'
images=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}',guide.read_text())
with ZipFile(ROOT/'defense_guide_bundle.zip','w',ZIP_DEFLATED) as z:
    z.write(guide,guide.name)
    for image in images:z.write(ROOT/image,image)
with ZipFile(ROOT/'defense_guide_bundle.zip') as z:
    assert z.testzip() is None
    assert z.read('defense_guide.tex')==guide.read_bytes()
    for image in images:assert z.read(image)==(ROOT/image).read_bytes()

names=['FINAL_CHECK.md','README.md','PLAN.md','REVIEW.md','DatasetInfo.md',
       'summary.md','TOLEARN.md','coursework.tex','defense_guide.tex',
       'defense_guide_bundle.zip','presentation_5min.pptx','presentation_5min.pdf',
       'speech_5min.md','science_work_simple.ipynb','retail_price.csv',
       'analysis_retail.py','build_analysis_materials.py','build_presentation.py',
       'run_notebook.py','validate_materials.py','validate_statistics.py',
       'validate_defense_materials.py','requirements.txt','build_final_package.py']
files=[ROOT/name for name in names]
for directory in ['figures','report_tables','appendix','results','presentation_assets']:
    files.extend(sorted(p for p in (ROOT/directory).rglob('*') if p.is_file()))
assert all(p.exists() for p in files)
checksums={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
archive=ROOT/'coursework_final.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for p in files:z.write(p,str(p.relative_to(ROOT)))
    z.writestr('CHECKSUMS.json',json.dumps(checksums,ensure_ascii=False,indent=2))
with ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(checksums)+1
    for name,digest in checksums.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
print(f'Final package verified: {len(files)} files, {archive.stat().st_size:,} bytes')
