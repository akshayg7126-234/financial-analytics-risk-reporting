"""Credit-risk scorecard: Weight of Evidence (WoE) -> logistic regression -> points -> risk bands.

Method (standard bank scorecard practice)
 1. Bin each predictor (numeric -> equal-frequency bins; categorical -> as is).
 2. WoE = ln(%good / %bad) per bin; Information Value (IV) ranks predictors.
 3. Logistic regression on WoE-transformed inputs predicts P(default).
 4. Scale to points: base 600 at 30:1 good:bad odds, +20 points doubles the odds (PDO=20).
 5. Cut the score into 5 risk bands.
 grade / int_rate are EXCLUDED from the model: they are the lender's own pricing outputs.
"""
import json, numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, roc_curve, brier_score_loss

R = Path(__file__).resolve().parent.parent
NUM = {"fico": 6, "dti": 6, "revol_util": 6, "annual_inc": 5, "delinq_2yrs": None, "inq_last_6m": None,
       "emp_length": None}
CAT = ["term", "purpose", "home_ownership"]
PDO, BASE_SCORE, BASE_ODDS = 20, 600, 30

def make_bins(train):
    """Return {feature: bin edges or category list}."""
    spec = {}
    for f, q in NUM.items():
        if q:
            edges = np.unique(np.quantile(train[f], np.linspace(0, 1, q + 1)))
            edges[0], edges[-1] = -np.inf, np.inf
            spec[f] = edges
        else:   # low-cardinality ints: cap high values into one bin
            cap = {"delinq_2yrs": 2, "inq_last_6m": 3, "emp_length": 10}[f]
            spec[f] = ("cap", cap)
    return spec

def binify(df, f, spec):
    s = spec[f]
    if isinstance(s, tuple):
        v = df[f].clip(upper=s[1])
        if f == "emp_length":
            v = pd.cut(v, [-1, 0, 2, 5, 9, 10], labels=["<1y", "1-2y", "3-5y", "6-9y", "10y+"]).astype(str)
        return v.astype(str)
    return pd.cut(df[f], s).astype(str)

def woe_table(train, f, spec, y="default_flag"):
    b = binify(train, f, spec) if f in NUM else train[f].astype(str)
    t = pd.DataFrame({"bin": b, "bad": train[y]})
    g = t.groupby("bin").agg(n=("bad", "size"), bad=("bad", "sum"))
    g["good"] = g.n - g.bad
    tot_g, tot_b = g.good.sum(), g.bad.sum()
    g["woe"] = np.log(((g.good + .5) / tot_g) / ((g.bad + .5) / tot_b))
    g["bad_rate"] = g.bad / g.n
    g["iv_part"] = ((g.good / tot_g) - (g.bad / tot_b)) * g.woe
    g["feature"] = f
    return g.reset_index()

def apply_woe(df, tables, spec):
    out = pd.DataFrame(index=df.index)
    for f, tb in tables.items():
        b = binify(df, f, spec) if f in NUM else df[f].astype(str)
        out[f] = b.map(tb.set_index("bin").woe).fillna(0.0)
    return out

def ks_stat(y, p):
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))

