"""Bettet dashboard_data.json in das Template ein und schreibt index.html."""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent

def main():
    template = (ROOT / "index_template.html").read_text()
    data = json.loads((ROOT / "data" / "dashboard_data.json").read_text())
    data["monthly"] = json.loads((ROOT / "data" / "monthly_data.json").read_text())
    data["monthly_age_adjusted"] = json.loads((ROOT / "data" / "monthly_age_adjusted.json").read_text())
    data["weekly_age_adjusted"] = json.loads((ROOT / "data" / "weekly_age_adjusted.json").read_text())

    html = template.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    html = html.replace("__BUILD_DATE__", date.today().isoformat())

    (ROOT / "index.html").write_text(html)
    print("index.html geschrieben")


if __name__ == "__main__":
    main()
