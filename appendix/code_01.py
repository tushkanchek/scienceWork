from pathlib import Path
import hashlib
import json
import importlib.metadata
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from IPython.display import display

ROOT = Path.cwd()
if not (ROOT / 'retail_price.csv').exists():
    ROOT = ROOT / 'scienceWork'
assert (ROOT / 'retail_price.csv').exists(), 'Run from the project directory'
for folder in ['results', 'figures', 'report_tables', 'appendix']:
    (ROOT / folder).mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
SEED = 20261030

def table(name, data):
    data.to_csv(ROOT / 'results' / (name + '.csv'), index=False)
    display(data.round(5))

def figure(name):
    plt.tight_layout()
    plt.savefig(ROOT / 'figures' / (name + '.png'), dpi=170,
                bbox_inches='tight')
    plt.show()
    plt.close()