def run():
    loans = pd.read_csv(R / "data/loans.csv")
    feats = list(NUM) + CAT
    train, test = train_test_split(loans, test_size=0.3, random_state=42, stratify=loans.default_flag)
    spec = make_bins(train)
    tables = {f: woe_table(train, f, spec) for f in feats}
    iv = pd.DataFrame({"feature": feats, "iv": [tables[f].iv_part.sum() for f in feats]}).sort_values("iv", ascending=False)
    iv["strength"] = pd.cut(iv.iv, [-1, .02, .1, .3, .5, 99], labels=["useless", "weak", "medium", "strong", "very strong"])
    keep = iv[iv.iv >= 0.02].feature.tolist()                       # drop useless predictors
    tables = {f: tables[f] for f in keep}

    Xtr, Xte = apply_woe(train, tables, spec), apply_woe(test, tables, spec)
    model = LogisticRegression(C=1.0, max_iter=1000).fit(Xtr, train.default_flag)
    p_tr, p_te = model.predict_proba(Xtr)[:, 1], model.predict_proba(Xte)[:, 1]

    # points scaling
    factor = PDO / np.log(2)
    offset = BASE_SCORE - factor * np.log(BASE_ODDS)
    n = len(keep)
    pts = []
    for f in keep:
        b = model.coef_[0][keep.index(f)]
        tb = tables[f].copy()
        tb["points"] = (-(b * tb.woe) - model.intercept_[0] / n) * factor + offset / n
        pts.append(tb)
    card = pd.concat(pts)[["feature", "bin", "n", "bad_rate", "woe", "points"]]
    card["points"] = card.points.round().astype(int)

    def score(df):
        X = apply_woe(df, tables, spec)
        logit = model.intercept_[0] + X.values @ model.coef_[0]
        return offset + factor * (-logit)
    loans["score"] = score(loans).round().astype(int)
    loans["pd_model"] = model.predict_proba(apply_woe(loans, tables, spec))[:, 1]
    loans["sample"] = np.where(loans.loan_id.isin(test.loan_id), "test", "train")

    # risk bands from TRAIN score quantiles (20/40/60/80th pct)
    cuts = np.quantile(loans.loc[loans["sample"] == "train", "score"], [.2, .4, .6, .8])
    labels = ["E - Very high risk", "D - High risk", "C - Medium risk", "B - Low risk", "A - Very low risk"]
    loans["risk_band"] = pd.cut(loans.score, [-np.inf, *cuts, np.inf], labels=labels).astype(str)

    t = loans[loans["sample"] == "test"]
    bands = loans.groupby("risk_band").agg(loans=("loan_id", "size"), exposure=("loan_amnt", "sum"),
            avg_score=("score", "mean"), avg_pd_model=("pd_model", "mean"), actual_default_rate=("default_flag", "mean"),
            avg_rate=("int_rate", "mean")).reset_index().sort_values("avg_score", ascending=False)
    bands_test = t.groupby("risk_band").default_flag.mean().rename("test_default_rate")
    bands = bands.merge(bands_test, on="risk_band")
    fpr, tpr, _ = roc_curve(t.default_flag, t.pd_model)
    metrics = {
        "n_loans": int(len(loans)), "n_train": int(len(train)), "n_test": int(len(test)),
        "overall_default_rate": float(loans.default_flag.mean()),
        "auc_train": float(roc_auc_score(train.default_flag, p_tr)),
        "auc_test": float(roc_auc_score(test.default_flag, p_te)),
        "gini_test": float(2 * roc_auc_score(test.default_flag, p_te) - 1),
        "ks_test": ks_stat(test.default_flag, p_te),
        "brier_test": float(brier_score_loss(test.default_flag, p_te)),
        "calibration_test": {"mean_predicted": float(p_te.mean()), "mean_actual": float(test.default_flag.mean())},
        "features_kept": keep, "intercept": float(model.intercept_[0]),
        "coefficients": dict(zip(keep, map(float, model.coef_[0]))),
        "score_cuts": [float(c) for c in cuts], "pdo": PDO, "base_score": BASE_SCORE, "base_odds": BASE_ODDS,
        "bands_monotonic_test": bool(bands.sort_values("avg_score").test_default_rate.is_monotonic_decreasing),
        "roc": {"fpr": np.round(fpr[::max(1, len(fpr) // 60)], 4).tolist(), "tpr": np.round(tpr[::max(1, len(tpr) // 60)], 4).tolist()},
    }
    out = R / "outputs"
    card.to_csv(out / "scorecard_points.csv", index=False)
    iv.to_csv(out / "information_value.csv", index=False)
    bands.to_csv(out / "risk_bands.csv", index=False)
    loans.drop(columns=["pd_model"]).assign(pd_model=loans.pd_model.round(5)).to_csv(R / "data/loans_scored.csv", index=False)
    json.dump(metrics, open(out / "model_metrics.json", "w"), indent=2)
    return metrics, bands, iv, card

if __name__ == "__main__":
    m, bands, iv, card = run()
    print(iv.to_string(index=False))
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k not in ("roc", "coefficients")})
    print(bands.round(4).to_string(index=False))
