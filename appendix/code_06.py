steps = {c: np.log(1.1) if c.startswith('ln_') else 1 for c in FACTORS}
steps['product_score'] = .1
effects = main[['term']].copy()
for source, target in [('coef','percent'), ('low','low'), ('high','high')]:
    effects[target] = [100 * np.expm1(row[source] * steps[row.term])
                       for _, row in main.iterrows()]
effects['step'] = ['10%' if c.startswith('ln_') else
                  ('0.1' if c == 'product_score' else '1') for c in FACTORS]
table('effects', effects)
fig, ax = plt.subplots(figsize=(9, 5))
ax.errorbar(effects.percent, range(9),
    xerr=[effects.percent-effects.low, effects.high-effects.percent], fmt='o', capsize=3)
ax.axvline(0, color='black', ls='--')
ax.set_yticks(range(9), [LABELS[c] + ' (+' + step + ')'
                         for c, step in zip(effects.term, effects.step)])
ax.set_xlabel('Изменение геометрического среднего, %; индивидуальные 95% ДИ')
figure('effects')
