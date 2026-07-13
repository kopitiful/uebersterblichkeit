"""Laedt den aktuellen Destatis-Bericht "Sterbefaelle nach Tagen, Wochen und
Monaten" (taeglich/woechentlich aktualisiert, deutlich aktueller als Eurostat)
und extrahiert die woechentlichen Gesamt-Sterbefallzahlen fuer Deutschland.

Deckt nur 2021-heute ab, dafuer mit wenigen Tagen Verzug statt Eurostats
Monate. Wird mit der laengeren Eurostat-Reihe (2000-2020) zusammengefuehrt.
"""
import json
import subprocess
from pathlib import Path

import openpyxl

DATA_DIR = Path(__file__).parent.parent / "data"
URL = (
    "https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/"
    "Sterbefaelle-Lebenserwartung/Publikationen/Downloads-Sterbefaelle/"
    "statistischer-bericht-sterbefaelle-tage-wochen-monate-aktuell-5126109.xlsx"
    "?__blob=publicationFile&v=2"
)


def main():
    out_xlsx = DATA_DIR / "destatis_sterbefaelle_aktuell.xlsx"
    subprocess.run(["curl", "-sL", "-o", str(out_xlsx), URL], check=True)

    wb = openpyxl.load_workbook(out_xlsx, data_only=True)
    ws = wb["csv-12613-01"]

    weekly = {}
    weekly_by_age = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[0] is None:
            continue
        _, gebiet, geschlecht, jahr, alter, kw, sf, _qk = row[:8]
        if gebiet != "Deutschland" or geschlecht != "Insgesamt":
            continue
        if not isinstance(sf, (int, float)):
            continue  # "..." = noch nicht verfuegbare Zukunftswoche
        week_key = f"{jahr}-W{int(kw):02d}"
        if alter == "Insgesamt":
            weekly[week_key] = sf
        else:
            weekly_by_age.setdefault(week_key, {})[alter] = sf

    with open(DATA_DIR / "destatis_deaths_weekly.json", "w") as f:
        json.dump(weekly, f)
    with open(DATA_DIR / "destatis_deaths_weekly_by_age.json", "w") as f:
        json.dump(weekly_by_age, f)

    weeks = sorted(weekly.keys())
    print(f"{len(weeks)} Wochen: {weeks[0]} bis {weeks[-1]}")
    print(f"Altersaufschluesselung fuer {len(weekly_by_age)} Wochen")


if __name__ == "__main__":
    main()
