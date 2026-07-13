"""Laedt woechentliche Sterbefallzahlen fuer Deutschland von Eurostat.

Quelle: Eurostat demo_r_mwk_ts (Gestorbene je ISO-Woche), geo=DE, sex=T.
Verfuegbar ab 2000-W01, offene REST-API ohne Login.
"""
import json
import subprocess
from pathlib import Path

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
OUT_DIR = Path(__file__).parent.parent / "data"


def fetch(dataset: str, extra: str = "") -> dict:
    url = f"{BASE}/{dataset}?format=JSON&geo=DE&sex=T&lang=EN{extra}"
    raw = subprocess.run(["curl", "-s", url], capture_output=True, check=True).stdout
    return json.loads(raw)


def jsonstat_to_week_dict(d: dict) -> dict:
    dims = d["id"]
    sizes = d["size"]
    idx = d["dimension"]
    fixed = {}
    for dname in dims:
        cats = idx[dname]["category"]["index"]
        if dname != "time":
            fixed[dname] = next(iter(cats.values()))

    def compute(indices_dict):
        pos = 0
        for dname, sz in zip(dims, sizes):
            pos = pos * sz + indices_dict[dname]
        return pos

    out = {}
    for week, w_i in idx["time"]["category"]["index"].items():
        ind = dict(fixed)
        ind["time"] = w_i
        pos = compute(ind)
        val = d["value"].get(str(pos))
        if val is not None:
            out[week] = val
    return out


def main():
    print("Lade demo_r_mwk_ts (Gestorbene je Woche)...")
    weekly_raw = fetch("demo_r_mwk_ts")
    weekly = jsonstat_to_week_dict(weekly_raw)

    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / "eurostat_deaths_weekly.json", "w") as f:
        json.dump(weekly, f)

    weeks = sorted(weekly.keys())
    print(f"{len(weeks)} Wochen: {weeks[0]} bis {weeks[-1]}")


if __name__ == "__main__":
    main()
