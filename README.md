# 🌳 Arboretum ArcGIS Story & Map Automation

This repository automatically updates ArcGIS Online feature layers when new data is added or modified, either *manually* or through *automated syncing* with the dashboard repository.

---

## 📂 Watched Folders

The following folders are synced from the dashboard and monitored for changes:

•⁠  ⁠⁠ TMS_Data/ ⁠

•⁠  ⁠⁠ Dendrometer_Data/ ⁠

Any additions, updates, or deletions within these folders will trigger an update to the ArcGIS layers.

---

## ⚡ How the Automation Works

There are *two ways* the update process can be triggered:

### ✅ 1. *Automatic Trigger (Dashboard Sync)*

Changes made to the dashboard repository (⁠ arboretum ⁠) will automatically propagate to this repo and update ArcGIS layers.

Steps:

•⁠  ⁠New data is committed to the [Dashboard repo](https://github.com/UM-Arboretum/dashboard).

•⁠  ⁠That triggers a ⁠ repository_dispatch ⁠ to this repo (⁠ dashboard-data-updated ⁠).

•⁠  ⁠⁠ fetch-dashboard-data.yml ⁠ pulls the latest folders (⁠ TMS_Data/ ⁠ and ⁠ Dendrometer_Data/ ⁠) and commits them here.

•⁠  ⁠It then triggers a second workflow, ⁠ update_urls.yml ⁠, which pushes the data to ArcGIS Online.


### 🧑‍💻 2. *Manual Trigger*

You can also manually run the update process without new data commits.

Steps:

•⁠  ⁠Go to the *Actions* tab on GitHub.

•⁠  ⁠Select the *Update Layers* workflow.

•⁠  ⁠Click *"Run workflow"* manually.


Result: The ⁠ update_layers.py ⁠ script will run with the current data in the repo.

---

## 🔒 Environment Variables

The workflows use the following GitHub Secrets (configured in repo Settings → Secrets → Actions):

•⁠  ⁠⁠ AGO_ORG_URL ⁠

•⁠  ⁠⁠ AGO_USERNAME ⁠

•⁠  ⁠⁠ AGO_PASSWORD ⁠

•⁠  ⁠⁠ DENDRO_AVG_ITEMID ⁠

•⁠  ⁠⁠ DENDRO_DAILY_ITEMID ⁠

•⁠  ⁠⁠ TMS_AVG_ITEMID ⁠

•⁠  ⁠⁠ DBH_ITEMID ⁠

•⁠  ⁠⁠ DASHBOARD_PAT ⁠ ← used by the fetch workflow to clone the private Dashboard repo


These secrets must be properly configured for everything to run correctly.

---

## 🚨 Important Notes

•⁠  ⁠If your sync or update doesn't seem to trigger automatically, check the *Actions* tab for logs and events.

•⁠  ⁠The fetch workflow uses the [⁠ peter-evans/repository-dispatch ⁠](https://github.com/peter-evans/repository-dispatch) GitHub Action to fire custom events between workflows.

•⁠  ⁠If you need help setting secrets or reviewing logs, contact *dag204@miami.edu*.
