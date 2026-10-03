"""Project-wide settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

# REES46 "eCommerce Events History in Cosmetics Shop" (monthly CSV files)
EVENTS_GLOB = "cosmetics/*.csv"
# Kaggle "Marketing A/B Testing" (faviovaz)
AB_FILE = RAW / "marketing_AB.csv"

ENGAGED_MIN_VIEWS = 3   # "Engaged" (activation proxy) = at least 3 product views
ALPHA = 0.05            # significance level
SEED = 42
