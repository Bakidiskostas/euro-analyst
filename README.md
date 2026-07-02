# Euro Analyst Compass

Static dashboard που συγκρίνει 30 ευρωπαϊκές χώρες σε 16 δείκτες (οικονομία, κόστος ζωής, εισόδημα, υγεία, αγορά εργασίας για data analysts). Τα δεδομένα ανανεώνονται καθημερινά μέσω GitHub Actions και η σελίδα φιλοξενείται δωρεάν στο GitHub Pages.

## Πηγές (όλες δωρεάν & νόμιμες, επίσημα APIs)
- **Eurostat** — GDP growth, πληθωρισμός, ανεργία, καθαροί μισθοί, price level indices (σύνολο/τρόφιμα/ενέργεια), πραγματικό εισόδημα, προσδόκιμο ζωής, ικανοποίηση ζωής, πληθυσμός, φορολογική επιβάρυνση (gross vs net).
- **Adzuna API** — αγγελίες data analyst/engineer/scientist, μέσος μισθός αγγελιών, ποσοστό remote (10 ευρωπαϊκές αγορές: DE, AT, CH, NL, BE, FR, ES, IT, PL, SE). Το Indeed απαγορεύει scraping, γι' αυτό δεν χρησιμοποιείται.
- **Jooble API** — αγγελίες & ποσοστό remote για τις υπόλοιπες χώρες, **μαζί με Ελλάδα και Κύπρο** (δωρεάν κλειδί από jooble.org/api/about). Δεν δίνει αξιόπιστο μέσο μισθό, οπότε το salary card εμφανίζεται μόνο στις χώρες Adzuna. Σημ.: το EURES απαγορεύει εξαγωγή δεδομένων εκτός επίσημων partners, γι' αυτό δεν χρησιμοποιείται.
- **EF EPI** — γνώση αγγλικών (στατικές τιμές, ενημέρωση 1×/χρόνο στο `fetch_data.py`).

## Στήσιμο (μία φορά)
1. Φτιάξε νέο **public** repo στο GitHub και ανέβασε όλα τα αρχεία (κράτα τη δομή φακέλων, μαζί με το `.github/workflows/`).
2. **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main` / root. Η σελίδα θα βγει στο `https://USERNAME.github.io/REPO/`.
3. (Για job data) Στο repo → **Settings → Secrets and variables → Actions** πρόσθεσε:
   - `ADZUNA_APP_ID` και `ADZUNA_APP_KEY` — δωρεάν από https://developer.adzuna.com (10 μεγάλες αγορές, με μισθούς)
   - `JOOBLE_API_KEY` — δωρεάν από https://jooble.org/api/about (υπόλοιπες χώρες, **μαζί με Ελλάδα & Κύπρο**)
4. **Actions tab** → workflow *Update data daily* → **Run workflow** για την πρώτη φόρτωση αληθινών δεδομένων. Μετά τρέχει μόνο του κάθε μέρα στις 05:20 UTC.

## Τοπική δοκιμή
```bash
python fetch_data.py --sample   # demo δεδομένα χωρίς internet
python -m http.server           # άνοιξε http://localhost:8000
```
Δεν χρειάζονται εξωτερικές βιβλιοθήκες (μόνο standard library).

## Πώς δουλεύει το σκορ
Για κάθε δείκτη οι χώρες κατατάσσονται και παίρνουν 0–100 βάσει θέσης. Σε δείκτες όπου το χαμηλό είναι καλό (πληθωρισμός, ανεργία, τιμές, φόροι) η κατάταξη αντιστρέφεται, ώστε το 100 να σημαίνει πάντα "καλύτερο". Το συνολικό σκορ είναι σταθμισμένος μέσος όρος — τα βάρη αλλάζουν στο `INDICATORS` του `fetch_data.py`.

## Σημειώσεις
- Αν ένα Eurostat dataset αποτύχει προσωρινά, το script κρατά τα προηγούμενα δεδομένα (δεν "σπάει" η σελίδα).
- Οι κωδικοί κατηγοριών PPP (`ppp_cat`) της Eurostat αλλάζουν σπάνια· αν κάποιος δείκτης τιμών βγει κενός, δες τα διαθέσιμα codes στο dataset `prc_ppp_ind` στον Eurostat Data Browser.
