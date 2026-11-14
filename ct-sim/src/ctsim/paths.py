"""Project paths. ROOT is the ct-sim folder (two levels above this file)."""
import os
from pathlib import Path

# CTSIM_ROOT lets a deployed copy (e.g. a Modal container) point at a data folder that is not next to the source.
ROOT = Path(os.environ.get("CTSIM_ROOT") or Path(__file__).resolve().parents[2])
DATA = ROOT / "data"
RAW = DATA / "raw"
POPULATION = DATA / "population"
ROUTING = DATA / "routing"
SCREENING = DATA / "screening"
MODEL_OUT = DATA / "model"
CONFIGS = ROOT / "configs"
MUNICIPALITIES_CSV = ROUTING / "municipalities.csv"
