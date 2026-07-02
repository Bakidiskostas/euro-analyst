# 📊 Commodity & Financial Indicators Dashboard

Interactive dashboard για συσχέτιση τιμών μετάλλων και οικονομικών δεικτών —
φτιαγμένο για Einkaufscontrolling.

## Τι περιλαμβάνει

**Commodities** (Yahoo Finance)
- Precious Metals: Gold, Silver, Platinum, Palladium
- Base Metals: Copper, Aluminum, Nickel, Zinc
- Energy: Brent Oil, WTI Oil, Natural Gas

**Financial Indicators** (FRED / St. Louis Fed — δωρεάν)
- USD Index (DXY), EUR/USD
- Fed Funds Rate, ECB Deposit Rate
- US CPI (Inflation)
- S&P 500, VIX
- US 10Y Treasury Yield

---

## Εγκατάσταση

```bash
# 1. Κλώνησε το repo
git clone https://github.com/YOUR_USERNAME/commodity-dashboard.git
cd commodity-dashboard

# 2. Εγκατάσταση Python libraries
pip install yfinance pandas requests

# 3. Κατέβασε δεδομένα (δημιουργεί data/commodities.json & data/indicators.json)
python scripts/fetch_data.py

# 4. Άνοιξε το dashboard
open index.html        # macOS
start index.html       # Windows
xdg-open index.html    # Linux
```

---

## Χρήση

- **Sidebar**: κλικ σε κάθε γραμμή για ενεργοποίηση/απενεργοποίηση
- **1Ε / 2Ε / 5Ε / 10Ε**: φιλτράρισμα χρονικής περιόδου
- **Εξομαλυμένο (base=100)**: κανονικοποίηση όλων των σειρών στο 100
  → ιδανικό για να βλέπεις συσχέτιση ανεξάρτητα από μονάδες
- **Hover**: ενοποιημένο tooltip με όλες τις τιμές για μια ημερομηνία
- **Zoom**: σύρε στο chart για zoom, διπλό κλικ για reset

---

## Ανανέωση δεδομένων

Τρέξε ξανά το script οποτεδήποτε:
```bash
python scripts/fetch_data.py
```

---

## Προσθήκη νέων Indicators

Άνοιξε `scripts/fetch_data.py` και πρόσθεσε γραμμή στη λίστα `INDICATORS`:

```python
{"fred_id": "UNRATE", "label": "US Unemployment", "unit": "%", "category": "Macro"},
```

Βρες FRED series IDs στο: https://fred.stlouisfed.org/

Για Trading Economics API (αν αποκτήσεις subscription):
- Αντικατάστησε τη συνάρτηση `fetch_fred()` με κλήση στο TE API
- Το HTML δεν χρειάζεται καμία αλλαγή

---

## GitHub Pages (δωρεάν hosting)

1. Κάνε commit τα αρχεία (συμπεριλαμβανομένου του `data/` folder)
2. Στο GitHub repo → Settings → Pages → Source: `main` branch, `/root`
3. Το dashboard τρέχει στο `https://YOUR_USERNAME.github.io/commodity-dashboard/`

> **Σημείωση**: Τα JSON αρχεία πρέπει να γίνουν commit μαζί με τον κώδικα.
> Για αυτόματη ανανέωση, μπορείς να φτιάξεις GitHub Action που τρέχει
> το Python script εβδομαδιαία (βλ. παρακάτω).

---

## GitHub Action για αυτόματη ανανέωση (προαιρετικό)

Δημιούργησε `.github/workflows/update-data.yml`:

```yaml
name: Update commodity data

on:
  schedule:
    - cron: '0 6 * * 1'   # κάθε Δευτέρα 06:00 UTC
  workflow_dispatch:        # manual trigger

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install yfinance pandas requests
      - run: python scripts/fetch_data.py
      - uses: actions/upload-artifact@v4
        with:
          name: data
          path: data/
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: 'data: weekly update'
```

---

## Δομή αρχείων

```
commodity-dashboard/
├── index.html              ← Dashboard (άνοιξε στον browser)
├── README.md
├── scripts/
│   └── fetch_data.py       ← Python script για δεδομένα
└── data/
    ├── commodities.json    ← Δημιουργείται από το script
    └── indicators.json     ← Δημιουργείται από το script
```
