"""Lädt altersspezifische Sterbefälle und Bevölkerung für Deutschland von Eurostat.

Quelle: Eurostat demo_magec (Gestorbene nach Einzelalter) und demo_pjan
(Bevölkerung nach Einzelalter, Stichtag 1.1.), geo=DE, sex=T.
Beide Reihen sind fuer Deutschland erst ab 1991 auf wiedervereinigtem Gebiet
konsistent (Bevoelkerungssprung 1990->1991 bestaetigt alte BRD-only vor 1991).
"""
import json
import subprocess
from pathlib import Path

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
OUT_DIR = Path(__file__).parent.parent / "data"


def fetch(dataset: str) -> dict:
    url = f"{BASE}/{dataset}?format=JSON&geo=DE&sex=T&lang=EN"
    raw = subprocess.run(["curl", "-s", url], capture_output=True, check=True).stdout
    return json.loads(raw)


def jsonstat_to_year_age_dict(d: dict) -> dict:
    """Wandelt JSON-stat Antwort in {year: {age_code: value}} um."""
    dims = d["id"]
    sizes = d["size"]
    idx = d["dimension"]

    def cat_index(dim, key):
        return idx[dim]["category"]["index"][key]

    fixed = {}
    for dname in dims:
        cats = idx[dname]["category"]["index"]
        if dname not in ("age", "time"):
            # nur ein Wert vorhanden (freq, unit, sex, geo), fix nehmen
            fixed[dname] = next(iter(cats.values()))

    years = idx["time"]["category"]["index"]
    ages = idx["age"]["category"]["index"]

    def compute(indices_dict):
        pos = 0
        for dname, sz in zip(dims, sizes):
            pos = pos * sz + indices_dict[dname]
        return pos

    result = {}
    for year, y_i in years.items():
        row = {}
        for age_code, a_i in ages.items():
            ind = dict(fixed)
            ind["age"] = a_i
            ind["time"] = y_i
            pos = compute(ind)
            val = d["value"].get(str(pos))
            if val is not None:
                row[age_code] = val
        result[year] = row
    return result


def main():
    print("Lade demo_magec (Gestorbene nach Alter)...")
    deaths_raw = fetch("demo_magec")
    deaths = jsonstat_to_year_age_dict(deaths_raw)

    print("Lade demo_pjan (Bevoelkerung nach Alter)...")
    pop_raw = fetch("demo_pjan")
    pop = jsonstat_to_year_age_dict(pop_raw)

    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / "eurostat_deaths_by_age.json", "w") as f:
        json.dump(deaths, f)
    with open(OUT_DIR / "eurostat_population_by_age.json", "w") as f:
        json.dump(pop, f)

    print(f"Deaths: {len(deaths)} Jahre, Population: {len(pop)} Jahre")
    print("Beispiel 2024 Deaths TOTAL:", deaths.get("2024", {}).get("TOTAL"))
    print("Beispiel 2024 Pop TOTAL:", pop.get("2024", {}).get("TOTAL"))


if __name__ == "__main__":
    main()
