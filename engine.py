"""FlowInsights engine: plain-English (and Hinglish) question -> answer. No API key needed."""
import re
from datetime import date, timedelta
from difflib import get_close_matches
import numpy as np
import pandas as pd

REQUIRED = {"date", "product", "quantity", "revenue"}
PRODUCTS = [("Notebook", "Stationery", 120, 9), ("Headphones", "Electronics", 850, 5),
            ("Backpack", "Fashion", 650, 4), ("Water Bottle", "Home", 280, 8),
            ("Keyboard", "Electronics", 1100, 3), ("Desk Lamp", "Home", 540, 4)]
REGIONS = [("North", 9), ("South", 7), ("East", 4), ("West", 6)]

def sample_data(end=None):
    """Fictional sales (90 days) with clear winners and weekend peaks."""
    end = end or date.today()
    rng = np.random.RandomState(42)
    pw = np.array([p[3] for p in PRODUCTS], float); pw /= pw.sum()
    rw = np.array([r[1] for r in REGIONS], float); rw /= rw.sum()
    rows = []
    for off in range(89, -1, -1):
        d = pd.Timestamp(end - timedelta(days=off))
        for _ in range(int(rng.randint(10, 19) * (1.3 if d.weekday() >= 5 else 1.0))):
            pi, ri, q = rng.choice(len(PRODUCTS), p=pw), rng.choice(len(REGIONS), p=rw), int(rng.randint(1, 6))
            name, cat, price, _w = PRODUCTS[pi]
            rows.append((d, name, cat, REGIONS[ri][0], q, q * price))
    return pd.DataFrame(rows, columns=["date", "product", "category", "region", "quantity", "revenue"])

