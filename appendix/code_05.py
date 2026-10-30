X = matrices['M3']
vif = pd.DataFrame({'term': FACTORS, 'vif': [variance_inflation_factor(
    X.to_numpy(), X.columns.get_loc(c)) for c in FACTORS]})
table('vif', vif)
ols, robust = fits['M3']
e = ols.resid
fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
ax[0].scatter(ols.fittedvalues, e, s=12, alpha=.4)
ax[0].axhline(0, color='black', lw=1)
ax[0].set(xlabel='Предсказанный ln(Y)', ylabel='Остаток')
ax[1].scatter(ols.fittedvalues, np.sqrt(abs(e / e.std())), s=12, alpha=.4)
ax[1].set(xlabel='Предсказанный ln(Y)', ylabel='Корень |стандарт. остатка|')
stats.probplot(e, dist='norm', plot=ax[2])
ax[2].set(title='Q–Q остатков', xlabel='Квантили нормального распределения',
          ylabel='Квантили остатков')
figure('diagnostics')
loo = []
for product in sorted(df.product_id.unique()):
    subset = df.loc[df.product_id != product]
    Xsub = design(subset, FACTORS, True)
    model, _ = fit_cluster(Xsub, subset)
    for term in FACTORS:
        loo.append({'removed_product': product, 'term': term,
                    'coef': model.params[term]})
loo = pd.DataFrame(loo)
loo.to_csv(ROOT / 'results' / 'leave_one_product_out.csv', index=False)
sensitivity = loo.groupby('term').coef.agg(['min','max']).reindex(FACTORS)
sensitivity['full'] = main.set_index('term').coef
sensitivity['sign_changes'] = [int((np.sign(loo.loc[loo.term == c, 'coef']) !=
    np.sign(sensitivity.loc[c, 'full'])).sum()) for c in FACTORS]
table('sensitivity', sensitivity.reset_index())
variants = []
for omit in ['ln_volume', 'ln_product_weight_g']:
    model, r = fit_cluster(design(df, [c for c in FACTORS if c != omit], True), df)
    for j, term in enumerate(model.model.exog_names):
        if term in FACTORS:
            variants.append({'omitted': omit, 'term': term,
                'coef': r.params[j], 'low': r.conf_int()[j,0], 'high': r.conf_int()[j,1]})
table('weight_volume_sensitivity', pd.DataFrame(variants))
