"""Altersstandardisierte woechentliche Sterberate (ESP2013), annualisiert,
fuer 2021-2026 (nur dort liegt eine Altersaufschluesselung je Woche vor).

Im Gegensatz zur monatlichen Version wird hier NICHT von Woche auf Monat
verteilt, sondern direkt je ISO-Woche gerechnet (Rate * 365,25/7, um auf eine
Jahresrate je 100.000 hochzurechnen -> vergleichbar mit der jaehrlichen und
der monatlichen ESP2013-Kurve). Da die Historie mit 6 Jahren zu kurz fuer eine
Vorjahres-Baseline ist, wird hier keine Abweichung, sondern der Absolutwert
dargestellt (sequentielle statt divergierende Farbskala).
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

AGE_BIN_WEIGHTS = {
    "0-29": 1000 + 4000 + 5500 + 5500 + 5500 + 6000 + 6000,
    "30-34": 6500, "35-39": 7000, "40-44": 7000, "45-49": 7000, "50-54": 7000,
    "55-59": 6500, "60-64": 6000, "65-69": 5500, "70-74": 5000, "75-79": 4000,
    "80-84": 2500, "85-89": 1500, "90+": 1000,
}
TOTAL_WEIGHT = sum(AGE_BIN_WEIGHTS.values())
assert TOTAL_WEIGHT == 100_000

POP_AGE_CODES = {
    "0-29": [f"Y{i}" for i in range(1, 30)] + ["Y_LT1"],
    "30-34": [f"Y{i}" for i in range(30, 35)], "35-39": [f"Y{i}" for i in range(35, 40)],
    "40-44": [f"Y{i}" for i in range(40, 45)], "45-49": [f"Y{i}" for i in range(45, 50)],
    "50-54": [f"Y{i}" for i in range(50, 55)], "55-59": [f"Y{i}" for i in range(55, 60)],
    "60-64": [f"Y{i}" for i in range(60, 65)], "65-69": [f"Y{i}" for i in range(65, 70)],
    "70-74": [f"Y{i}" for i in range(70, 75)], "75-79": [f"Y{i}" for i in range(75, 80)],
    "80-84": [f"Y{i}" for i in range(80, 85)], "85-89": [f"Y{i}" for i in range(85, 90)],
    "90+": [f"Y{i}" for i in range(90, 100)] + ["Y_OPEN"],
}


def main():
    weekly_age = json.load(open(DATA_DIR / "destatis_deaths_weekly_by_age.json"))
    pop_by_age = json.load(open(DATA_DIR / "eurostat_population_by_age.json"))

    def population_for_year(y: int) -> dict[str, float]:
        yy = min(y, 2025)
        row = pop_by_age[str(yy)]
        return {b: sum(row.get(c, 0) for c in codes) for b, codes in POP_AGE_CODES.items()}

    pop_cache: dict[int, dict[str, float]] = {}

    by_year: dict[int, dict[int, float]] = {}
    for week_key, bins in weekly_age.items():
        y_str, kw_str = week_key.split("-W")
        y, kw = int(y_str), int(kw_str)
        pop = pop_cache.setdefault(y, population_for_year(y))

        asr_sum = 0.0
        for age_bin, weight in AGE_BIN_WEIGHTS.items():
            if age_bin == "90+":
                deaths = bins.get("90-94", 0) + bins.get("95+", 0)
            else:
                deaths = bins.get(age_bin, 0)
            population = pop[age_bin]
            rate_annualized = deaths / population * (365.25 / 7)
            asr_sum += rate_annualized * weight
        asr = asr_sum / TOTAL_WEIGHT * 100_000
        by_year.setdefault(y, {})[kw] = round(asr, 1)

    years = sorted(by_year.keys())
    max_kw = max(kw for kws in by_year.values() for kw in kws)
    cells = []
    for y in years:
        row = []
        for kw in range(1, max_kw + 1):
            val = by_year[y].get(kw)
            row.append({"asr": val})
        cells.append(row)

    result = {
        "years": years,
        "max_kw": max_kw,
        "cells": cells,
        "source": (
            "Destatis-Sonderauswertung 'Sterbefälle nach Tagen, Wochen und Monaten' "
            "(Altersgruppen je Woche, ab 2021). Direkt auf ESP2013 standardisiert, je "
            "Woche auf Jahresrate hochgerechnet (× 365,25/7). Bevölkerung je "
            "Altersgruppe: Eurostat demo_pjan, Stand 1. Januar (2026: Stand 2025). "
            "Absolutwert statt Abweichung, da die Historie (ab 2021) für eine "
            "Vorjahres-Baseline zu kurz ist."
        ),
    }

    with open(DATA_DIR / "weekly_age_adjusted.json", "w") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    print(f"Woechentliche ASR: {years[0]}-{years[-1]}, {sum(len(r) for r in cells)} Zellen")


if __name__ == "__main__":
    main()
