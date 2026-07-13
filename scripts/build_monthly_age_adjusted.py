"""Altersstandardisierte monatliche Sterberate (ESP2013) fuer 2021-2026.

Nur fuer diesen Zeitraum verfuegbar, weil die Destatis-Sonderauswertung
"Sterbefaelle nach Tagen, Wochen und Monaten" erst ab 2021 eine
Altersgruppen-Aufschluesselung je Woche liefert (die laengere Eurostat-
Wochenreihe 2000-2020 hat keine Altersgruppen).

Methodik: Wochenwerte je Altersgruppe werden taggenau auf Kalendermonate
verteilt (wie bei den Rohdaten). Je Monat wird die direkt auf ESP2013
standardisierte Rate berechnet und auf ein Jahr hochgerechnet
(rate_annualisiert = deaths_monat / bevoelkerung_jahr * 365.25/Tage_im_Monat),
damit die Werte in derselben Einheit ("je 100.000 pro Jahr") wie die
jaehrliche ESP2013-Kurve liegen und direkt vergleichbar sind.

Bevoelkerung je Altersgruppe kommt aus Eurostats demo_pjan (Einzelaltersjahre,
Stand 1. Januar). Fuer 2026 gibt es noch keine Bevoelkerungsfortschreibung,
dafuer wird der Stand 2025 verwendet (Altersstruktur aendert sich innerhalb
eines Jahres kaum).
"""
import json
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

MONTH_NAMES = [
    "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]

# Destatis-Altersgruppen -> passende ESP2013-Gewichte (0-29 fasst die ESP-
# Gruppen 0/1-4/5-9/.../25-29 zusammen; 90-94 + 95+ werden zum ESP-Topf
# "90+" zusammengefasst, weil Destatis dort feiner unterteilt als ESP2013).
AGE_BIN_WEIGHTS = {
    "0-29": 1000 + 4000 + 5500 + 5500 + 5500 + 6000 + 6000,  # 33500
    "30-34": 6500,
    "35-39": 7000,
    "40-44": 7000,
    "45-49": 7000,
    "50-54": 7000,
    "55-59": 6500,
    "60-64": 6000,
    "65-69": 5500,
    "70-74": 5000,
    "75-79": 4000,
    "80-84": 2500,
    "85-89": 1500,
    "90+": 1000,  # = 90-94 + 95+ zusammengefasst
}
TOTAL_WEIGHT = sum(AGE_BIN_WEIGHTS.values())
assert TOTAL_WEIGHT == 100_000

# Eurostat-Einzelaltersjahr-Codes je Destatis-Bin (fuer die Bevoelkerung)
POP_AGE_CODES = {
    "0-29": [f"Y{i}" for i in range(1, 30)] + ["Y_LT1"],
    "30-34": [f"Y{i}" for i in range(30, 35)],
    "35-39": [f"Y{i}" for i in range(35, 40)],
    "40-44": [f"Y{i}" for i in range(40, 45)],
    "45-49": [f"Y{i}" for i in range(45, 50)],
    "50-54": [f"Y{i}" for i in range(50, 55)],
    "55-59": [f"Y{i}" for i in range(55, 60)],
    "60-64": [f"Y{i}" for i in range(60, 65)],
    "65-69": [f"Y{i}" for i in range(65, 70)],
    "70-74": [f"Y{i}" for i in range(70, 75)],
    "75-79": [f"Y{i}" for i in range(75, 80)],
    "80-84": [f"Y{i}" for i in range(80, 85)],
    "85-89": [f"Y{i}" for i in range(85, 90)],
    "90+": [f"Y{i}" for i in range(90, 100)] + ["Y_OPEN"],
}


def week_day_shares(week_key: str) -> dict[tuple[int, int], float]:
    iso_year, iso_week = week_key.split("-W")
    monday = date.fromisocalendar(int(iso_year), int(iso_week), 1)
    shares: dict[tuple[int, int], float] = {}
    for i in range(7):
        d = monday + timedelta(days=i)
        key = (d.year, d.month)
        shares[key] = shares.get(key, 0) + 1 / 7
    return shares


def main():
    weekly_age = json.load(open(DATA_DIR / "destatis_deaths_weekly_by_age.json"))
    pop_by_age = json.load(open(DATA_DIR / "eurostat_population_by_age.json"))

    # monthly[y][m][bin] = deaths (taggenau verteilt)
    monthly: dict[int, dict[int, dict[str, float]]] = {}
    for week_key, bins in weekly_age.items():
        for (y, m), share in week_day_shares(week_key).items():
            slot = monthly.setdefault(y, {}).setdefault(m, {})
            # 90-94 + 95+ zusammenfassen auf "90+"
            for age_bin, deaths in bins.items():
                target = "90+" if age_bin in ("90-94", "95+") else age_bin
                slot[target] = slot.get(target, 0) + deaths * share

    def population_for_year(y: int) -> dict[str, float]:
        yy = min(y, 2025)  # 2026: noch keine Fortschreibung, letzten Stand nehmen
        row = pop_by_age[str(yy)]
        return {b: sum(row.get(c, 0) for c in codes) for b, codes in POP_AGE_CODES.items()}

    years = sorted(monthly.keys())
    result_years = []
    asr_by_year_month: dict[int, list[float | None]] = {}
    for y in years:
        pop = population_for_year(y)
        row = [None] * 12
        for m in range(1, 13):
            bins = monthly[y].get(m)
            if not bins:
                continue
            days_in_month = monthrange(y, m)[1]
            asr_sum = 0.0
            for age_bin, weight in AGE_BIN_WEIGHTS.items():
                deaths = bins.get(age_bin, 0)
                population = pop[age_bin]
                rate_annualized = deaths / population * (365.25 / days_in_month)
                asr_sum += rate_annualized * weight
            asr = asr_sum / TOTAL_WEIGHT * 100_000
            row[m - 1] = round(asr, 1)
        asr_by_year_month[y] = row
        result_years.append(y)

    result = {
        "years": result_years,
        "months": MONTH_NAMES,
        "age_std_rate_per_100k_annualized": {str(y): asr_by_year_month[y] for y in result_years},
        "source": (
            "Destatis-Sonderauswertung 'Sterbefälle nach Tagen, Wochen und Monaten' "
            "(Altersgruppen je Woche, ab 2021), taggenau auf Kalendermonate verteilt. "
            "Direkt auf ESP2013 standardisiert, auf Jahresrate hochgerechnet "
            "(Tage im Monat -> 365,25 Tage) und damit vergleichbar zur jährlichen "
            "ESP2013-Kurve. Bevölkerung je Altersgruppe: Eurostat demo_pjan, Stand "
            "1. Januar des jeweiligen Jahres (2026: Stand 2025, da noch keine "
            "Fortschreibung vorliegt)."
        ),
    }

    with open(DATA_DIR / "monthly_age_adjusted.json", "w") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    print(f"Altersstandardisierte Monatsdaten: {result_years[0]}-{result_years[-1]}")


if __name__ == "__main__":
    main()
