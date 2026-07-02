#!/usr/bin/env python3
"""
Euro Analyst Compass - data fetcher
Fetches macroeconomic indicators for European countries from free, legal APIs
(Eurostat, World Bank, Adzuna) and writes data/data.json for the static site.

Usage:
    python fetch_data.py            # real fetch (needs internet)
    python fetch_data.py --sample   # generate realistic demo data (offline)

Adzuna (job listings) is optional. Set env vars ADZUNA_APP_ID / ADZUNA_APP_KEY
(free account at https://developer.adzuna.com). Without them, job data is skipped
and any previously fetched job data in data/data.json is kept.
"""

import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "data.json")
YEARS_BACK = 11  # keep ~10 years of history

# ---------------------------------------------------------------------------
# Countries (EU + EFTA). code: Eurostat geo code
# ---------------------------------------------------------------------------
COUNTRIES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia",
    "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia",
    "FI": "Finland", "FR": "France", "DE": "Germany", "EL": "Greece",
    "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LV": "Latvia",
    "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia",
    "SI": "Slovenia", "ES": "Spain", "SE": "Sweden",
    "NO": "Norway", "CH": "Switzerland", "IS": "Iceland",
}

# EF English Proficiency Index 2024 scores (static; no free API exists).
# Source: EF EPI 2024 public rankings. Update once a year.
ENGLISH_PROFICIENCY = {
    "NL": 636, "NO": 610, "SE": 608, "HR": 607, "PT": 605, "DK": 603,
    "EL": 602, "AT": 600, "DE": 598, "BE": 594, "RO": 589, "FI": 583,
    "PL": 580, "BG": 574, "HU": 573, "SK": 567, "EE": 566, "LU": 562,
    "LT": 561, "CZ": 560, "LV": 556, "CH": 551, "SI": 619, "IS": 590,
    "ES": 538, "IT": 534, "FR": 531, "CY": 540, "MT": 620, "IE": 700,
}

# ---------------------------------------------------------------------------
# Indicator definitions
#   direction: +1 = higher is better, -1 = lower is better
#   weight: contribution to the total score
# ---------------------------------------------------------------------------
INDICATORS = {
    "gdp_growth":     {"name": "GDP growth", "unit": "% y/y", "direction": +1, "weight": 1.0},
    "inflation":      {"name": "Inflation (HICP)", "unit": "% y/y", "direction": -1, "weight": 1.0},
    "unemployment":   {"name": "Unemployment rate", "unit": "%", "direction": -1, "weight": 1.0},
    "net_salary":     {"name": "Net annual salary (single, avg wage)", "unit": "EUR/yr", "direction": +1, "weight": 1.5},
    "price_level":    {"name": "Price level (EU27=100, household consumption)", "unit": "index", "direction": -1, "weight": 1.0},
    "price_food":     {"name": "Food price level (EU27=100)", "unit": "index", "direction": -1, "weight": 0.5},
    "price_energy":   {"name": "Energy & housing price level (EU27=100)", "unit": "index", "direction": -1, "weight": 0.5},
    "real_income_gr": {"name": "Real household income growth per capita", "unit": "% y/y", "direction": +1, "weight": 1.0},
    "tax_wedge":      {"name": "Tax & contributions wedge (gross vs net)", "unit": "%", "direction": -1, "weight": 1.0},
    "life_expect":    {"name": "Life expectancy (health system proxy)", "unit": "years", "direction": +1, "weight": 1.0},
    "life_satisf":    {"name": "Life satisfaction (0-10)", "unit": "rating", "direction": +1, "weight": 1.0},
    "english":        {"name": "English proficiency (EF EPI)", "unit": "score", "direction": +1, "weight": 0.5},
    # job-market indicators (from Adzuna, latest snapshot only)
    "data_jobs":      {"name": "Data analyst/engineer/science job ads", "unit": "ads", "direction": +1, "weight": 1.0},
    "jobs_per_100k":  {"name": "Data job ads per 100k population", "unit": "ads/100k", "direction": +1, "weight": 1.5},
    "data_salary":    {"name": "Average advertised data salary", "unit": "EUR/yr", "direction": +1, "weight": 1.0},
    "remote_share":   {"name": "Share of data job ads that are remote", "unit": "%", "direction": +1, "weight": 0.5},
}

# ---------------------------------------------------------------------------
# Eurostat helper
# ---------------------------------------------------------------------------
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

def http_get_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "euro-analyst-compass/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"  retry {attempt+1}/{retries} for {url[:120]}... ({e})")
            time.sleep(3 * (attempt + 1))
    return None

