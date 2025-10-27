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
import re
import glob
import pandas as pd

# ─── CONFIG ────────────────────────────────────────────────────────────────────

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))  # parent of Scripts/
DENDRO_DATA_DIR = os.path.join(ROOT_DIR, "Dendrometer_Data")
TMS_DATA_DIR    = os.path.join(ROOT_DIR, "TMS_Data")

JOINED_DENDRO_CSV = os.path.join(ROOT_DIR, "JOINED.DENDROMETER.csv")
JOINED_TMS_CSV   = os.path.join(ROOT_DIR, "JOINED.TMS.csv")

START_DBH_CSV     = os.path.join(ROOT_DIR, "Dendrometer_Start_DBH.csv")

OUTPUT_DENDRO      = os.path.join(ROOT_DIR, "Dendrometer_Average.csv")
OUTPUT_TMS         = os.path.join(ROOT_DIR, "TMS_Average.csv")
OUTPUT_DENDRO_DAILY= os.path.join(ROOT_DIR, "Dendrometer_Daily.csv")
OUTPUT_TMS_DAILY   = os.path.join(ROOT_DIR, "TMS_Daily.csv")
OUTPUT_DBH_DF      = os.path.join(ROOT_DIR, "Dendrometer_DBH_Raw.csv")
OUTPUT_DBH_MERGED  = os.path.join(ROOT_DIR, "Dendrometer_DBH_Difference.csv")


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def summarize_folder(data_dir, metrics, sep=';', verbose=True):
    """
    Compute overall mean metrics per sensor.
    """
    records = []
    pattern = re.compile(r"data_(\d+)_\d{4}_\d{2}_\d{2}_\d+\.csv")
    paths = glob.glob(os.path.join(data_dir, "data_*.csv"))

    for path in paths:
        fname = os.path.basename(path)
        m = pattern.match(fname)
        if not m:
            if verbose: print(f"⚠️  skipping unexpected filename: {fname}")
            continue
        sensor_id = int(m.group(1))

        df = pd.read_csv(path, header=None, sep=sep, engine='python', encoding='latin1')
        if df.shape[1] <= max(metrics.values()):
            if verbose: print(f"⚠️  {fname} only has {df.shape[1]} cols—skipping")
            continue

        summary = {'sensor_id': sensor_id}
        for col_name, idx in metrics.items():
            summary[col_name] = df.iloc[:, idx].mean()
        records.append(summary)

    if verbose:
        print(f"  • scanned {len(paths)} files, produced {len(records)} summaries")
    return pd.DataFrame(records)


def daily_summary(data_dir, metrics, sep=';', verbose=True):
    """
    Compute daily mean metrics per sensor.
    Returns DataFrame: sensor_id, date, <metrics>
    """
    dfs = []
    pattern = re.compile(r"data_(\d+)_\d{4}_\d{2}_\d{2}_\d+\.csv")
    paths = glob.glob(os.path.join(data_dir, "data_*.csv"))

    for path in paths:
        fname = os.path.basename(path)
        m = pattern.match(fname)
        if not m:
            if verbose: print(f"⚠️  skipping unexpected filename: {fname}")
            continue
        sensor_id = int(m.group(1))

        df = pd.read_csv(path, header=None, sep=sep, engine='python', encoding='latin1')
        if df.shape[1] <= max(metrics.values()) or df.shape[1] <= 1:
            if verbose: print(f"⚠️  {fname} only has {df.shape[1]} cols—skipping")
            continue

        data = df.iloc[:, [1] + list(metrics.values())].copy()
        data.columns = ['timestamp'] + list(metrics.keys())
        data['sensor_id'] = sensor_id
        dfs.append(data)

    if not dfs:
        return pd.DataFrame()

    all_data = pd.concat(dfs, ignore_index=True)
    all_data['timestamp'] = pd.to_datetime(
        all_data['timestamp'], format="%Y.%m.%d %H:%M", errors='coerce'
    )
    all_data['date'] = all_data['timestamp'].dt.date

    daily = (
        all_data
        .groupby(['sensor_id','date'])[list(metrics.keys())]
        .mean()
        .reset_index()
    )
    if verbose:
        print(f"  • aggregated to {len(daily)} daily rows")
    return daily


