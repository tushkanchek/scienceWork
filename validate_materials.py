"""Validate numerical exports and report references without compiling TeX."""
from pathlib import Path
import hashlib
import json
import re
from io import StringIO
import numpy as np
import pandas as pd
import nbformat
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

root = Path(__file__).resolve().parent
load = lambda name: pd.read_csv(root/'results'/f'{name}.csv')
manifest = json.loads((root/'results'/'manifest.json').read_text())
assert manifest['sha256'] == hashlib.sha256((root/'retail_price.csv').read_bytes()).hexdigest()
main = load('main_coefficients')
assert len(main) == 9 and main.term.is_unique
# Independent Holm calculation, then return to the original order.
p = main.p.to_numpy()
order = np.argsort(p)
adjusted = np.minimum(1, np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]))
np.testing.assert_allclose(main.p_holm.to_numpy()[order], adjusted)
assert set(main.loc[main.p_holm < .05,'term']) == {'ln_customers','ln_product_weight_g'}
for model in ['M1','M2','M3','M3_time']:
    r = load('model_comparison').set_index('model').loc[model]
    assert r['parameters'] == r['rank'] == r['cov_rank']
    n, k = r['n'], r['parameters']-1
    np.testing.assert_allclose(r.adjusted_r2, 1-(1-r.r2)*(n-1)/(n-k-1))
raw = pd.read_csv(root/'retail_price.csv')
oof = load('oof_predictions')
assert len(oof) == len(raw) == 676
assert not oof.isna().any().any()
assert oof.groupby('product_id').fold.nunique().max() == 1
np.testing.assert_allclose(oof.observed, np.log(raw.total_price))
np.testing.assert_array_equal(oof.product_id, raw.product_id)
assert oof.fold.nunique() == 5
for fold in sorted(oof.fold.unique()):
    train = oof.fold != fold
    assert set(raw.loc[train,'product_category_name']) == set(raw.product_category_name)
    np.testing.assert_allclose(oof.loc[~train,'Mean'], np.log(raw.loc[train,'total_price']).mean())
for _,r in load('cv_metrics').iterrows():
    np.testing.assert_allclose(r.rmse, np.sqrt(mean_squared_error(oof.observed,oof[r.model])))
    np.testing.assert_allclose(r.mae, mean_absolute_error(oof.observed,oof[r.model]))
    np.testing.assert_allclose(r.r2, r2_score(oof.observed,oof[r.model]))
time=load('time_sensitivity').set_index('model')
assert time.loc['M3_time','parameters']==37
assert time.loc['M3_time','month_indicators']==19
assert (time.n==676).all()
assert time.loc['M3','competitors_p'] < .05 < time.loc['M3_time','competitors_p']
assert time.loc['M3','weight_p_holm'] < .05 < time.loc['M3_time','weight_p_holm']
nb=nbformat.read(root/'science_work_simple.ipynb',as_version=4)
nbformat.validate(nb)
source=(root/'analysis_retail.py').read_text()
chunks=re.split(r'^# %%([^\n]*)\n',source,flags=re.M)
blocks=[chunks[i+1].strip() for i in range(1,len(chunks),2) if '[markdown]' not in chunks[i]]
code_cells=[c for c in nb.cells if c.cell_type=='code']
assert len(code_cells)==len(blocks)==8
for i,(cell,block) in enumerate(zip(code_cells,blocks),1):
    assert cell.source == block
    assert cell.execution_count == i
    assert not any(o.output_type=='error' for o in cell.outputs)
    assert (root/'appendix'/f'code_{i:02}.py').read_text().strip()==block
# Check the visible notebook results as well as code/execution counters.
rendered=[]
for cell in code_cells:
    for output in cell.outputs:
        html=output.get('data',{}).get('text/html','')
        if '<table' in html:
            rendered.append(pd.read_html(StringIO(html),index_col=0)[0].reset_index(drop=True))
displayed_names=['categories','column_audit','descriptive','target_correlations',
    'model_comparison','main_coefficients','time_coefficients','joint_tests',
    'time_joint_test','time_sensitivity','vif','sensitivity',
    'weight_volume_sensitivity','effects','cv_metrics']
assert len(rendered)==len(displayed_names)
for name,frame in zip(displayed_names,rendered):
    pd.testing.assert_frame_equal(frame,load(name).round(5).reset_index(drop=True),
                                  check_dtype=False,check_exact=False,rtol=1e-8,atol=1e-8)
tex=(root/'coursework.tex').read_text()
for table,caption,label in re.findall(r'\\resulttable\{([^{}]+)\}\{([^{}]+)\}\{([^{}]+)\}',tex):
    assert (root/'report_tables'/f'{table}.tex').exists(),table
for fig in re.findall(r'\\resultfigure\{([^{}]+)\}',tex):
    if '#' not in fig: assert (root/'figures'/f'{fig}.png').exists(),fig
for file in re.findall(r'\\(?:input|VerbatimInput)(?:\[[^\]]*\])?\{([^{}]+)\}',tex):
    if '#' not in file: assert (root/file).exists(),file
labels=[x for x in re.findall(r'\\label\{([^{}]+)\}',tex) if '#' not in x]
labels+=re.findall(r'\\result(?:table|figure)\{[^{}]+\}\{[^{}]+\}\{([^{}]+)\}',tex)
assert len(labels)==len(set(labels)), 'Duplicate labels'
for ref in re.findall(r'\\(?:ref|eqref)\{([^{}]+)\}',tex): assert ref in labels,ref
# Check both the report and its separately editable cover.
# Rendered layout still requires a separate PDF build.
for filename in ['coursework.tex', 'titlepage.tex', 'defense_guide.tex']:
    stack=[]
    content=(root/filename).read_text()
    for action,env in re.findall(r'\\(begin|end)\{([^{}]+)\}',content):
        if action=='begin':stack.append(env)
        else: assert stack and stack.pop()==env,(filename,env)
    assert not stack,filename
    # A mistaken \[10pt] opens display math; \\[10pt] is a line break.
    uncommented='\n'.join(re.split(r'(?<!\\)%',line,maxsplit=1)[0]
                           for line in content.splitlines())
    math_stack=[]
    for delimiter in re.findall(r'(?<!\\)\\([\[\]()])',uncommented):
        if delimiter in ['[','(']:
            assert not math_stack,(filename,'Nested math delimiter',delimiter)
            math_stack.append(delimiter)
        else:
            expected='[' if delimiter==']' else '('
            assert math_stack and math_stack.pop()==expected,(filename,delimiter)
    assert not math_stack,(filename,'Unclosed math delimiter')
assert tex.index('\\workappendix{А}') > tex.index('\\chapter*{Список использованных источников}')
print('PASS: exported statistics, Holm, adjusted R2, out-of-training metrics,')
print('group/category separation, 15 rendered notebook tables, shared appendix source, TeX references.')
print('PDF rendering was not checked.')
