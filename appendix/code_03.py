original = log_fields + ['product_photos_qty', 'product_score', 'freight_price']
desc = df[original].describe().T.reset_index(names='variable')
table('descriptive', desc)
pearson = df[['ln_total_price'] + FACTORS].corr()
spearman = df[['ln_total_price'] + FACTORS].corr(method='spearman')
pearson.to_csv(ROOT / 'results' / 'pearson.csv')
spearman.to_csv(ROOT / 'results' / 'spearman.csv')
table('target_correlations', pd.DataFrame({'factor': FACTORS,
    'pearson': pearson.loc[FACTORS, 'ln_total_price'].values,
    'spearman': spearman.loc[FACTORS, 'ln_total_price'].values}))
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
for a, c, title in zip(ax, ['total_price', 'ln_total_price'],
                      ['Суммарная стоимость продаж', 'Логарифм суммы продаж']):
    a.hist(df[c], bins=30, color='#386a91', edgecolor='white')
    a.set(xlabel=title, ylabel='Число наблюдений')
figure('distributions')
fig, ax = plt.subplots(2, 2, figsize=(10, 7))
for a, c in zip(ax.flat, BASE[:4]):
    a.scatter(df[c], df.ln_total_price, s=12, alpha=.4)
    a.set(xlabel='ln: ' + LABELS[c], ylabel='ln суммы продаж')
figure('relationships')
fig, ax = plt.subplots(figsize=(9, 7))
im = ax.imshow(pearson, cmap='RdBu_r', vmin=-1, vmax=1)
labels = ['Отклик'] + [LABELS[c] for c in FACTORS]
ax.set_xticks(range(10), labels, rotation=55, ha='right')
ax.set_yticks(range(10), labels)
for i in range(10):
    for j in range(10):
        ax.text(j, i, f'{pearson.iloc[i,j]:.2f}', ha='center', va='center', fontsize=7)
fig.colorbar(im, ax=ax, shrink=.8)
figure('correlations')
fig, ax = plt.subplots(figsize=(10, 5))
ax.boxplot([df.loc[df.product_category_name == c, 'ln_total_price']
            for c in categories], tick_labels=categories, orientation='horizontal')
ax.set_xlabel('ln суммы продаж')
figure('categories')