def eurostat_series(dataset, params):
    """Return {geo: {year: value}} for a Eurostat dataset (JSON-stat 2.0)."""
    this_year = datetime.now().year
    p = dict(params)
    p["format"] = "JSON"
    p["sinceTimePeriod"] = str(this_year - YEARS_BACK)
    url = EUROSTAT_BASE + dataset + "?" + urllib.parse.urlencode(p, doseq=True)
    js = http_get_json(url)
    if not js or "value" not in js:
        print(f"  !! Eurostat fetch failed for {dataset}")
        return {}
    dims = js["id"]
    sizes = js["size"]
    geo_idx = {v: k for k, v in js["dimension"]["geo"]["category"]["index"].items()}
    time_idx = {v: k for k, v in js["dimension"]["time"]["category"]["index"].items()}
    # strides for flattened index
    strides, s = {}, 1
    for d in reversed(dims):
        strides[d] = s
        s *= sizes[dims.index(d)]
    out = {}
    for flat, val in js["value"].items():
        flat = int(flat)
        g = geo_idx[(flat // strides["geo"]) % sizes[dims.index("geo")]]
        t = time_idx[(flat // strides["time"]) % sizes[dims.index("time")]]
        if g in COUNTRIES and val is not None:
            out.setdefault(g, {})[t[:4]] = round(float(val), 2)
    return out

# ---------------------------------------------------------------------------
# Real fetchers
# ---------------------------------------------------------------------------
def fetch_eurostat_all():
    """Fetch all Eurostat-based indicators. Returns {indicator: {geo: {year: value}}}."""
    result = {}
    jobs = [
        ("gdp_growth", "tec00115", {"unit": "CLV_PCH_PRE", "na_item": "B1GQ"}),
        ("inflation", "prc_hicp_aind", {"unit": "RCH_A_AVG", "coicop": "CP00"}),
        ("unemployment", "une_rt_a", {"unit": "PC_ACT", "sex": "T", "age": "Y15-74"}),
        ("net_salary", "earn_nt_net", {"currency": "EUR", "estruct": "NET",
                                       "ecase": "P1_NCH_AW100"}),
        ("gross_salary", "earn_nt_net", {"currency": "EUR", "estruct": "GRS",
                                         "ecase": "P1_NCH_AW100"}),
        ("price_level", "prc_ppp_ind", {"na_item": "PLI_EU27_2020", "ppp_cat": "E011"}),
        ("price_food", "prc_ppp_ind", {"na_item": "PLI_EU27_2020", "ppp_cat": "A010101"}),
        ("price_energy", "prc_ppp_ind", {"na_item": "PLI_EU27_2020", "ppp_cat": "A010405"}),
        ("real_income_gr", "tec00113", {"unit": "CLV_PCH_PRE", "na_item": "B6G"}),
        ("life_expect", "demo_mlexpec", {"sex": "T", "age": "Y_LT1"}),
        ("life_satisf", "ilc_pw01a", {"sex": "T", "age": "Y_GE16",
                                      "indic_wb": "LIFESAT", "unit": "RTG"}),
        ("population", "tps00001", {"indic_de": "JAN"}),
    ]
    for key, dataset, params in jobs:
        print(f"Fetching {key} ({dataset})...")
        result[key] = eurostat_series(dataset, params)
        time.sleep(1)

    # Fallbacks for PPP categories if codes yield nothing (codes occasionally change):
    if not result.get("price_level"):
        result["price_level"] = eurostat_series("prc_ppp_ind",
            {"na_item": "PLI_EU27_2020", "ppp_cat": "A01"})
    # tax wedge = 100 * (1 - net/gross)
    tw = {}
    for g, years in result.get("gross_salary", {}).items():
        for y, gross in years.items():
            net = result.get("net_salary", {}).get(g, {}).get(y)
            if net and gross:
                tw.setdefault(g, {})[y] = round(100.0 * (1 - net / gross), 2)
    result["tax_wedge"] = tw
    result.pop("gross_salary", None)
    return result

# Adzuna country endpoints (Adzuna covers these European markets)
ADZUNA_COUNTRIES = {"AT": "at", "BE": "be", "CH": "ch", "DE": "de", "ES": "es",
                    "FR": "fr", "IT": "it", "NL": "nl", "PL": "pl"}

def fetch_adzuna(population):
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("Adzuna keys not set - skipping job data.")
        return {}
    out = {}
    query = 'data analyst OR "data engineer" OR "data scientist"'
    for geo, cc in ADZUNA_COUNTRIES.items():
        base = f"https://api.adzuna.com/v1/api/jobs/{cc}/search/1"
        common = {"app_id": app_id, "app_key": app_key, "what_or": "data analyst,data engineer,data scientist",
                  "results_per_page": 1, "content-type": "application/json"}
        js = http_get_json(base + "?" + urllib.parse.urlencode(common))
        time.sleep(1)
        js_rem = http_get_json(base + "?" + urllib.parse.urlencode({**common, "what_and": "remote"}))
        time.sleep(1)
        if not js:
            continue
        total = js.get("count", 0)
        remote = js_rem.get("count", 0) if js_rem else 0
        salary = js.get("mean")  # Adzuna returns mean salary estimate in local currency
        rec = {"data_jobs": total,
               "remote_share": round(100.0 * remote / total, 1) if total else None,
               "data_salary": round(salary) if salary else None}
        pop = population.get(geo, {})
        if pop:
            latest_pop = pop[max(pop)]
            rec["jobs_per_100k"] = round(total / (latest_pop / 100000.0), 2)
        out[geo] = rec
        print(f"  Adzuna {geo}: {total} ads, {remote} remote")
    return out

# ---------------------------------------------------------------------------
# Jooble (official free API, https://jooble.org/api/about)
# Uses a single endpoint api.jooble.org with location filter per country.
# ---------------------------------------------------------------------------
JOOBLE_COUNTRIES = {"EL": "Greece", "CY": "Cyprus", "PT": "Portugal",
                    "IE": "Ireland", "DK": "Denmark", "FI": "Finland",
                    "NO": "Norway", "SE": "Sweden", "CZ": "Czech Republic",
                    "HU": "Hungary", "RO": "Romania", "BG": "Bulgaria",
                    "HR": "Croatia", "SK": "Slovakia", "SI": "Slovenia",
                    "EE": "Estonia", "LV": "Latvia", "LT": "Lithuania",
                    "LU": "Luxembourg", "IS": "Iceland", "MT": "Malta"}

def http_post_json(url, payload, retries=3):
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, method="POST",
                headers={"Content-Type": "application/json",
                         "User-Agent": "euro-analyst-compass/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"  retry {attempt+1}/{retries} for {url[:80]}... ({e})")
            time.sleep(3 * (attempt + 1))
    return None

def fetch_jooble(population, skip_geos):
    key = os.environ.get("JOOBLE_API_KEY")
    if not key:
        print("Jooble key not set - skipping Jooble job data.")
        return {}
    out = {}
    url = f"https://api.jooble.org/api/{key}"
    kw = "data analyst"
    for geo, country_name in JOOBLE_COUNTRIES.items():
        if geo in skip_geos:
            continue
        js = http_post_json(url, {"keywords": kw, "location": country_name, "page": 1})
        time.sleep(1)
        js_rem = http_post_json(url, {"keywords": kw + " remote", "location": country_name, "page": 1})
        time.sleep(1)
        if not js:
            continue
        total = js.get("totalCount", 0)
        remote = js_rem.get("totalCount", 0) if js_rem else 0
        rec = {"data_jobs": total,
               "remote_share": round(100.0 * min(remote, total) / total, 1) if total else None}
        pop = population.get(geo, {})
        if pop:
            latest_pop = pop[max(pop)]
            rec["jobs_per_100k"] = round(total / (latest_pop / 100000.0), 2)
        out[geo] = rec
        print(f"  Jooble {geo}: {total} ads, {remote} remote")
    return out

# ---------------------------------------------------------------------------
# Sample data generator (offline demo)
# ---------------------------------------------------------------------------
def make_sample():
    random.seed(42)
    this_year = datetime.now().year
    years = [str(y) for y in range(this_year - YEARS_BACK, this_year)]
    base = {
        # geo: (gdp, infl, unemp, net_salary, PLI, food, energy, realinc, tax, lifeexp, satisf)
        "DE": (1.2, 2.2, 3.5, 34000, 108, 104, 118, 0.8, 38, 81.2, 7.1),
        "NL": (1.8, 2.4, 3.6, 38000, 115, 102, 122, 1.1, 33, 81.9, 7.5),
        "CH": (1.6, 1.2, 4.3, 62000, 160, 152, 135, 1.0, 22, 84.0, 7.6),
        "AT": (1.1, 2.6, 5.2, 33000, 112, 110, 115, 0.6, 33, 81.6, 7.3),
        "SE": (1.9, 1.9, 7.8, 33500, 118, 111, 108, 1.2, 30, 83.2, 7.4),
        "DK": (2.0, 1.7, 5.4, 41000, 138, 122, 112, 1.4, 36, 81.5, 7.6),
        "NO": (1.5, 2.8, 3.9, 45000, 142, 140, 95, 0.9, 28, 83.3, 7.4),
        "FI": (0.9, 1.8, 7.6, 31500, 122, 114, 110, 0.5, 31, 81.9, 7.7),
        "IE": (4.5, 2.1, 4.4, 40000, 135, 117, 128, 2.0, 26, 82.4, 7.2),
        "FR": (1.1, 2.0, 7.3, 29500, 108, 112, 105, 0.7, 30, 82.9, 7.0),
        "BE": (1.3, 2.5, 5.6, 30500, 113, 108, 116, 0.6, 40, 82.1, 7.2),
        "LU": (1.7, 2.3, 5.5, 47000, 132, 121, 110, 1.0, 29, 82.7, 7.2),
        "ES": (2.4, 2.4, 11.5, 24000, 91, 96, 108, 1.5, 24, 83.7, 7.1),
        "PT": (2.1, 2.2, 6.4, 17500, 84, 94, 102, 1.6, 26, 82.4, 6.8),
        "IT": (0.8, 1.6, 7.0, 24500, 98, 103, 112, 0.4, 32, 83.5, 6.8),
        "EL": (2.2, 2.7, 9.8, 15500, 82, 100, 96, 1.8, 25, 81.9, 6.6),
        "CY": (2.8, 2.0, 5.6, 21500, 88, 104, 92, 1.7, 20, 82.9, 6.9),
        "MT": (4.2, 2.5, 3.0, 20500, 90, 105, 88, 2.1, 22, 83.0, 7.0),
        "PL": (3.2, 3.6, 2.9, 14500, 68, 79, 84, 3.0, 25, 78.5, 7.3),
        "CZ": (2.0, 2.8, 2.6, 17500, 79, 88, 108, 1.8, 26, 79.8, 7.2),
        "SK": (2.1, 3.3, 5.4, 13500, 76, 89, 96, 1.6, 27, 78.1, 6.9),
        "HU": (2.3, 4.4, 4.2, 12500, 66, 84, 74, 1.9, 33, 76.9, 6.8),
        "SI": (2.4, 2.4, 3.7, 18500, 85, 95, 98, 1.7, 30, 81.9, 7.4),
        "HR": (2.8, 3.1, 5.6, 14500, 74, 92, 87, 2.2, 28, 78.6, 6.9),
        "RO": (2.9, 4.9, 5.5, 11500, 57, 74, 72, 3.2, 28, 76.6, 7.3),
        "BG": (2.6, 3.4, 4.3, 10500, 55, 76, 68, 3.4, 24, 75.8, 6.2),
        "EE": (1.4, 3.8, 7.2, 18500, 88, 95, 92, 1.2, 24, 79.1, 7.0),
        "LV": (1.6, 3.2, 6.6, 14500, 78, 92, 88, 1.9, 28, 75.9, 6.9),
        "LT": (2.2, 3.0, 6.9, 16500, 76, 91, 86, 2.4, 27, 76.7, 7.1),
        "IS": (2.3, 3.5, 3.7, 44000, 148, 132, 78, 1.3, 27, 83.1, 7.6),
    }
    keys = ["gdp_growth", "inflation", "unemployment", "net_salary", "price_level",
            "price_food", "price_energy", "real_income_gr", "tax_wedge",
            "life_expect", "life_satisf"]
    trends = {"net_salary": 0.03, "life_expect": 0.1}
    series = {k: {} for k in keys}
    series["population"] = {}
    pops = {"DE": 84.5, "FR": 68.4, "IT": 58.9, "ES": 48.6, "PL": 36.6, "RO": 19.0,
            "NL": 17.9, "BE": 11.8, "CZ": 10.9, "SE": 10.6, "PT": 10.6, "EL": 10.4,
            "HU": 9.6, "AT": 9.2, "CH": 8.9, "BG": 6.4, "DK": 6.0, "FI": 5.6,
            "NO": 5.6, "SK": 5.4, "IE": 5.3, "HR": 3.9, "LT": 2.9, "SI": 2.1,
            "LV": 1.9, "EE": 1.4, "CY": 0.9, "LU": 0.67, "MT": 0.55, "IS": 0.39}
    for geo, vals in base.items():
        for i, k in enumerate(keys):
            s = {}
            v = vals[i]
            for j, y in enumerate(years):
                noise = random.uniform(-0.6, 0.6) * (abs(v) * 0.15 + 0.2)
                growth = 1 + trends.get(k, 0) * (j - len(years) + 1)
                # 2022-2023 inflation spike for realism
                spike = 0
                if k == "inflation" and y in ("2022", "2023"):
                    spike = 6 if y == "2022" else 3
                if k == "real_income_gr" and y in ("2022", "2023"):
                    spike = -3
                s[y] = round(v * growth + noise + spike, 2)
            series[k][geo] = s
        series["population"][geo] = {years[-1]: int(pops[geo] * 1e6)}
    # sample job data
    jobs = {}
    job_base = {"DE": (5200, 62000, 22), "NL": (2100, 58000, 28), "CH": (1400, 95000, 18),
                "AT": (620, 54000, 16), "SE": (900, 52000, 30), "FR": (3100, 50000, 20),
                "BE": (760, 52000, 19), "ES": (1900, 38000, 25), "IT": (1300, 40000, 14),
                "PL": (1500, 28000, 33), "EL": (240, 26000, 21), "CY": (95, 32000, 26)}
    for geo, (n, sal, rem) in job_base.items():
        pop = series["population"][geo][years[-1]]
        jobs[geo] = {"data_jobs": n, "data_salary": sal, "remote_share": rem,
                     "jobs_per_100k": round(n / (pop / 100000), 2)}
    return series, jobs

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def latest(series_geo):
    if not series_geo:
        return None
    y = max(series_geo)
    return series_geo[y], y

def compute_scores(series, jobs):
    """Rank-normalised 0-100 score per indicator + weighted total per country."""
    values = {}  # indicator -> {geo: latest value}
    for ind in INDICATORS:
        vals = {}
        if ind in ("data_jobs", "jobs_per_100k", "data_salary", "remote_share"):
            for g, rec in jobs.items():
                if rec.get(ind) is not None:
                    vals[g] = rec[ind]
        elif ind == "english":
            vals = {g: v for g, v in ENGLISH_PROFICIENCY.items() if g in COUNTRIES}
        else:
            for g, s in series.get(ind, {}).items():
                lv = latest(s)
                if lv:
                    vals[g] = lv[0]
        values[ind] = vals

    scores = {g: {} for g in COUNTRIES}
    for ind, meta in INDICATORS.items():
        vals = values[ind]
        if len(vals) < 2:
            continue
        ordered = sorted(vals.items(), key=lambda kv: kv[1],
                         reverse=(meta["direction"] > 0))
        n = len(ordered)
        for rank, (g, v) in enumerate(ordered):
            score = round(100 * (n - 1 - rank) / (n - 1), 1)
            scores[g][ind] = {"value": v, "rank": rank + 1, "of": n, "score": score}
    totals = {}
    for g, s in scores.items():
        num = den = 0.0
        for ind, rec in s.items():
            w = INDICATORS[ind]["weight"]
            num += rec["score"] * w
            den += w
        if den:
            totals[g] = round(num / den, 1)
    return scores, totals

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    sample = "--sample" in sys.argv
    prev = {}
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH) as f:
                prev = json.load(f)
        except Exception:
            pass

    if sample:
        print("Generating SAMPLE data (demo mode)...")
        series, jobs = make_sample()
    else:
        series = fetch_eurostat_all()
        # keep previous values for any indicator that failed entirely
        for k, v in prev.get("series", {}).items():
            if not series.get(k):
                print(f"  keeping previous data for {k}")
                series[k] = v
        jobs = fetch_adzuna(series.get("population", {}))
        jooble = fetch_jooble(series.get("population", {}), skip_geos=set(jobs))
        for g, rec in jooble.items():
            jobs.setdefault(g, rec)
        # keep previous job data for any country that failed this run
        for g, rec in prev.get("jobs", {}).items():
            jobs.setdefault(g, rec)

    scores, totals = compute_scores(series, jobs)
    out = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample": sample,
        "countries": COUNTRIES,
        "indicators": {k: {kk: vv for kk, vv in m.items()} for k, m in INDICATORS.items()},
        "english": ENGLISH_PROFICIENCY,
        "series": series,
        "jobs": jobs,
        "scores": scores,
        "totals": totals,
    }
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {DATA_PATH} ({os.path.getsize(DATA_PATH)//1024} KB)")

if __name__ == "__main__":
    main()
