def fit_cluster(X, data):
    assert np.linalg.matrix_rank(X) == X.shape[1], 'Rank deficient design'
    ols = sm.OLS(data.ln_total_price, X).fit()
    robust = ols.get_robustcov_results(cov_type='cluster',
        groups=data.product_id.to_numpy(), use_correction=True,
        df_correction=True, use_t=True)
    return ols, robust

specs = {f'S{j}': (['ln_customers', f'ln_comp_{j}',
    'ln_product_weight_g', 'product_photos_qty'], False) for j in [1, 2, 3]}
specs.update({'M1': (BASE, False), 'M2': (BASE, True), 'M3': (FACTORS, True)})
fits, matrices, fit_rows = {}, {}, []
for name, (factors, categorical) in specs.items():
    X = design(df, factors, categorical)
    ols, robust = fit_cluster(X, df)
    fits[name] = (ols, robust)
    matrices[name] = X
    fit_rows.append({'model': name, 'n': int(ols.nobs), 'parameters': X.shape[1],
        'rank': np.linalg.matrix_rank(X), 'cov_rank': np.linalg.matrix_rank(robust.cov_params()),
        'r2': ols.rsquared, 'adjusted_r2': ols.rsquared_adj})
# Sensitivity only: 19 calendar year-month indicators, base January 2017.
# Keep the same rows, factors, CR1 correction and product clusters.
month_labels = df.date.dt.to_period('M').astype(str)
month_indicators = pd.get_dummies(month_labels, prefix='time', drop_first=True,
                                  dtype=float)
assert month_indicators.shape[1] == 19
Xtime = pd.concat([matrices['M3'], month_indicators], axis=1)
fits['M3_time'] = fit_cluster(Xtime, df)
matrices['M3_time'] = Xtime
ols_time, robust_time = fits['M3_time']
fit_rows.append({'model': 'M3_time', 'n': int(ols_time.nobs),
    'parameters': Xtime.shape[1], 'rank': np.linalg.matrix_rank(Xtime),
    'cov_rank': np.linalg.matrix_rank(robust_time.cov_params()),
    'r2': ols_time.rsquared, 'adjusted_r2': ols_time.rsquared_adj})
table('model_comparison', pd.DataFrame(fit_rows))

coef_rows = []
for name, (ols, r) in fits.items():
    ci = r.conf_int()
    for j, col in enumerate(matrices[name].columns):
        coef_rows.append({'model': name, 'term': col, 'coef': r.params[j],
            'se': r.bse[j], 't': r.tvalues[j], 'p': r.pvalues[j],
            'low': ci[j,0], 'high': ci[j,1]})
coefs = pd.DataFrame(coef_rows)
coefs.to_csv(ROOT / 'results' / 'all_coefficients.csv', index=False)
main = coefs[(coefs.model == 'M3') & coefs.term.isin(FACTORS)].copy()
main['p_holm'] = multipletests(main.p, method='holm')[1]
main['holm_reject'] = main.p_holm < .05
table('main_coefficients', main)
time_coefficients = coefs[(coefs.model == 'M3_time') & coefs.term.isin(FACTORS)].copy()
time_coefficients['p_holm'] = multipletests(time_coefficients.p, method='holm')[1]
time_coefficients['holm_reject'] = time_coefficients.p_holm < .05
table('time_coefficients', time_coefficients)


# Reject singular restrictions rather than silently changing degrees of freedom.
def joint(model, cols, label):
    ols, r = fits[model]
    names = list(matrices[model].columns)
    A = np.eye(len(names))[[names.index(c) for c in cols]]
    rank = np.linalg.matrix_rank(A @ r.cov_params() @ A.T)
    if rank != len(cols):
        return dict(test=label, model=model, q=len(cols), rank=rank,
                    F=np.nan, p=np.nan, df_denom=np.nan)
    t = r.f_test(A)
    return dict(test=label, model=model, q=len(cols), rank=rank,
        F=float(t.fvalue), p=float(t.pvalue), df_denom=float(t.df_denom))

joint_rows = [joint('M3', BASE[1:4], 'competitors'),
    joint('M3', EXTRA, 'additional_block'),
    joint('M3', DUMMIES, 'categories'),
    joint('M3', FACTORS + DUMMIES, 'overall')]
Xq = matrices['M3'].copy()
Xq['customers_sq'] = (df.ln_customers - df.ln_customers.mean()) ** 2
matrices['M3q'] = Xq
fits['M3q'] = fit_cluster(Xq, df)
joint_rows.append(joint('M3q', ['customers_sq'], 'curvature'))
table('joint_tests', pd.DataFrame(joint_rows))
# Additional exploratory check; no search over alternative time specifications.
time_test = joint('M3_time', BASE[1:4], 'competitors_time')
table('time_joint_test', pd.DataFrame([time_test]))
time_rows = []
for model, coefficients, test in [
        ('M3', main, joint_rows[0]), ('M3_time', time_coefficients, time_test)]:
    time_rows.append({'model': model, 'n': len(df),
        'parameters': matrices[model].shape[1],
        'month_indicators': 19 if model == 'M3_time' else 0,
        'competitors_F': test['F'], 'competitors_p': test['p'],
        'weight_p_holm': float(coefficients.set_index('term').loc[
            'ln_product_weight_g', 'p_holm'])})
table('time_sensitivity', pd.DataFrame(time_rows))
print('Calendar check: the competitors result depends on specification. '
      'Failing to reject at 5% is not proof of no relationship.')
