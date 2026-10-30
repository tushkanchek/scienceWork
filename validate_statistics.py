"""Reconstruct statistical exports directly with NumPy, without statsmodels fits."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
root=Path(__file__).resolve().parent
d=pd.read_csv(root/'retail_price.csv'); y=np.log(d.total_price.to_numpy())
base=['customers','comp_1','comp_2','comp_3','product_weight_g','product_photos_qty']
names=['ln_'+c if c!='product_photos_qty' else c for c in base]
cat=sorted(set(d.product_category_name)-{'garden_tools'})
coefs=pd.read_csv(root/'results/all_coefficients.csv')
models=pd.read_csv(root/'results/model_comparison.csv').set_index('model')
tests=pd.read_csv(root/'results/joint_tests.csv').set_index('test')
answers=[]
oof=pd.read_csv(root/'results/oof_predictions.csv')
loo=pd.read_csv(root/'results/leave_one_product_out.csv')
vifs=pd.read_csv(root/'results/vif.csv').set_index('term')
effects=pd.read_csv(root/'results/effects.csv').set_index('term')
for model in ['S1','S2','S3','M1','M2','M3','M3_time']:
    fields=base if not model.startswith('S') else ['customers','comp_'+model[1], 'product_weight_g','product_photos_qty']
    columns=['const']+['ln_'+c if c!='product_photos_qty' else c for c in fields]
    values=[np.ones(len(d))]+[np.log(d[c]) if c!='product_photos_qty' else d[c] for c in fields]
    if model in ['M2','M3','M3_time']:
        columns+=['cat_'+c for c in cat];values += [(d.product_category_name==c).astype(float) for c in cat]
    if model in ['M3','M3_time']:
        columns+=['product_score','ln_volume','freight_price'];values += [d.product_score,np.log(d.volume),d.freight_price]
    if model=='M3_time':
        months=pd.to_datetime(d.month_year,format='%d-%m-%Y').dt.to_period('M').astype(str)
        for month in sorted(months.unique())[1:]:
            columns.append('time_'+month);values.append((months==month).astype(float))
    X=np.column_stack(values); b=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@b
    inv=np.linalg.inv(X.T@X);meat=np.zeros((len(b),len(b)))
    for product in d.product_id.unique():
        idx=d.product_id==product;s=X[idx].T@e[idx];meat+=np.outer(s,s)
    V=(52/51)*((len(d)-1)/(len(d)-len(b)))*inv@meat@inv
    saved=coefs[coefs.model==model].set_index('term').loc[columns]
    np.testing.assert_allclose(b,saved.coef,atol=1e-9)
    np.testing.assert_allclose(np.sqrt(V.diagonal()),saved.se,atol=1e-8)
    half_width=stats.t.ppf(.975,51)*np.sqrt(V.diagonal())
    np.testing.assert_allclose(b-half_width,saved.low,atol=1e-8)
    np.testing.assert_allclose(b+half_width,saved.high,atol=1e-8)
    np.testing.assert_allclose(2*stats.t.sf(abs(b/np.sqrt(V.diagonal())),51),saved.p,atol=1e-8)
    r2=1-e@e/((y-y.mean())@(y-y.mean()));np.testing.assert_allclose(r2,models.loc[model,'r2'])
    if model in ['M1','M2','M3']:
        for fold in sorted(oof.fold.unique()):
            tr=(oof.fold!=fold).to_numpy();te=~tr
            train_beta=np.linalg.lstsq(X[tr],y[tr],rcond=None)[0]
            np.testing.assert_allclose(X[te]@train_beta,oof.loc[te,model],atol=1e-8)
        ids=[columns.index('ln_comp_'+str(j)) for j in [1,2,3]]
        F=b[ids]@np.linalg.solve(V[np.ix_(ids,ids)],b[ids])/3
        answers.append({'model':model,'F_competitors':F,'p_competitors':stats.f.sf(F,3,51)})
    if model=='M3_time':
        ids=[columns.index('ln_comp_'+str(j)) for j in [1,2,3]]
        F=b[ids]@np.linalg.solve(V[np.ix_(ids,ids)],b[ids])/3
        ts=pd.read_csv(root/'results/time_sensitivity.csv').set_index('model').loc[model]
        np.testing.assert_allclose(F,ts.competitors_F,rtol=1e-7)
        np.testing.assert_allclose(stats.f.sf(F,3,51),ts.competitors_p,rtol=1e-7)
        factors=list(vifs.index);ix=[columns.index(c) for c in factors]
        raw_p=2*stats.t.sf(abs(b[ix]/np.sqrt(np.diag(V)[ix])),51)
        order=np.argsort(raw_p);corrected=np.empty(9)
        corrected[order]=np.minimum(1,np.maximum.accumulate((9-np.arange(9))*raw_p[order]))
        tc=pd.read_csv(root/'results/time_coefficients.csv').set_index('term').loc[factors]
        np.testing.assert_allclose(corrected,tc.p_holm,rtol=1e-7,atol=1e-9)
        np.testing.assert_allclose(corrected[factors.index('ln_product_weight_g')],ts.weight_p_holm,rtol=1e-7)
        assert X.shape[1]==37 and np.linalg.matrix_rank(X)==37
        print('Calendar control: F=',F,'p=',ts.competitors_p,'weight Holm p=',ts.weight_p_holm)
    if model=='M3':
        for label,ids in [('competitors',[columns.index('ln_comp_'+str(j)) for j in [1,2,3]]),
             ('additional_block',[columns.index(c) for c in ['product_score','ln_volume','freight_price']]),
             ('categories',[columns.index('cat_'+c) for c in cat]),('overall',list(range(1,len(b))))]:
            F=b[ids]@np.linalg.solve(V[np.ix_(ids,ids)],b[ids])/len(ids)
            np.testing.assert_allclose(F,tests.loc[label,'F'],rtol=1e-7)
            np.testing.assert_allclose(stats.f.sf(F,len(ids),51),tests.loc[label,'p'],rtol=1e-6)
        for c in vifs.index:
            j=columns.index(c); others=np.delete(X,j,axis=1)
            err=X[:,j]-others@np.linalg.lstsq(others,X[:,j],rcond=None)[0]
            denom=((X[:,j]-X[:,j].mean())**2).sum()
            np.testing.assert_allclose(denom/(err@err),vifs.loc[c,'vif'],rtol=1e-8)
            step=np.log(1.1) if c.startswith('ln_') else (.1 if c=='product_score' else 1.)
            np.testing.assert_allclose(100*np.expm1(b[j]*step),effects.loc[c,'percent'],atol=1e-8)
            np.testing.assert_allclose(100*np.expm1((b[j]-half_width[j])*step),effects.loc[c,'low'],atol=1e-8)
            np.testing.assert_allclose(100*np.expm1((b[j]+half_width[j])*step),effects.loc[c,'high'],atol=1e-8)
        # Independently verify the diagnostic quadratic term.
        cx=np.log(d.customers.to_numpy());Q=np.column_stack([X,(cx-cx.mean())**2])
        qb=np.linalg.lstsq(Q,y,rcond=None)[0];qe=y-Q@qb
        qbread=np.linalg.inv(Q.T@Q);qmeat=np.zeros((Q.shape[1],Q.shape[1]))
        for product in d.product_id.unique():
            mask=(d.product_id==product).to_numpy();score=Q[mask].T@qe[mask]
            qmeat+=np.outer(score,score)
        qV=52/51*675/(676-Q.shape[1])*qbread@qmeat@qbread
        qF=qb[-1]**2/qV[-1,-1]
        np.testing.assert_allclose(qF,tests.loc['curvature','F'],rtol=1e-7)
        np.testing.assert_allclose(stats.f.sf(qF,1,51),tests.loc['curvature','p'],rtol=1e-7)
        for product in d.product_id.unique():
            keep=(d.product_id!=product).to_numpy()
            reduced=np.linalg.lstsq(X[keep],y[keep],rcond=None)[0]
            saved_loo=loo[loo.removed_product==product].set_index('term')
            for c in saved_loo.index:
                np.testing.assert_allclose(reduced[columns.index(c)],saved_loo.loc[c,'coef'],atol=1e-8)
        print('Residual skewness:',stats.skew(e))
        print('Condition number, scaled design:',np.linalg.cond(np.column_stack([np.ones(len(d)),(X[:,1:]-X[:,1:].mean(0))/X[:,1:].std(0)])))
print(pd.DataFrame(answers).to_string(index=False))
print('PASS: seven models including calendar sensitivity, CR1 covariance and p-values, main and calendar joint tests, VIF,')
print('effect estimates, 52 exclusions, and predictions for all group folds.')
