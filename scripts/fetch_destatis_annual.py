"""Laedt die Destatis-Zeitreihe "Ehescheidungen, Eheschliessungen, Geborene
und Gestorbene - Zeitreihen 1841-2024" (jaehrliche Rohdaten, Basis fuer
build_data.py).
"""
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
URL = (
    "https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/"
    "Eheschliessungen-Ehescheidungen-Lebenspartnerschaften/Publikationen/"
    "Downloads-Eheschliessungen/statistischer-bericht-ehescheidungen-"
    "eheschliessungen-geborene-gestorbene-zeitreihen-5126107.xlsx"
    "?__blob=publicationFile&v=4"
)


def main():
    DATA_DIR.mkdir(exist_ok=True)
    out_xlsx = DATA_DIR / "destatis_zeitreihen_1841-2024.xlsx"
    subprocess.run(["curl", "-sL", "-o", str(out_xlsx), URL], check=True)
    size = out_xlsx.stat().st_size
    if size < 100_000:  # Fehlerseite (404 etc.) ist deutlich kleiner als die echte Datei
        raise RuntimeError(f"Download sieht fehlerhaft aus ({size} bytes) - URL/Version pruefen")
    print(f"{out_xlsx.name}: {size} bytes")


if __name__ == "__main__":
    main()
