"""Validate numerical exports and report references without compiling TeX."""
from pathlib import Path
import hashlib
import json
import re
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
# Check nested environments; rendered layout requires a separate PDF build.
stack=[]
for action,env in re.findall(r'\\(begin|end)\{([^{}]+)\}',tex):
    if action=='begin':stack.append(env)
    else: assert stack.pop()==env,env
assert not stack
assert tex.index('Приложение А') > tex.index('\\chapter*{Литература}')
print('PASS: exported statistics, Holm, adjusted R2, out-of-training metrics,')
print('group/category separation, executed notebook, shared appendix source, TeX references.')
print('PDF rendering was not checked.')