def compute_dbh_df(dendro_dir, start_dbh_path, sep=';', verbose=True):
    """
    Returns DataFrame with columns: sensor_id, start_DBH, end_DBH, dbh_diff
    Uses the last column value for dendrometer raw growth.
    """
    dbh_df = pd.read_csv(start_dbh_path, encoding='latin1')
    if 'ID' not in dbh_df.columns or 'start_DBH' not in dbh_df.columns:
        raise ValueError("START_DBH_CSV must have columns ID and start_DBH")

    records = []
    pattern = re.compile(r"data_(\d+)_\d{4}_\d{2}_\d{2}_\d+\.csv")
    for path in glob.glob(os.path.join(dendro_dir, "data_*.csv")):
        fname = os.path.basename(path)
        m = pattern.match(fname)
        if not m:
            continue
        sid = int(m.group(1))

        raw = pd.read_csv(path, header=None, sep=sep, engine='python', encoding='latin1')
        if raw.empty or raw.shape[1] < 7:
            continue

        last_size = float(raw.iloc[-1, 6])
        start_val = float(dbh_df.loc[dbh_df['ID'] == sid, 'start_DBH'].iloc[0])

        end_val = start_val + (last_size / 10000) * 2
        dbh_diff = end_val - start_val

        records.append({
            'sensor_id': sid,
            'start_DBH': round(start_val, 2),
            'end_DBH': round(end_val, 2),
            'dbh_diff': round(dbh_diff, 2),
        })

    if verbose:
        print(f"  • computed DBH for {len(records)} sensors")
    return pd.DataFrame(records)


# ─── MAIN PROCESS ──────────────────────────────────────────────────────────────

print("🔄 Summarizing dendrometer data…")
dendro_metrics = {'avg_air_temp': 3, 'avg_growth': 6}

df_dendro_sum = summarize_folder(DENDRO_DATA_DIR, dendro_metrics)

print(f"🔄 Reading metadata from {JOINED_DENDRO_CSV}")
df_meta_d = pd.read_csv(JOINED_DENDRO_CSV, encoding='latin1')

print("🔄 Merging summaries into metadata")
df_dendro_out = df_meta_d.merge(df_dendro_sum, on='sensor_id', how='left')

print(f"🔄 Writing output to {OUTPUT_DENDRO}")
df_dendro_out.to_csv(OUTPUT_DENDRO, index=False)


print("🔄 Building daily dendrometer summaries…")
dendro_daily = daily_summary(DENDRO_DATA_DIR, dendro_metrics)
meta_sel = df_meta_d[['sensor_id','X','Y','Common_Name']]
df_dendro_daily = dendro_daily.merge(meta_sel, on='sensor_id', how='left')

print(f"🔄 Writing output to {OUTPUT_DENDRO_DAILY}")
df_dendro_daily.to_csv(OUTPUT_DENDRO_DAILY, index=False)


print("🔄 Summarizing TMS data…")
tms_metrics = {'avg_t1':3,'avg_t2':4,'avg_t3':5,'avg_moist':6}

df_tms_sum = summarize_folder(TMS_DATA_DIR, tms_metrics)

print(f"🔄 Reading metadata from {JOINED_TMS_CSV}")
df_meta_t = pd.read_csv(JOINED_TMS_CSV, encoding='latin1')

print("🔄 Merging TMS summaries into metadata")
df_tms_out = df_meta_t.merge(df_tms_sum, on='sensor_id', how='left')

print(f"🔄 Writing output to {OUTPUT_TMS}")
df_tms_out.to_csv(OUTPUT_TMS, index=False)


print("🔄 Building daily TMS summaries…")
tms_daily = daily_summary(TMS_DATA_DIR, tms_metrics)
meta_sel_t = df_meta_t[['sensor_id','X','Y','Common_Name']]
df_tms_daily = tms_daily.merge(meta_sel_t, on='sensor_id', how='left')

print(f"🔄 Writing output to {OUTPUT_TMS_DAILY}")
df_tms_daily.to_csv(OUTPUT_TMS_DAILY, index=False)


# ─── DBH DIFFERENCE ───────────────────────────────────────────────────────────

print("🔄 Computing DBH raw values...")
df_dbh = compute_dbh_df(DENDRO_DATA_DIR, START_DBH_CSV)
df_dbh.to_csv(OUTPUT_DBH_DF, index=False)
print(f"  • wrote raw DBH to {OUTPUT_DBH_DF}")

df_dbh_merged = df_meta_d.merge(df_dbh, on='sensor_id', how='left')
df_dbh_merged.to_csv(OUTPUT_DBH_MERGED, index=False)
print(f"🔄 Merging DBH difference to {OUTPUT_DBH_MERGED}")

print("✅ All is done! :)")
