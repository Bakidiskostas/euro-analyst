# Euro Analyst Compass

A static dashboard comparing 30 European countries across 16 indicators: economy, cost of living, income, health, quality of life and the data analyst job market. Data is refreshed automatically via GitHub Actions and hosted for free on GitHub Pages.

## Data sources (all free & legal — official APIs only)

- **Eurostat** — GDP growth, inflation (HICP), unemployment, net salaries, price level indices (overall / food / energy & housing), real household income growth, life expectancy, life satisfaction, population, tax wedge (gross vs net salary).
- **Adzuna API** — data analyst / engineer / scientist job ads, average advertised salary, remote share. Covers 10 markets: DE, AT, CH, NL, BE, FR, ES, IT, PL, SE. Free key at https://developer.adzuna.com
- **Jooble API** — job ads & remote share for the remaining countries, **including Greece and Cyprus**. Free key at https://jooble.org/api/about. Salary data not available via Jooble, so the salary card is shown only for Adzuna-covered markets.
- **EF EPI** — English proficiency scores (static values, updated once a year in `fetch_data.py`).

> Indeed is not used (scraping prohibited). EURES is not used (API restricted to official partners only).

## Setup (one time)

1. Create a new **public** GitHub repository and upload all files, keeping the folder structure (including `.github/workflows/`).
2. **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main` / root. Your site will be live at `https://USERNAME.github.io/REPO/`.
3. Add your API keys as repository secrets: **Settings → Secrets and variables → Actions → New repository secret**:
   - `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` (from developer.adzuna.com)
   - `JOOBLE_API_KEY` (from jooble.org/api/about)
4. Go to the **Actions** tab → select *Update data* workflow → click **Run workflow**. This loads real data for the first time. After that it runs automatically on the 1st and 15th of every month at 05:20 UTC.

## Local testing (no internet required)

```bash
python fetch_data.py --sample   # generates realistic demo data offline
python -m http.server           # open http://localhost:8000
```

No external libraries needed — standard library only.

## How scoring works

Each indicator is ranked across all countries and converted to a 0–100 score based on rank position. For indicators where lower is better (inflation, unemployment, price levels, tax wedge) the ranking is inverted, so 100 always means "best". The overall country score is a weighted average — weights can be adjusted in the `INDICATORS` dictionary in `fetch_data.py`.

## Notes

- If a Eurostat dataset fails temporarily, the script keeps the previous values so the site never breaks.
- Eurostat PPP category codes (`ppp_cat`) rarely change. If a price-level indicator comes back empty, check the available codes for dataset `prc_ppp_ind` in the Eurostat Data Browser.
