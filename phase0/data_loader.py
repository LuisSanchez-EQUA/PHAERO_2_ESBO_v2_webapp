import json
from pathlib import Path
from typing import Dict

import pandas as pd

from .paths import ZONE_DATA_PATH, ZONE_TYPES_PATH, ZONES_JSON_PATH


def read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp1252")


def load_zone_types(path: Path = ZONE_TYPES_PATH) -> Dict[str, str]:
    df = read_csv_robust(path)
    df.columns = [column.strip() for column in df.columns]
    if "code" not in df.columns or "description" not in df.columns:
        raise ValueError("zone_types.csv must have headers: 'code' and 'description'")

    df["code"] = df["code"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["description"] = df["description"].astype(str).str.strip()
    return dict(zip(df["code"], df["description"]))


def load_zone_data(path: Path = ZONE_DATA_PATH) -> Dict[str, Dict[str, float]]:
    df = read_csv_robust(path)
    df.columns = [column.strip() for column in df.columns]
    required = {"code", "occupants", "lights", "equipment", "CAVsup", "CAVret"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"zone_data.csv missing required columns: {missing}")

    df["code"] = df["code"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    for column in ["occupants", "lights", "equipment", "CAVsup", "CAVret"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    result: Dict[str, Dict[str, float]] = {}
    for _, row in df.iterrows():
        result[row["code"]] = {
            "occupants": float(row["occupants"]),
            "lights": float(row["lights"]),
            "equipment": float(row["equipment"]),
            "CAVsup": float(row["CAVsup"]),
            "CAVret": float(row["CAVret"]),
        }
    return result


def load_zones_from_json(path: Path = ZONES_JSON_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
