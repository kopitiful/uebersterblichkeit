"""Aggregiert woechentliche Sterbefallzahlen zu Monatswerten und berechnet
saisonale Abweichungen von der 2000-2019 Monats-Baseline (vor-pandemisch).

Woche -> Monat: jede ISO-Woche wird taggenau auf die Kalendermonate verteilt,
die sie ueberlappt (Anteil = Tage der Woche in diesem Monat / 7). Eine simple
"Donnerstag entscheidet"-Regel wuerde Monate mit 4 vs. 5 zugeordneten Wochen
erzeugen und damit eine rein artefaktbedingte Schwankung von bis zu 25% in die
Monatswerte einbauen.
"""
import json
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

MONTH_NAMES = [
    "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


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
    weekly = json.load(open(DATA_DIR / "eurostat_deaths_weekly.json"))
    destatis_weekly = json.load(open(DATA_DIR / "destatis_deaths_weekly.json"))
    weekly = {**weekly, **destatis_weekly}  # Destatis ist aktueller, hat Vorrang

    monthly: dict[int, dict[int, float]] = {}
    for week_key, deaths in weekly.items():
        for (y, m), share in week_day_shares(week_key).items():
            monthly.setdefault(y, {}).setdefault(m, 0)
            monthly[y][m] += deaths * share

    complete_years = sorted(y for y, months in monthly.items() if len(months) == 12)
    incomplete_years = sorted(y for y in monthly if y not in complete_years)

    # Gleitende Baseline statt fixem 2000-2019-Mittel: sonst erscheint fast jedes
    # spaetere Jahr allein wegen des demografischen Alterungstrends als "Excess".
    # Referenz = Mittelwert der bis zu 5 vorangehenden vollstaendigen Jahre je
    # Kalendermonat (analog zur Destatis-Methodik fuer die Sonderauswertung).
    ROLLING_WINDOW = 5
    MIN_PRIOR_YEARS = 3

    # Auch das laufende (unvollstaendige) Jahr aufnehmen, damit die neuesten
    # Monate sofort sichtbar sind -> fehlende Monate bleiben als leere Zelle.
    all_years_sorted = sorted(monthly.keys())
    heatmap_years = [y for y in all_years_sorted if len([p for p in complete_years if p < y]) >= MIN_PRIOR_YEARS]
    cells = []
    for y in heatmap_years:
        prior_years = [p for p in complete_years if y - ROLLING_WINDOW <= p < y]
        row = []
        for m in range(1, 13):
            deaths = monthly[y].get(m)
            if deaths is None:
                row.append({"deaths": None, "baseline": None, "pct_vs_baseline": None})
                continue
            baseline_vals = [monthly[p][m] for p in prior_years if m in monthly[p]]
            baseline = sum(baseline_vals) / len(baseline_vals)
            pct = (deaths - baseline) / baseline * 100
            row.append({
                "deaths": round(deaths),
                "baseline": round(baseline),
                "pct_vs_baseline": round(pct, 1),
            })
        cells.append(row)

    # Wochen-Heatmap: gleiche gleitende-Baseline-Methodik wie bei den Monaten,
    # nur je ISO-Kalenderwoche statt Kalendermonat.
    weekly_by_year_kw: dict[int, dict[int, float]] = {}
    for week_key, deaths in weekly.items():
        y, kw = week_key.split("-W")
        weekly_by_year_kw.setdefault(int(y), {})[int(kw)] = deaths

    week_years_all = sorted(weekly_by_year_kw.keys())
    max_kw = max(kw for kws in weekly_by_year_kw.values() for kw in kws)
    week_heatmap_years = [
        y for y in week_years_all
        if len([p for p in week_years_all if p < y]) >= MIN_PRIOR_YEARS
    ]
    week_cells = []
    for y in week_heatmap_years:
        prior_years = [p for p in week_years_all if y - ROLLING_WINDOW <= p < y]
        row = []
        for kw in range(1, max_kw + 1):
            deaths = weekly_by_year_kw.get(y, {}).get(kw)
            if deaths is None:
                row.append({"deaths": None, "baseline": None, "pct_vs_baseline": None})
                continue
            baseline_vals = [weekly_by_year_kw[p][kw] for p in prior_years if kw in weekly_by_year_kw.get(p, {})]
            if len(baseline_vals) < MIN_PRIOR_YEARS:
                row.append({"deaths": round(deaths), "baseline": None, "pct_vs_baseline": None})
                continue
            baseline = sum(baseline_vals) / len(baseline_vals)
            pct = (deaths - baseline) / baseline * 100
            row.append({
                "deaths": round(deaths),
                "baseline": round(baseline),
                "pct_vs_baseline": round(pct, 1),
            })
        week_cells.append(row)

    result = {
        "years": heatmap_years,
        "months": MONTH_NAMES,
        "rolling_window": ROLLING_WINDOW,
        "cells": cells,
        "monthly_deaths": {
            str(y): [round(monthly[y][m]) if m in monthly[y] else None for m in range(1, 13)]
            for y in sorted(monthly.keys())
        },
        "weekly": {
            "years": week_heatmap_years,
            "max_kw": max_kw,
            "cells": week_cells,
        },
        "incomplete_years": incomplete_years,
        "source": (
            "Eurostat demo_r_mwk_ts 2000-2020, ab 2021 Destatis-Sonderauswertung "
            "'Sterbefälle nach Tagen, Wochen und Monaten' (aktueller, wenige Tage "
            "Verzug), Gestorbene je ISO-Woche, Deutschland. Taggenau zu "
            "Kalendermonaten aggregiert. Baseline je Zelle = Mittelwert desselben "
            "Kalendermonats in den bis zu 5 vorangehenden vollstaendigen Jahren "
            "(gleitend, min. 3 Vorjahre). Die letzten 1-2 Wochen sind vorläufig "
            "und koennen durch Nachmeldungen noch revidiert werden."
        ),
    }

    with open(DATA_DIR / "monthly_data.json", "w") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    print(f"Heatmap-Jahre: {heatmap_years[0]}-{heatmap_years[-1]} ({len(heatmap_years)}), davon unvollstaendig: {incomplete_years}")


if __name__ == "__main__":
    main()
