"""Baut dashboard_data.json aus den Rohquellen (Destatis-Zeitreihe + Eurostat-Altersdaten).

Rohdaten: Statistik der Sterbefaelle, Gebiet "Deutschland" (retrospektiv fuer
das jeweils aktuelle Gebietsstand kombiniert, siehe Destatis-Zeitreihe 1841-2024),
1946-2024 -> 79 Jahre.

Altersstandardisiert: Eurostat demo_magec (Gestorbene je Einzelalter) und
demo_pjan (Bevoelkerung je Einzelalter), geo=DE. Diese Reihen sind nur ab 1991
auf wiedervereinigtem Gebiet konsistent (siehe fetch_eurostat.py), daher
1991-2024 -> 34 Jahre. Standardisierung direkt auf die European Standard
Population 2013 (ESP2013), Ergebnis als Rate je 100.000 Einwohner.
"""
import json
from pathlib import Path

import openpyxl

DATA_DIR = Path(__file__).parent.parent / "data"

ESP2013_BINS = [
    ("0", ["Y_LT1"], 1000),
    ("1-4", ["Y1", "Y2", "Y3", "Y4"], 4000),
    ("5-9", [f"Y{i}" for i in range(5, 10)], 5500),
    ("10-14", [f"Y{i}" for i in range(10, 15)], 5500),
    ("15-19", [f"Y{i}" for i in range(15, 20)], 5500),
    ("20-24", [f"Y{i}" for i in range(20, 25)], 6000),
    ("25-29", [f"Y{i}" for i in range(25, 30)], 6000),
    ("30-34", [f"Y{i}" for i in range(30, 35)], 6500),
    ("35-39", [f"Y{i}" for i in range(35, 40)], 7000),
    ("40-44", [f"Y{i}" for i in range(40, 45)], 7000),
    ("45-49", [f"Y{i}" for i in range(45, 50)], 7000),
    ("50-54", [f"Y{i}" for i in range(50, 55)], 7000),
    ("55-59", [f"Y{i}" for i in range(55, 60)], 6500),
    ("60-64", [f"Y{i}" for i in range(60, 65)], 6000),
    ("65-69", [f"Y{i}" for i in range(65, 70)], 5500),
    ("70-74", [f"Y{i}" for i in range(70, 75)], 5000),
    ("75-79", [f"Y{i}" for i in range(75, 80)], 4000),
    ("80-84", [f"Y{i}" for i in range(80, 85)], 2500),
    ("85-89", [f"Y{i}" for i in range(85, 90)], 1500),
    ("90+", [f"Y{i}" for i in range(90, 100)] + ["Y_OPEN"], 1000),
]
ESP2013_TOTAL = sum(w for _, _, w in ESP2013_BINS)
assert ESP2013_TOTAL == 100_000


def parse_destatis_raw():
    wb = openpyxl.load_workbook(
        DATA_DIR / "destatis_zeitreihen_1841-2024.xlsx", data_only=True
    )
    ws = wb["csv-126xx-b02"]
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[0] is None:
            continue
        _, gebiet, jahr, merkmal, geschlecht, einheit, wert = row[:7]
        if gebiet != "Deutschland" or merkmal != "Gestorbene" or geschlecht != "insgesamt":
            continue
        if wert in (".", None):
            continue
        jahr = int(jahr)
        out.setdefault(jahr, {})
        if einheit == "Anzahl":
            out[jahr]["deaths"] = int(wert)
        elif einheit.startswith("je 1"):
            out[jahr]["rate_per_1000"] = float(wert)
    return dict(sorted(out.items()))


