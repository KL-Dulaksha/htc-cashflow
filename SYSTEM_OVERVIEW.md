# HTC CashFlow Application — Architecture & Codebase Overview

## 1. Business Context & Workflow
- **Application Name:** Hindurangala Tea Collectors (HTC) — Cash Flow & Distribution System.
- **Industry:** Sri Lankan Tea Leaf Collection Agency.
- **Core Purpose:** Manage and track daily cash disbursements to hundreds of smallholder tea leaf suppliers across multiple transportation routes and rounds, and calculate exact physical currency denominations (Rs. 5000, 1000, 500, 100, 50, 20, 10, 5, 2, 1) for cashiers and delivery lorry drivers.
- **Billing Period Model:**
  - Sri Lankan tea factories operate on monthly billing books (e.g., `2026-10` for October).
  - Suppliers are paid in the **following month** (e.g. October's leaf supply is paid in late November).
  - Therefore, payment transactions entered on calendar dates in November belong to the **October payment cycle**.

## 2. Technical Stack
- **Framework:** Python 3.14 + PyQt6 desktop GUI (frameless dark-themed custom window).
- **Packaging:** PyInstaller single-file Windows executable (`HTC CashFlow.exe`).
- **Data Persistence:** Local JSON-based storage:
  - `htc_meta.json`: Stores system configuration (e.g., `"active_cycle": "2026-10"`).
  - `htc_cycles/{cycle_key}.json`: Independent data file for each billing month (e.g., `2026-10.json`).
  - Key Schema inside cycle files: `"{Route}|{Cycle}|{Date}"` (e.g. `"Store|2026-10|2026-11-24"`).
  - Value Schema: List of entry dictionaries: `[{"id": "101", "amount": 15000, "round": 1, "note": ""}, ...]`.
  - `htc_backups/`: Rolling backups and automated 5-minute snapshots (`{cycle}.json.{YYYY-MM-DD_HHMM}.bak`).
- **External Integration:**
  - Local FastAPI Tea ERP server at `http://localhost:8000`.
  - Connects to `/api/operator/payments` via a background thread (`WebAppFetcher`) to fetch supplier net payables and check for supplier debt warnings.

## 3. Key Modules & Functional Workflows
1. **Payment Book (Page 1):**
   - Fast keyboard-driven payment entry (`Supplier ID -> Amount -> Note -> Enter`).
   - Route selector (`Store`, `ජානක`, `සමින්ද`, `මනෝජ්`, `සම්පත්`) and Round selector (`Round 1` to `Round 5`).
   - Combined multi-route table for the currently selected date.
   - Batch actions: Edit entry, Delete selected, Move entries across routes/rounds.
   - Search Dialog across all dates in the cycle.
2. **Cash Breakdown (Page 2):**
   - Greedy denomination algorithm calculating counts of Rs. 5000, 1000, 500, 100, 50, 20, 10, 5, 2, 1 notes and coins needed for physical cash distribution.
   - Direct thermal printing (`_print_route`) formatted for 80mm POS receipt printers.
3. **Monthly Summary (Page 3):**
   - High-level overview of total cash disbursed, comparison against ERP system payables, and breakdown per route.
4. **Data Protection & Reliability Layer:**
   - **Single-Instance Mutex:** Windows named mutex `HTC_CashFlow_SingleInstance_Mutex` to ensure duplicate processes bring the existing window to front and exit.
   - **Physical Disk Sync:** Atomic write via `.tmp` file with `f.flush()` and `os.fsync(f.fileno())` to survive sudden electrical power outages.
   - **5-Minute Auto-Backup Timer:** `QTimer` background snapshots into `htc_backups/`.
   - **Auto-Recovery:** Detects power-loss corruptions (null bytes, cut-off JSON), recovers valid entries, and selects the recovery source with the highest entry count.
   - **Safety Guard:** Blocks empty memory state `{}` from overwriting populated files on disk.
   - **Mouse-Wheel Ignore:** Event filters on DateEdit and ComboBoxes to prevent accidental scroll changes.
