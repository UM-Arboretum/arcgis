#!/usr/bin/env python3
"""
summary.py

Generates summary CSVs for Dendrometer and TMS,
merges them into your JOINED.*.csv metadata files,
produces daily summaries per sensor,
and computes DBH differences.

These files will be used in ArcGIS Online to build our Story.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from pytz import timezone

# -----------------------------
# Config
# -----------------------------
EXTRACT_FOLDER = "./Extracted"
SUMMARIES_FOLDER = "./Summaries"
DBH_STATIC_FOLDER = "./DBH_Raw"
TIMEZONE = timezone("America/New_York")

JOINED_DENDRO_CSV = "./joined_dendro.csv"
JOINED_TMS_CSV = "./joined_tms.csv"

def convert_to_eastern(dt_string):
    dt = datetime.strptime(dt_string, "%Y.%m.%d %H:%M")
    local_dt = timezone("UTC").localize(dt).astimezone(TIMEZONE)
    return local_dt.replace(tzinfo=None)

# -----------------------------
# Daily Summary Logic
# -----------------------------
def daily_summary(df, station_id, dest_folder):
    df["Timestamp"] = pd.to_datetime(df["Timestamp"].astype(str), format="%Y.%m.%d %H:%M")
    df.sort_values("Timestamp", inplace=True)

    df["Date"] = df["Timestamp"].dt.date

    grouped = df.groupby("Date").agg(
        T1_Min=("T1", "min"),
        T1_Max=("T1", "max"),
        T2_Min=("T2", "min"),
        T2_Max=("T2", "max"),
        T3_Min=("T3", "min"),
        T3_Max=("T3", "max"),
        Soil_Min=("SM", "min"),
        Soil_Max=("SM", "max"),
        Shake_Max=("SH", "max"),
        Rows=("Timestamp", "count"),
    ).reset_index()

    dest_path = os.path.join(dest_folder, f"{station_id}_daily.csv")
    grouped.to_csv(dest_path, index=False, encoding="utf-8")

# -----------------------------
# Summarize each folder file
# -----------------------------
def summarize_folder(folder, dest_folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".csv"):
                full_path = os.path.join(root, file)

                try:
                    df = pd.read_csv(full_path, encoding='latin1')
                except UnicodeDecodeError:
                    df = pd.read_csv(full_path, encoding="utf-8", errors="ignore")

                station_id = Path(file).stem.split("_")[0]
                daily_summary(df, station_id, dest_folder)

# -----------------------------
# DBH Processing
# -----------------------------
def compute_dbh_df(path, sep=";", start_row=1):
    try:
        raw = pd.read_csv(path, header=None, sep=sep, engine="python", encoding="latin1")
    except UnicodeDecodeError:
        raw = pd.read_csv(path, header=None, sep=sep, engine="python", encoding="utf-8", errors="ignore")

    df = raw.iloc[start_row:].copy()
    df.reset_index(drop=True, inplace=True)

    df.columns = [
        "Sensor", "Timestamp", "X3", "T1", "T2", "T3", "Size",
        "Humidity", "Battery", "X"
    ]

    df["Timestamp"] = df["Timestamp"].apply(convert_to_eastern)
    df.sort_values("Timestamp", inplace=True)

    if df["Size"].dtype != float and df["Size"].dtype != int:
        df["Size"] = pd.to_numeric(df["Size"], errors="coerce")

    rollover_points = df[df["Size"] == 8890].index.tolist()

    if rollover_points:
        last_8890_index = rollover_points[-1]
        baseline = 8890
        df.loc[last_8890_index + 1:, "Size"] += baseline

    return df

# -----------------------------
# Process DBH Raw Folder
# -----------------------------
def process_dbh_folder(folder):
    all_data = []

    for file in os.listdir(folder):
        if not file.lower().endswith(".csv"):
            continue

        full_path = os.path.join(folder, file)
        print(f"Processing DBH: {file}")

        df = compute_dbh_df(full_path)
        sensor_id = Path(file).stem.split("_")[0]
        df["Sensor_ID"] = sensor_id
        all_data.append(df)

    if not all_data:
        print("No DBH files found.")
        return None

    combined = pd.concat(all_data, ignore_index=True)

    daily = combined.groupby(["Sensor_ID", combined["Timestamp"].dt.date]).agg(
        Min_Size=("Size", "min"),
        Max_Size=("Size", "max")
    ).reset_index()

    daily["Growth_mm"] = daily["Max_Size"] - daily["Min_Size"]
    daily["Growth_cm"] = daily["Growth_mm"] / 10.0

    out_path = os.path.join(SUMMARIES_FOLDER, "dbh_summary.csv")
    daily.to_csv(out_path, index=False, encoding="utf-8")

    print("DBH summary generated:", out_path)

    return daily

# -----------------------------
# Metadata Join
# -----------------------------
def join_metadata():
    try:
        df_meta_d = pd.read_csv(JOINED_DENDRO_CSV, encoding='latin1')
    except UnicodeDecodeError:
        df_meta_d = pd.read_csv(JOINED_DENDRO_CSV, encoding="utf-8", errors="ignore")

    try:
        df_meta_t = pd.read_csv(JOINED_TMS_CSV, encoding='latin1')
    except UnicodeDecodeError:
        df_meta_t = pd.read_csv(JOINED_TMS_CSV, encoding="utf-8", errors="ignore")

    return df_meta_d, df_meta_t


if __name__ == "__main__":
    os.makedirs(SUMMARIES_FOLDER, exist_ok=True)

    print("Generating climate summaries...")
    summarize_folder(EXTRACT_FOLDER, SUMMARIES_FOLDER)

    print("Processing DBH corrections...")
    process_dbh_folder(DBH_STATIC_FOLDER)

    print("Joining metadata...")
    df_meta_d, df_meta_t = join_metadata()

    print("✅ All tasks complete.")
