splits = list(GroupKFold(n_splits=5).split(df, groups=df.product_id))
def coverage_ok(splits):
    return all(set(df.iloc[tr].product_category_name) == set(categories)
               for tr, te in splits)
fold_method = 'GroupKFold'
if not coverage_ok(splits):
    fold_method = 'category_balanced_product_folds'
    products = df[['product_id', 'product_category_name']].drop_duplicates()
    rng = np.random.default_rng(SEED)
    assignment, loads = {}, np.zeros(5, dtype=int)
    for cat in sorted(categories):
        ids = products.loc[products.product_category_name == cat, 'product_id'].to_numpy()
        ids = rng.permutation(np.sort(ids))
        for start in range(0, len(ids), 5):
            order = np.argsort(loads, kind='stable')
            for product, fold in zip(ids[start:start+5], order):
                assignment[product] = int(fold)
                loads[fold] += 1
    fold_vector = df.product_id.map(assignment).to_numpy()
    splits = [(np.where(fold_vector != f)[0], np.where(fold_vector == f)[0])
              for f in range(5)]
assert coverage_ok(splits)
oof = pd.DataFrame({'product_id': df.product_id, 'observed': df.ln_total_price,
                    'fold': -1})
fold_rows = []
for fold, (tr, te) in enumerate(splits):
    train, test = df.iloc[tr], df.iloc[te]
    assert set(train.product_id).isdisjoint(set(test.product_id))
    assert len(te) > 0
    oof.loc[te, 'fold'] = fold
    preds = {'Mean': np.repeat(train.ln_total_price.mean(), len(te))}
    for name in ['M1', 'M2', 'M3']:
        factors, categorical = specs[name]
        Xtrain = design(train, factors, categorical)
        assert np.linalg.matrix_rank(Xtrain) == Xtrain.shape[1]
        fitted = sm.OLS(train.ln_total_price, Xtrain).fit()
        preds[name] = fitted.predict(design(test, factors, categorical))
    for name, pred in preds.items():
        oof.loc[te, name] = np.asarray(pred)
        fold_rows.append({'fold': fold, 'model': name, 'test_rows': len(te),
            'test_products': test.product_id.nunique(),
            'rmse': np.sqrt(mean_squared_error(test.ln_total_price, pred)),
            'mae': mean_absolute_error(test.ln_total_price, pred)})
assert (oof.fold >= 0).all() and not oof.isna().any().any()
assert oof.groupby('product_id').fold.nunique().max() == 1
oof.to_csv(ROOT / 'results' / 'oof_predictions.csv', index=False)
fold_metrics = pd.DataFrame(fold_rows)
fold_metrics.to_csv(ROOT / 'results' / 'fold_metrics.csv', index=False)
cv = pd.DataFrame([{'model': name,
    'rmse': np.sqrt(mean_squared_error(oof.observed, oof[name])),
    'mae': mean_absolute_error(oof.observed, oof[name]),
    'r2': r2_score(oof.observed, oof[name]),
    'fold_rmse_sd': fold_metrics.loc[fold_metrics.model == name, 'rmse'].std()}
    for name in ['Mean', 'M1', 'M2', 'M3']])
table('cv_metrics', cv)
print('Fold allocation:', fold_method)
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].bar(cv.model, cv.rmse, color='#386a91')
ax[0].set(ylabel='RMSE логарифма вне обучения', xlabel='Модель')
ax[1].scatter(oof.observed, oof.M3, s=12, alpha=.4)
bounds = [min(oof.observed.min(), oof.M3.min()), max(oof.observed.max(), oof.M3.max())]
ax[1].plot(bounds, bounds, 'k--')
ax[1].set(xlabel='Наблюдаемый ln(Y)', ylabel='Предсказанный ln(Y), M3')
figure('validation')
