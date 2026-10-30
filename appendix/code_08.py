r = fits['M3'][1]
np.testing.assert_allclose(r.pvalues, 2 * stats.t.sf(abs(r.tvalues), 51))
np.testing.assert_allclose(r.conf_int()[:,0], r.params-stats.t.ppf(.975,51)*r.bse)
X = matrices['M3'].to_numpy()
resid = np.asarray(fits['M3'][0].resid)
bread = np.linalg.inv(X.T @ X)
meat = np.zeros_like(bread)
for product in df.product_id.unique():
    idx = (df.product_id == product).to_numpy()
    score = X[idx].T @ resid[idx]
    meat += np.outer(score, score)
n, p = X.shape
g = df.product_id.nunique()
manual_cov = (g/(g-1))*((n-1)/(n-p))*bread @ meat @ bread
np.testing.assert_allclose(manual_cov, r.cov_params(), rtol=1e-6, atol=1e-8)
manual_beta = np.linalg.lstsq(X, df.ln_total_price, rcond=None)[0]
np.testing.assert_allclose(manual_beta, r.params, rtol=1e-8, atol=1e-8)
manifest = {'checks': checks, 'seed': SEED, 'fold_method': fold_method,
    'time_sensitivity': {'reference_month': str(month_labels.min()),
                         'month_indicators': month_indicators.shape[1]},
    'sha256': hashlib.sha256((ROOT/'retail_price.csv').read_bytes()).hexdigest(),
    'versions': {p: importlib.metadata.version(p) for p in
                 ['numpy','pandas','scipy','statsmodels','scikit-learn']},
    'validated': ['OLS coefficients', 'cluster CR1 covariance', 't p-values',
                  'confidence intervals', 'group separation', 'category coverage',
                  'full rank training matrices', 'complete OOF predictions']}
(ROOT/'results'/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
print('Completed:', json.dumps(manifest, ensure_ascii=False, indent=2))
