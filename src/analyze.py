"""Voice-of-customer analysis: what drives bad reviews, and what is fixing it worth?
Run after load_data.py. Writes tables and charts to reports/."""
import sqlite3, sys, pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "src")
from themes import tag, THEMES

OUT = pathlib.Path("reports"); OUT.mkdir(exist_ok=True)
d = pd.read_csv("data/review_base.csv")
d["bad"] = d.review_score <= 2
d["problem"] = (d.order_status != "delivered") | (d.days_vs_estimate > 3)   # undelivered, or 4+ days later than promised

# 1. Delivery performance vs review score ------------------------------------------------------
dl = d[d.order_status == "delivered"].copy()
dl["bucket"] = pd.cut(dl.days_vs_estimate, [-999, -7, 0, 3, 7, 14, 999],
                      labels=["7+ days early", "Early / on time", "1-3 days late", "4-7 days late", "8-14 days late", "15+ days late"])
buck = dl.groupby("bucket", observed=True).agg(orders=("bad", "size"), avg_score=("review_score", "mean"), pct_1_2_star=("bad", "mean")).round(3)
buck.to_csv(OUT / "delay_vs_score.csv")
fig, ax = plt.subplots(figsize=(7.5, 4)); ax.bar(buck.index, buck.avg_score, color=["#4C78A8"] * 3 + ["#E45756"] * 3)
ax.set_ylabel("Average review score"); ax.set_title("Reviews collapse once delivery is 4+ days late"); ax.set_ylim(0, 5)
for i, v in enumerate(buck.avg_score): ax.text(i, v + 0.07, f"{v:.1f}", ha="center")
plt.xticks(rotation=20); fig.tight_layout(); fig.savefig(OUT / "delay_vs_score.png", dpi=150); plt.close()

# 2. Complaint themes (commented reviews only) -------------------------------------------------
c = tag(d[d.comment.notna()].copy()); low = c[c.bad]
th = pd.DataFrame({"low_score_comments_mentioning": [int(low[k].sum()) for k in THEMES],
                   "pct_of_1_2_star_comments": [round(100 * low[k].mean(), 1) for k in THEMES],
                   "avg_score_when_mentioned": [round(c.loc[c[k], "review_score"].mean(), 2) for k in THEMES]}, index=list(THEMES))
th = th.sort_values("pct_of_1_2_star_comments", ascending=False); th.to_csv(OUT / "theme_summary.csv")
fig, ax = plt.subplots(figsize=(7.5, 4)); ax.barh(th.index[::-1], th.pct_of_1_2_star_comments[::-1], color="#4C78A8")
ax.set_xlabel("% of 1-2 star comments mentioning the theme"); ax.set_title("What 1-2 star reviewers complain about")
fig.tight_layout(); fig.savefig(OUT / "themes.png", dpi=150); plt.close()
cov = low.any_theme.mean(); fp = c[c.review_score == 5].any_theme.mean()

# 3. Perception vs fact: do "late" complainers actually get late orders? ---------------------------
lt = c[c["Late delivery"] & c.bad & (c.order_status == "delivered")]
persist = (lt.days_vs_estimate <= 0).mean()

# 4. What is fixing delivery worth? Counterfactual on average score ----------------------------
ok_avg = d.loc[~d.problem, "review_score"].mean()
actual = d.review_score.mean()
cf = d.review_score.where(~d.problem, ok_avg).mean()
share_bad_from_problem = d.loc[d.bad, "problem"].mean()
fix = pd.Series({"orders_with_review": len(d), "problem_orders_pct": round(100 * d.problem.mean(), 1),
                 "avg_score_now": round(actual, 3), "avg_score_if_problem_orders_scored_like_ok_orders": round(cf, 3),
                 "pct_of_all_1_2_star_reviews_from_problem_orders": round(100 * share_bad_from_problem, 1)})
fix.to_csv(OUT / "fix_delivery_counterfactual.csv", header=["value"])

# 5. Where do problems concentrate? ------------------------------------------------------------
cat = d.groupby("category").agg(orders=("problem", "size"), problem_rate=("problem", "mean"), avg_score=("review_score", "mean"))
cat = cat[cat.orders >= 500].sort_values("problem_rate", ascending=False).round(3); cat.to_csv(OUT / "problem_rate_by_category.csv")
st = d.groupby("state").agg(orders=("problem", "size"), problem_rate=("problem", "mean"), avg_score=("review_score", "mean"))
st = st[st.orders >= 500].sort_values("problem_rate", ascending=False).round(3); st.to_csv(OUT / "problem_rate_by_state.csv")

# 6. Does a bad first experience cut repeat purchases? (180-day window, orders before 1 Mar 2018) --
con = sqlite3.connect("data/olist.db")
o = pd.read_sql("""SELECT c.customer_unique_id cid, o.order_id, o.order_purchase_timestamp ts FROM orders o
                   JOIN customers c USING(customer_id) WHERE o.order_status='delivered'""", con, parse_dates=["ts"]).sort_values(["cid", "ts"])
first = o.groupby("cid").head(1).rename(columns={"ts": "first_ts"}); first = first[first.first_ts < "2018-03-01"]
nxt = o.merge(first[["cid", "first_ts"]], on="cid"); nxt = nxt[(nxt.ts > nxt.first_ts) & (nxt.ts <= nxt.first_ts + pd.Timedelta(days=180))]
first["repeat"] = first.cid.isin(nxt.cid)
f = first.merge(d.drop(columns=["customer_unique_id"]), on="order_id")
def ci(g):
    n, p = len(g), g["repeat"].mean(); se = np.sqrt(p * (1 - p) / n)
    return pd.Series({"customers": n, "repeat_rate_pct": round(100 * p, 2), "ci95_low": round(100 * (p - 1.96 * se), 2), "ci95_high": round(100 * (p + 1.96 * se), 2)})
f["first_order_experience"] = np.select([f.review_score <= 2, f.review_score == 3], ["1-2 stars", "3 stars"], "4-5 stars")
rep = pd.concat({"by review score": f.groupby("first_order_experience").apply(ci, include_groups=False),
                 "by delivery": f[f.order_status == "delivered"].assign(d=lambda x: np.where(x.days_vs_estimate > 3, "4+ days late", "on time / <=3 days late")).groupby("d").apply(ci, include_groups=False)})
rep.to_csv(OUT / "repeat_by_first_experience.csv")

# 7. Hand-validation sample (fill the blank column yourself) ------------------------------------
vs = low.sample(100, random_state=7)[["order_id", "review_score", "comment"] + list(THEMES)].copy()
vs["human_theme_correct (yes/no)"] = ""; vs.to_csv(OUT / "validation_sample.csv", index=False)

print(f"Orders with review {len(d):,}; with comment {len(c):,}; 1-2 star comments {len(low):,}")
print(f"Theme coverage of 1-2 star comments: {cov:.1%}; 5-star comments wrongly tagged: {fp:.1%}")
print(f"'Late' complainers whose order was actually on time: {persist:.1%} (n={len(lt)})")
print(buck.to_string(), "\n", th.to_string(), "\n", fix.to_string(), "\n", rep.to_string())
print(cat.head(5).to_string(), "\n", st.head(5).to_string())
