"""Build notebook, LaTeX tables and code appendices from shared sources."""
from pathlib import Path
import re
import nbformat
import pandas as pd
ROOT = Path(__file__).resolve().parent
source = (ROOT/'analysis_retail.py').read_text()
chunks = re.split(r'^# %%([^\n]*)\n', source, flags=re.M)
cells=[]; code=[]
for i in range(1,len(chunks),2):
    kind, body=chunks[i],chunks[i+1].strip()
    if '[markdown]' in kind:
        cells.append(nbformat.v4.new_markdown_cell('\n'.join(
            line[2:] if line.startswith('# ') else line.lstrip('#') for line in body.splitlines())))
    else:
        cells.append(nbformat.v4.new_code_cell(body));code.append(body)
nb=nbformat.v4.new_notebook(cells=cells,metadata={
    'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}})
notebook_path = ROOT/'science_work_simple.ipynb'
if notebook_path.exists():
    previous = nbformat.read(notebook_path, as_version=4)
    if [(c.cell_type, c.source) for c in previous.cells] == [(c.cell_type, c.source) for c in cells]:
        nb = previous  # Keep executed outputs when source has not changed.
nbformat.write(nb, notebook_path)
for i,body in enumerate(code,1):
    (ROOT/'appendix'/f'code_{i:02}.py').write_text(body+'\n')
labels=dict(zip(['ln_customers','ln_comp_1','ln_comp_2','ln_comp_3',
 'ln_product_weight_g','product_photos_qty','product_score','ln_volume','freight_price'],
 ['Покупатели','Конкурент 1','Конкурент 2','Конкурент 3','Вес','Фотографии','Рейтинг','Объём','Доставка']))
original={'total_price':'Сумма продаж','customers':'Покупатели','comp_1':'Конкурент 1',
 'comp_2':'Конкурент 2','comp_3':'Конкурент 3','product_weight_g':'Вес',
 'product_photos_qty':'Фотографии','product_score':'Рейтинг','volume':'Объём','freight_price':'Доставка'}
def esc(x):
    return str(x).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def fmt(x):
    if isinstance(x,(float,int)) and not isinstance(x,bool):
        if pd.isna(x): return '---'
        if 0 < abs(x) < 0.0005:
            return '$' + f'{x:.3g}'.replace('.', '{,}') + '$'
        return f'{x:.3f}'.replace('.',',')
    return esc(x)
def pv(x):
    return '$<0{,}001$' if x < .001 else fmt(x)
def out(name,headers,rows,align=None):
    align=align or ('l'+'r'*(len(headers)-1))
    lines=[r'\begin{tabular}{'+align+'}',r'\toprule',
           ' & '.join(headers)+r' \\',r'\midrule']
    lines += [' & '.join(row)+r' \\' for row in rows]
    lines += [r'\bottomrule',r'\end{tabular}']
    (ROOT/'report_tables'/f'{name}.tex').write_text('\n'.join(lines)+'\n')
def read(name):return pd.read_csv(ROOT/'results'/f'{name}.csv')
x=read('descriptive')
out('descriptive',['Переменная','Среднее','Медиана','Ст. откл.','Мин.','Макс.'],
 [[original[r.variable]]+[fmt(r[c]) for c in ['mean','50%','std','min','max']] for _,r in x.iterrows()])
x=read('categories');out('categories',['Категория','Строк','Товаров'],
 [[esc(r.product_category_name),str(r.rows),str(r.products)] for _,r in x.iterrows()])
x=read('model_comparison');out('models',['Модель','Параметров','$R^2$','$R^2_{adj}$'],
 [[('M3 + месяцы' if r.model=='M3_time' else r.model),str(r.parameters),fmt(r.r2),fmt(r.adjusted_r2)] for _,r in x.iterrows()])
x=read('main_coefficients');out('coefficients',['Фактор',r'$\widehat\beta$','SE','$p$','$p_{Holm}$',r'95\%-ный ДИ'],
 [[labels[r.term],fmt(r.coef),fmt(r.se),pv(r.p),pv(r.p_holm),f'[{fmt(r.low)}; {fmt(r.high)}]'] for _,r in x.iterrows()])
x=read('joint_tests');names={'competitors':'Цены конкурентов','additional_block':'Три новых фактора',
 'categories':'Категории','overall':'Все факторы','curvature':'Квадрат ln покупателей'}
out('tests',['Гипотеза','$q$','$F$','$p$'],[[names[r.test],str(r.q),fmt(r.F),pv(r.p)] for _,r in x.iterrows()])
x=read('vif');out('vif',['Фактор','VIF'],[[labels[r.term],fmt(r.vif)] for _,r in x.iterrows()])
x=read('sensitivity');out('sensitivity',['Фактор','Полная оценка','Минимум','Максимум','Смен знака'],
 [[labels[r.term],fmt(r.full),fmt(r['min']),fmt(r['max']),str(r.sign_changes)] for _,r in x.iterrows()])
x=read('effects');out('effects',['Фактор','Изменение фактора',r'Оценка, \%',r'95\%-ный ДИ, \%'],
 [[labels[r.term],esc(r.step),fmt(r.percent),f'[{fmt(r.low)}; {fmt(r.high)}]'] for _,r in x.iterrows()])
x=read('cv_metrics');out('cv',['Модель','RMSE','MAE','$R^2$','SD(RMSE)'],
 [[r.model,fmt(r.rmse),fmt(r.mae),fmt(r.r2),fmt(r.fold_rmse_sd)] for _,r in x.iterrows()])
x=read('all_coefficients');x=x[x.model.isin(['M1','M2','M3']) & x.term.isin(labels)]
pivot=x.pivot(index='term',columns='model',values='coef').reindex(labels)
out('coefficient_comparison',['Фактор','M1','M2','M3'],
 [[labels[c]]+[fmt(row[m]) for m in ['M1','M2','M3']] for c,row in pivot.iterrows()])
x=read('target_correlations');out('correlations',['Фактор','Пирсон','Спирмен'],
 [[labels[r.factor],fmt(r.pearson),fmt(r.spearman)] for _,r in x.iterrows()])
x=read('all_coefficients');x=x[(x.model=='M3') & x.term.str.startswith('cat_')]
out('category_coefficients',['Категория',r'$\widehat\alpha$','SE',r'95\%-ный ДИ'],
 [[esc(r.term[4:]),fmt(r.coef),fmt(r.se),f'[{fmt(r.low)}; {fmt(r.high)}]'] for _,r in x.iterrows()])
print('Notebook, tables and code appendices generated')

x=read('time_sensitivity')
out('time_sensitivity',['Спецификация','Параметров','$p$ конкурентов','$p_{Holm}$ веса'],
 [[('M3 + месяцы' if r.model=='M3_time' else 'M3'),str(r.parameters),
   pv(r.competitors_p),pv(r.weight_p_holm)] for _,r in x.iterrows()])
x=read('time_coefficients')
out('time_coefficients',['Фактор',r'$\widehat\beta$','SE','$p$','$p_{Holm}$',r'95\%-ный ДИ'],
 [[labels[r.term],fmt(r.coef),fmt(r.se),pv(r.p),pv(r.p_holm),f'[{fmt(r.low)}; {fmt(r.high)}]'] for _,r in x.iterrows()])
