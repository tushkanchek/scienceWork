raw = pd.read_csv(ROOT / 'retail_price.csv')
df = raw.copy()
df['date'] = pd.to_datetime(df['month_year'], format='%d-%m-%Y')
log_fields = ['total_price', 'customers', 'comp_1', 'comp_2', 'comp_3',
              'product_weight_g', 'volume']
checks = {
    'rows': len(df), 'products': df.product_id.nunique(),
    'categories': df.product_category_name.nunique(),
    'months': df.date.nunique(), 'missing': int(raw.isna().sum().sum()),
    'duplicates': int(raw.duplicated().sum()),
    'duplicate_product_month': int(df.duplicated(['product_id', 'date']).sum()),
    'nonpositive_log_values': int((df[log_fields] <= 0).sum().sum()),
    'negative_freight': int((df.freight_price < 0).sum()),
    'zero_freight': int((df.freight_price == 0).sum()),
    'calendar_mismatch': int(((df.date.dt.month != df.month) |
                              (df.date.dt.year != df.year)).sum()),
}
for name in ['missing', 'duplicates', 'duplicate_product_month',
             'nonpositive_log_values', 'negative_freight', 'calendar_mismatch']:
    assert checks[name] == 0, (name, checks[name])
assert np.isfinite(df.select_dtypes('number')).all().all()
assert df.groupby('product_id').product_category_name.nunique().max() == 1
relative_gap = abs(df.total_price - df.unit_price * df.qty) / df.total_price
checks['identity_within_0_3_percent'] = int((relative_gap < 0.003).sum())
checks['identity_max_gap'] = float(relative_gap.max())
checks['category_month_customer_max_unique'] = int(df.groupby(
    ['product_category_name', 'date']).customers.nunique().max())
checks['start'] = str(df.date.min().date())
checks['end'] = str(df.date.max().date())
for col in log_fields:
    df['ln_' + col] = np.log(df[col])
BASE = ['ln_customers', 'ln_comp_1', 'ln_comp_2', 'ln_comp_3',
        'ln_product_weight_g', 'product_photos_qty']
EXTRA = ['product_score', 'ln_volume', 'freight_price']
FACTORS = BASE + EXTRA
LABELS = dict(zip(FACTORS, ['Покупатели', 'Конкурент 1', 'Конкурент 2',
    'Конкурент 3', 'Вес', 'Фотографии', 'Рейтинг', 'Объём', 'Доставка']))
category_counts = df.groupby('product_category_name').agg(
    rows=('product_id', 'size'), products=('product_id', 'nunique'),
    median_total=('total_price', 'median')).reset_index()
# Ties are resolved lexicographically, without using the outcome.
base_category = category_counts.sort_values(
    ['products', 'product_category_name'], ascending=[False, True]).iloc[0, 0]
categories = [base_category] + sorted(set(df.product_category_name) - {base_category})
DUMMIES = ['cat_' + c for c in categories[1:]]

def design(data, factors, categorical=False):
    X = data[factors].astype(float).copy()
    if categorical:
        for cat, col in zip(categories[1:], DUMMIES):
            X[col] = (data.product_category_name == cat).astype(float)
    return sm.add_constant(X, has_constant='add')

checks['base_category'] = base_category
print(json.dumps(checks, ensure_ascii=False, indent=2))
table('categories', category_counts)
audit = []
for c in raw.columns:
    row = {'column': c, 'dtype': str(raw[c].dtype),
           'missing': int(raw[c].isna().sum()), 'unique': raw[c].nunique()}
    if pd.api.types.is_numeric_dtype(raw[c]):
        row.update(min=float(raw[c].min()), max=float(raw[c].max()),
            varying_products=int((df.groupby('product_id')[c].nunique() > 1).sum()))
    audit.append(row)
table('column_audit', pd.DataFrame(audit))
