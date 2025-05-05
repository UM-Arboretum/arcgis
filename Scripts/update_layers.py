"""
update_layers.py

1) Runs your summary.py to rebuild the three CSVs.
2) Authenticates to ArcGIS Online.
3) Overwrites each hosted feature service with the corresponding CSV.
"""
import os
import subprocess
from arcgis.gis import GIS
from dotenv import load_dotenv
from arcgis.features import FeatureLayerCollection

load_dotenv()

# ─── STEP 0: regenerate your CSVs ───────────────────────────────────────────────
subprocess.check_call(["python", "Scripts/summary.py"])

# ─── STEP 1: authenticate ───────────────────────────────────────────────────────
gis = GIS(
    os.environ["AGO_ORG_URL"],
    username=os.environ["AGO_USERNAME"],
    password=os.environ["AGO_PASSWORD"],
)

# ─── STEP 2: map each CSV to its Feature Layer Item ID ─────────────────────────
layer_map = {
    "Dendrometer_Average.csv": os.environ["DENDRO_AVG_ITEMID"],
    "Dendrometer_Daily.csv":   os.environ["DENDRO_DAILY_ITEMID"],
    "TMS_Average.csv":         os.environ["TMS_AVG_ITEMID"],
    "Dendrometer_DBH_Difference.csv":  os.environ["DBH_ITEMID"]
}

# ─── STEP 3: overwrite each layer ───────────────────────────────────────────────
for csv_name, item_id in layer_map.items():
    print(f"\n🔄 Overwriting '{item_id}' with {csv_name}…")
    item = gis.content.get(item_id)
    flc = FeatureLayerCollection.fromitem(item)

    # Iterate through the layers to find the one with time enabled
    for layer in flc.layers:
        if 'date' in [field['name'] for field in layer.properties.fields]:
            # We found the layer with the 'date' field, so let's enable time on it
            time_info = {
                "timeField": "date",  # Field holding time data
                "timeFormat": "esriTimeUnitsMinutes",  # You can adjust time units
                "timeExtent": None  # Default to the entire time range (optional)
            }
            layer.manager.update_definition({
                "timeInfo": time_info
            })
            print(f"✅ Time enabled on layer '{item_id}' with 'date' field.")
            break  # Stop iterating once we've found the correct layer

    # Overwrite the layer with the new CSV
    flc.manager.overwrite(csv_name)
    print(f"✅ {item_id} overwritten successfully.")

print("\n🎉 All done!")