def compute_age_standardized():
    deaths = json.load(open(DATA_DIR / "eurostat_deaths_by_age.json"))
    pop = json.load(open(DATA_DIR / "eurostat_population_by_age.json"))

    out = {}
    for year in sorted(set(deaths) & set(pop)):
        y = int(year)
        if y < 1991:  # vor Wiedervereinigung nur altes Bundesgebiet, siehe Docstring
            continue
        d_by_age = deaths[year]
        p_by_age = pop[year]
        if "TOTAL" not in d_by_age or "TOTAL" not in p_by_age:
            continue

        asr_sum = 0.0
        used_weight = 0
        for _, age_codes, weight in ESP2013_BINS:
            bin_deaths = sum(d_by_age.get(c, 0) for c in age_codes)
            bin_pop = sum(p_by_age.get(c, 0) for c in age_codes)
            if bin_pop == 0:
                continue
            rate = bin_deaths / bin_pop
            asr_sum += rate * weight
            used_weight += weight
        if used_weight == 0:
            continue
        asr_per_100k = asr_sum / used_weight * 100_000

        crude_deaths = d_by_age["TOTAL"]
        crude_pop = p_by_age["TOTAL"]
        crude_rate_per_1000 = crude_deaths / crude_pop * 1000

        out[y] = {
            "deaths": crude_deaths,
            "population": crude_pop,
            "crude_rate_per_1000": round(crude_rate_per_1000, 3),
            "age_std_rate_per_100k": round(asr_per_100k, 1),
        }
    return dict(sorted(out.items()))


def main():
    raw = parse_destatis_raw()
    age_adj = compute_age_standardized()

    aa_years = list(age_adj.keys())
    baseline_years = [y for y in aa_years if 2015 <= y <= 2019]
    baseline_asr = sum(age_adj[y]["age_std_rate_per_100k"] for y in baseline_years) / len(baseline_years)
    latest_year = aa_years[-1]
    latest_asr = age_adj[latest_year]["age_std_rate_per_100k"]
    pandemic_years = [y for y in aa_years if y >= 2020]
    peak_year = max(pandemic_years, key=lambda y: age_adj[y]["age_std_rate_per_100k"])
    peak_asr = age_adj[peak_year]["age_std_rate_per_100k"]

    raw_latest_year = list(raw.keys())[-1]
    raw_latest_deaths = raw[raw_latest_year]["deaths"]

    summary = {
        "raw_latest_year": raw_latest_year,
        "raw_latest_deaths": raw_latest_deaths,
        "age_latest_year": latest_year,
        "age_latest_asr": latest_asr,
        "baseline_2015_2019_asr": round(baseline_asr, 1),
        "pct_change_vs_baseline": round((latest_asr - baseline_asr) / baseline_asr * 100, 1),
        "peak_year": peak_year,
        "peak_asr": peak_asr,
        "peak_pct_vs_baseline": round((peak_asr - baseline_asr) / baseline_asr * 100, 1),
    }

    result = {
        "summary": summary,
        "raw_annual": {
            "years": list(raw.keys()),
            "deaths": [v["deaths"] for v in raw.values()],
            "rate_per_1000": [v.get("rate_per_1000") for v in raw.values()],
            "source": "Destatis, Statistischer Bericht – Ehescheidungen, Eheschließungen, Geborene und Gestorbene, Zeitreihen 1841-2024 (Gebiet: Deutschland, jeweils aktueller Gebietsstand)",
        },
        "age_adjusted": {
            "years": list(age_adj.keys()),
            "deaths": [v["deaths"] for v in age_adj.values()],
            "population": [v["population"] for v in age_adj.values()],
            "crude_rate_per_1000": [v["crude_rate_per_1000"] for v in age_adj.values()],
            "age_std_rate_per_100k": [v["age_std_rate_per_100k"] for v in age_adj.values()],
            "pct_vs_baseline": [
                round((v["age_std_rate_per_100k"] - baseline_asr) / baseline_asr * 100, 1)
                for v in age_adj.values()
            ],
            "source": "Eurostat demo_magec / demo_pjan, geo=DE, direkt altersstandardisiert auf European Standard Population 2013 (ESP2013). Nur ab 1991 (wiedervereinigtes Gebiet).",
        },
        "esp2013_bins": [{"label": b[0], "weight": b[2]} for b in ESP2013_BINS],
    }

    with open(DATA_DIR / "dashboard_data.json", "w") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    print(f"Rohdaten: {len(raw)} Jahre ({min(raw)}-{max(raw)})")
    print(f"Altersstandardisiert: {len(age_adj)} Jahre ({min(age_adj)}-{max(age_adj)})")


if __name__ == "__main__":
    main()
