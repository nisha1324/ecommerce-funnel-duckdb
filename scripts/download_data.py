"""Download the Olist Brazilian e-commerce CSVs into data/raw/.

Source: Olist's public mirror on GitHub (olist/work-at-olist-data), the same
data published on Kaggle as "Brazilian E-Commerce Public Dataset by Olist".
The geolocation table (~60 MB) is skipped; the analysis doesn't need it.
"""
from pathlib import Path
import time
import urllib.request

BASE = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets"
TABLES = [
    "orders",
    "order_items",
    "order_payments",
    "order_reviews",
    "customers",
    "products",
    "sellers",
]
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def fetch(url: str, dest: Path, retries: int = 3) -> None:
    for attempt in range(1, retries + 1):
        try:
            urllib.request.urlretrieve(url, dest)
            return
        except OSError as exc:
            if attempt == retries:
                raise
            print(f"  retry {attempt} after error: {exc}")
            time.sleep(2 * attempt)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        dest = RAW / f"olist_{table}_dataset.csv"
        if dest.exists():
            print(f"skip  {dest.name} (already downloaded)")
            continue
        print(f"fetch {dest.name}")
        fetch(f"{BASE}/{dest.name}", dest)
    print(f"done: {len(TABLES)} files in {RAW}")


if __name__ == "__main__":
    main()