def prepare_data(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("Missing required CSV columns: " + ", ".join(sorted(missing)))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    for c in ("region", "category"):
        if c in df.columns: df[c] = df[c].astype("string").fillna("Unknown")
    if "region" not in df.columns: df["region"] = "All regions"
    df["product"] = df["product"].astype("string").fillna("Unknown")
    df = df.dropna(subset=["date", "quantity", "revenue"])
    if df.empty:
        raise ValueError("No usable rows found. Check date, quantity and revenue values.")
    return df

METRICS = {"revenue": ["revenue", "sales", "income", "earning", "earnings", "earned", "kamai", "bikri", "amount", "paisa"],
           "quantity": ["quantity", "units", "unit", "pieces", "qty", "kitne"],
           "orders": ["orders", "order", "transactions", "bills"]}
GROUPS = {"product": ["product", "products", "item", "items", "saman", "cheez", "cheezein"],
          "region": ["region", "regions", "state", "states", "area", "areas", "location"],
          "category": ["category", "categories"],
          "month": ["monthly", "trend", "monthwise"],
          "day": ["daily", "daywise", "roz", "date"]}
PERIODS = [("last 30 days", "last30"), ("past 30 days", "last30"), ("pichle mahine", "last_month"),
           ("last month", "last_month"), ("is mahine", "this_month"), ("this month", "this_month"),
           ("is hafte", "this_week"), ("this week", "this_week"), ("last week", "last_week"),
           ("pichle hafte", "last_week"), ("yesterday", "yesterday"), ("kal", "yesterday"),
           ("today", "today"), ("aaj", "today")]
ASC_WORDS = ["lowest", "least", "worst", "bottom", "kam", "weakest"]

def _lookup(token, table):
    for key, words in table.items():
        if token in words: return key
    if len(token) >= 5:
        for key, words in table.items():
            if get_close_matches(token, words, n=1, cutoff=0.8): return key
    return None

def period_range(code, ref):
    if code == "today": return ref, ref
    if code == "yesterday": return ref - timedelta(1), ref - timedelta(1)
    if code == "this_week": return ref - timedelta(ref.weekday()), ref
    if code == "last_week":
        s = ref - timedelta(ref.weekday() + 7); return s, s + timedelta(6)
    if code == "this_month": return ref.replace(day=1), ref
    if code == "last_month":
        e = ref.replace(day=1) - timedelta(1); return e.replace(day=1), e
    if code == "last30": return ref - timedelta(29), ref
    return None

def parse(question, df):
    """Returns a plan dict, or None if the question is not understood."""
    q = re.sub(r"[^\w\s-]", " ", question.lower())
    q = q.replace("-", "")
    period = None
    for phrase, code in PERIODS:
        if re.search(r"\b" + phrase + r"\b", q):
            period = code; q = re.sub(r"\b" + phrase + r"\b", " ", q); break
    metric = group = None
    for t in q.split():
        metric = metric or _lookup(t, METRICS)
        group = group or _lookup(t, GROUPS)
    if "over time" in q: group = group or "month"
    filters = {}
    for col in ("product", "region", "category"):
        if col in df.columns:
            for val in df[col].dropna().astype(str).unique():
                if re.search(r"\b" + re.escape(val.lower()) + r"\b", q): filters[col] = val
    if not (metric or group or period or filters): return None
    chart = "pie" if "pie" in q else "line" if "line" in q else "bar" if "bar" in q else None
    asc = any(w in q.split() for w in ASC_WORDS)
    m = re.search(r"(?:top|best|bottom|worst|lowest|first)\s*(\d+)", q) or \
        re.search(r"\b(\d+)\s*(?:products|items|regions|categories)", q)
    limit = int(m.group(1)) if m else None
    if limit is None and re.search(r"\b(which|kaunsa|kaunsi|kaunse|kaun|konsa|konsi)\b", q): limit = 1
    group = group or "product"
    if group not in df.columns and group not in ("month", "day"): group = "product"
    if group in ("month", "day"): limit, chart, asc = None, chart or "line", True
    else: limit = max(1, min(limit or (5 if group == "product" else 10), 50))
    return {"metric": metric or "revenue", "group": group, "period": period, "filters": filters,
            "limit": limit, "asc": asc, "chart": chart or "bar"}

def _fmt(metric, v):
    if metric == "revenue": return f"-₹{abs(v):,.0f}" if v < 0 else f"₹{v:,.0f}"
    return f"{v:,.0f} {'units' if metric == 'quantity' else 'orders'}"

def run(df, plan):
    """Returns dict(result, headline, explain, sql) or None when no rows match."""
    ref = df["date"].max().date()
    w = df
    rng = period_range(plan["period"], ref) if plan["period"] else None
    if rng: w = w[(w["date"].dt.date >= rng[0]) & (w["date"].dt.date <= rng[1])]
    for c, v in plan["filters"].items(): w = w[w[c].astype(str) == v]
    if w.empty: return None
    g, m = plan["group"], plan["metric"]
    key = (w["date"].dt.to_period("M").astype(str) if g == "month" else
           w["date"].dt.strftime("%Y-%m-%d") if g == "day" else w[g].astype(str))
    res = (w.groupby(key).size() if m == "orders" else w.groupby(key)[m].sum()).reset_index()
    res.columns = ["label", "value"]
    if g in ("month", "day"): res = res.sort_values("label")
    else:
        res = res.sort_values("value", ascending=plan["asc"])
        if plan["limit"]: res = res.head(plan["limit"])
    top = res.loc[res["value"].idxmax()] if g in ("month", "day") else res.iloc[0]
    if g in ("month", "day"): headline = f"Peak {g}: {top['label']} with {_fmt(m, top['value'])}."
    elif plan["asc"]: headline = f"{top['label']} is lowest with {_fmt(m, top['value'])}."
    else: headline = f"{top['label']} leads with {_fmt(m, top['value'])}."
    names = {"revenue": "revenue", "quantity": "units sold", "orders": "number of orders"}
    pl = {"today": "today", "yesterday": "yesterday", "this_week": "this week", "last_week": "last week",
          "this_month": "this month", "last_month": "last month", "last30": "in the last 30 days", None: "across all data"}
    ex = (f"{names[m].capitalize()} per {g}" if g in ("month", "day") else
          f"{'Lowest' if plan['asc'] else 'Top'} {len(res)} by {g}, measured as {names[m]}") + f", {pl[plan['period']]}"
    if plan["filters"]: ex += ", for " + ", ".join(plan["filters"].values())
    where = [f"{c} = '{v}'" for c, v in plan["filters"].items()] + ([f"date BETWEEN '{rng[0]}' AND '{rng[1]}'"] if rng else [])
    agg = "COUNT(*)" if m == "orders" else f"SUM({m})"
    gx = {"month": "strftime('%Y-%m', date)", "day": "date"}.get(g, g)
    sql = f"SELECT {gx} AS label, {agg} AS value FROM sales" + (" WHERE " + " AND ".join(where) if where else "") + \
          f" GROUP BY label ORDER BY " + ("label" if g in ("month", "day") else f"value {'ASC' if plan['asc'] else 'DESC'}") + \
          (f" LIMIT {plan['limit']}" if plan["limit"] else "")
    return {"result": res.reset_index(drop=True), "headline": headline, "explain": ex + ".", "sql": sql}

# ---------- Advanced: automatic insights, "why" drill-down, anomalies, shareable summary ----------
def _window(df, ref, days, offset=0):
    end = ref - timedelta(offset); start = end - timedelta(days - 1)
    return df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

def breakdown(df, dim, days=7):
    """Revenue by `dim` for the latest `days` vs the `days` before, sorted by change."""
    ref = df["date"].max().date()
    cur, prev = _window(df, ref, days), _window(df, ref, days, days)
    t = pd.concat([prev.groupby(dim)["revenue"].sum().rename("previous"),
                   cur.groupby(dim)["revenue"].sum().rename("current")], axis=1).fillna(0)
    t["change"] = t["current"] - t["previous"]
    t["change_pct"] = np.where(t["previous"] > 0, t["change"] / t["previous"].replace(0, np.nan) * 100, np.nan)
    t.index.name = dim
    return t.sort_values("change").reset_index()

def anomalies(df, days=30, z=2.0):
    """Days in the latest window whose revenue is unusually high or low."""
    ref = df["date"].max().date()
    daily = _window(df, ref, days).groupby(df["date"].dt.date)["revenue"].sum()
    if len(daily) < 7 or daily.std() == 0: return []
    zs = (daily - daily.mean()) / daily.std()
    return [(str(d), float(daily[d]), "high" if zs[d] > 0 else "low")
            for d in zs.abs().sort_values(ascending=False).index if abs(zs[d]) >= z][:3]

def insights(df, days=7):
    """Rule-based digest. Returns dict(ok, message|points, ...). Never claims a cause, only what changed."""
    ref = df["date"].max().date()
    span = (ref - df["date"].min().date()).days + 1
    if span < days * 2:
        return {"ok": False, "message": f"Need at least {days * 2} days of data to compare periods (you have {span})."}
    cur, prev = _window(df, ref, days), _window(df, ref, days, days)
    c, p = float(cur["revenue"].sum()), float(prev["revenue"].sum())
    if p <= 0: return {"ok": False, "message": "The previous period has no revenue to compare against."}
    pct = (c - p) / p * 100
    points = [f"Revenue {'rose' if pct >= 0 else 'fell'} {abs(pct):.0f}% vs the previous {days} days "
              f"({_fmt('revenue', c)} vs {_fmt('revenue', p)})."]
    prod, reg = breakdown(df, "product", days), breakdown(df, "region", days)
    drop, gain = prod.iloc[0], prod.iloc[-1]
    if drop["change"] < 0: points.append(f"Biggest product drop: {drop['product']} ({_fmt('revenue', drop['change'])}).")
    if gain["change"] > 0: points.append(f"Biggest product gain: {gain['product']} (+{_fmt('revenue', gain['change'])}).")
    mover = reg.iloc[reg["change"].abs().argmax()]
    if mover["change"] != 0 and reg["region"].nunique() > 1:
        points.append(f"{mover['region']} moved the most by region ({'+' if mover['change'] > 0 else ''}{_fmt('revenue', mover['change'])}).")
    wd = df.groupby([df["date"].dt.date, df["date"].dt.day_name()])["revenue"].sum().groupby(level=1).mean()
    points.append(f"Best weekday: {wd.idxmax()} (about {_fmt('revenue', wd.max())} per day).")
    for d, v, kind in anomalies(df)[:1]:
        points.append(f"Unusual day: {d} was unusually {kind} ({_fmt('revenue', v)}).")
    tip = None
    if drop["change"] < 0 and pct < 0:
        r = reg[reg["change"] < 0].iloc[0]["region"] if (reg["change"] < 0).any() else None
        tip = f"Worth checking stock, price or promotions for {drop['product']}" + (f", especially in {r}." if r else ".")
    return {"ok": True, "ref": ref, "days": days, "pct": pct, "current": c, "previous": p,
            "points": points, "tip": tip, "products": prod, "regions": reg}

def whatsapp_summary(df, days=7, shop="My shop"):
    ins = insights(df, days)
    if not ins["ok"]: return ins["message"]
    lines = [f"📊 {shop}: last {days} days (to {ins['ref']})"] + [f"• {x}" for x in ins["points"][:4]]
    if ins["tip"]: lines.append(f"👉 {ins['tip']}")
    lines.append("Made with FlowInsights (demo/fictional data unless you uploaded your own).")
    return "\n".join(lines)
