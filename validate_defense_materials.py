"""Check slide package, speech timing estimate and illustrated guide structure."""
from pathlib import Path
from zipfile import ZipFile
import re
import posixpath
from lxml import etree as E
import pandas as pd
root=Path(__file__).resolve().parent
p='http://schemas.openxmlformats.org/presentationml/2006/main'
a='http://schemas.openxmlformats.org/drawingml/2006/main'
with ZipFile(root/'presentation_5min.pptx') as z:
    slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
    assert len(slides)==10
    texts={};hidden=[]
    for name in slides:
        xml=E.fromstring(z.read(name));i=int(re.search(r'(\d+)\.xml',name)[1])
        texts[i]=' '.join(xml.xpath('//a:t/text()',namespaces={'a':a}))
        if xml.get('show')=='0':hidden.append(i)
        rels=E.fromstring(z.read(f'ppt/slides/_rels/slide{i}.xml.rels'))
        for r in rels:
            target=posixpath.normpath(posixpath.join('ppt/slides',r.get('Target')))
            assert target in z.namelist(),target
    assert sorted(hidden)==[9,10]
    tests=pd.read_csv(root/'results/joint_tests.csv').set_index('test')
    coef=pd.read_csv(root/'results/main_coefficients.csv').set_index('term')
    cv=pd.read_csv(root/'results/cv_metrics.csv').set_index('model')
    fmt=lambda x,n=3:f'{x:.{n}f}'.replace('.',',')
    assert fmt(tests.loc['competitors','p']) in texts[5]
    assert fmt(coef.loc['ln_product_weight_g','p_holm']) in texts[5]
    chart_metadata=' '.join(E.fromstring(z.read('ppt/slides/slide7.xml')).xpath('//p:cNvPr/@name',namespaces={'p':p}))
    for name in ['Mean','M1','M2','M3']:assert fmt(cv.loc[name,'rmse']) in texts[7]+' '+chart_metadata
    time=pd.read_csv(root/'results/time_sensitivity.csv').set_index('model')
    for slide in [6,8]:assert fmt(time.loc['M3_time','competitors_p']) in texts[slide]
    assert fmt(time.loc['M3_time','weight_p_holm']) in texts[6]
    for label in ['ln покупателей','ln цены конкурента 1','ln веса','ln объёма']:
        assert label in texts[5]
    assert 'ln(Y)' in texts[4]
    for text in texts.values():
        for old in ['0,594','+5,4%','Нет проверки модели на новых','Не учтены сезонность, категории']:
            assert old not in text,old
speech=(root/'speech_5min.md').read_text()
parts=re.split(r'^## Слайд .*$',speech,flags=re.M)[1:]
assert len(parts)==8
word_count=sum(len(x.split()) for x in parts)
assert 550<=word_count<=700,word_count
tex=(root/'defense_guide.tex').read_text()
assert '\\input{' not in tex
images=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}',tex)
expected={f'figures/{name}.png' for name in ['distributions','relationships','correlations',
    'categories','effects','diagnostics','validation']}
assert set(images)==expected and len(images)==7
for path in images:assert (root/path).exists(),path
labels=re.findall(r'\\label\{([^{}]+)\}',tex)
assert len(labels)==len(set(labels))
for ref in re.findall(r'\\ref\{([^{}]+)\}',tex):assert ref in labels,ref
stack=[]
for action,env in re.findall(r'\\(begin|end)\{([^{}]+)\}',tex):
    if action=='begin':stack.append(env)
    else:assert stack.pop()==env,env
assert not stack
for literal in ['0{,}011','0{,}049','0{,}151','6{,}76','1,033','0,061','0,116']:
    assert literal in tex,literal
print(f'PASS: 8 main + 2 hidden slides, current CSV values, {word_count} speech words, guide with 7 available figures.')
