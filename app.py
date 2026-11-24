"""
HTC Cash Flow Application
Hindurangala Tea Collectors — PyQt6 Application

Features:
  1. Custom dark title bar (frameless window)
  2. Sidebar navigation with 3 pages (Book, Cash Breakdown, Summary)
  3. Monthly cycle + date-based data management
  4. Cross-cycle duplicate Supplier ID checking
  5. Per-route denomination calculation
  6. Monthly summary with per-route totals
"""

import sys, json, os, re, shutil, glob
from datetime import date, datetime, timedelta
from calendar import month_name, month_abbr, monthrange
from urllib import request as urllib_req, parse as urllib_parse, error as urllib_error
from http.cookiejar import CookieJar
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QSpacerItem, QDateEdit, QAbstractItemView, QMessageBox,
    QStackedWidget, QDialog, QProgressBar, QScrollArea, QStyledItemDelegate,
    QCalendarWidget
)
from PyQt6.QtCore import Qt, QDate, QSize, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush, QMouseEvent, QPalette, QTextDocument, QIcon, QShortcut, QKeySequence, QPainter, QPen, QTextCharFormat
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo

DENOMINATIONS = [5000, 1000, 500, 100, 50, 20, 10, 5, 2, 1]
LORRY_ROUTES = ["ජානක", "සමින්ද", "මනෝජ්", "සම්පත්"]
STORE_ROUTE = "Store"
ROUTES = LORRY_ROUTES + [STORE_ROUTE]
ALL_ROUTES_ORDERED = [STORE_ROUTE] + LORRY_ROUTES   # display order for book
ROUTE_COLORS = {
    "Store": "#66dd88",
    "ජානක": "#88aaff",
    "සමින්ද": "#ff88aa",
    "මනෝජ්": "#88dddd",
    "සම්පත්": "#dddd88",
}
# When running as a PyInstaller .exe, __file__ points to a temp folder.
# Use sys.executable so data is saved next to the .exe itself.
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
META_FILE = os.path.join(_APP_DIR, "htc_meta.json")
CYCLES_DIR = os.path.join(_APP_DIR, "htc_cycles")
BACKUPS_DIR = os.path.join(_APP_DIR, "htc_backups")
LEGACY_DATA_FILE = os.path.join(_APP_DIR, "htc_data.json")
BACKUP_RETENTION_DAYS = 30

STYLESHEET = """
QMainWindow, QWidget { background-color: #141420; }
QWidget#centralWidget { background-color: #141420; }

/* Remove focus dotted outlines globally */
* { outline: none; }
QPushButton:focus { outline: none; border: none; }
QComboBox:focus { outline: none; }
QDateEdit:focus { outline: none; }

/* Title Bar */
QWidget#titleBar { background-color: #10101a; border-bottom: 1px solid #444466; }
QLabel#appTitleBar { color: #ffffff; font-size: 14px; font-weight: 600; letter-spacing: 0.5px; }
QPushButton#tbMinBtn, QPushButton#tbMaxBtn, QPushButton#tbCloseBtn {
    background-color: transparent; border: none; border-radius: 0;
    font-size: 14px; min-width: 46px; min-height: 32px; color: #ffffff; padding: 0;
}
QPushButton#tbMinBtn:hover, QPushButton#tbMaxBtn:hover { background-color: #3a3a5a; color: #ffffff; }
QPushButton#tbCloseBtn:hover { background-color: #c0392b; color: #ffffff; }
QPushButton#tbCloseBtn:pressed { background-color: #962d22; }

/* Sidebar */
QFrame#sidebar { background-color: #10101a; border-right: 1px solid #444466; }
QLabel#sidebarTitle { color: #ffffff; font-size: 16px; font-weight: 700; padding: 8px 0; }
QPushButton#navBtn {
    background-color: transparent; color: #ffffff; border: none;
    border-left: 3px solid transparent; padding: 13px 16px;
    font-size: 14px; font-weight: 600; text-align: left; border-radius: 0;
    min-height: 18px; outline: none;
}
QPushButton#navBtn:hover { background-color: #2a2a48; color: #ffffff; }
QPushButton#navBtn:focus { outline: none; border: none; border-left: 3px solid transparent; }
QPushButton#navBtn[active="true"] {
    background-color: #2a2a48; color: #ffffff;
    border-left: 3px solid #9b8cff;
}
QPushButton#navBtn[active="true"]:focus { border-left: 3px solid #9b8cff; }

/* Cards */
QFrame#card { background-color: #202036; border-radius: 16px; border: 1px solid #4a4a6a; }

/* Labels */
QLabel#pageTitle { color: #ffffff; font-size: 22px; font-weight: 700; padding: 2px 0; }
QLabel#sectionLabel { color: #ffffff; font-size: 14px; font-weight: 600; padding: 2px 0; }
QLabel#subtitleLabel { color: #ffffff; font-size: 14px; font-weight: 600; }
QLabel#statusLabel { color: #ffffff; font-size: 14px; padding: 20px; }
QLabel#grandTotalValue { color: #bbffbb; font-size: 34px; font-weight: 800; padding: 6px 0; }
QLabel#grandTotalCaption { color: #ffffff; font-size: 11px; font-weight: 600; letter-spacing: 1.5px; }
QLabel#routeBadgeLabel {
    color: #ffffff; font-size: 14px; font-weight: 600; padding: 5px 18px;
    background-color: rgba(120,100,255,60); border-radius: 14px;
}
QLabel#readonlyBanner {
    color: #ffff88; font-size: 13px; font-weight: 600;
    background-color: rgba(200,150,30,0.25); border: 1px solid rgba(220,170,40,0.55);
    border-radius: 0; padding: 8px 14px;
}
QLabel#dateNavLabel { color: #ffffff; font-size: 13px; font-weight: 600; }

/* ComboBox */
QComboBox {
    background-color: #1c1c30; color: #ffffff; border: 2px solid #4a4a70;
    border-radius: 10px; padding: 10px 16px; font-size: 16px; font-weight: 600; min-height: 22px;
}
QComboBox:hover { border-color: #7b7bf7; }
QComboBox:focus { border-color: #9b9bff; background-color: #2e2e50; }
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right; width: 36px;
    border-left: 1px solid #4a4a70; border-top-right-radius: 10px;
    border-bottom-right-radius: 10px; background-color: #303055;
}
QComboBox::down-arrow { width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background-color: #1c1c30; color: #ffffff; border: 2px solid #5a5a8a;
    border-radius: 8px; selection-background-color: #4a4a8a; selection-color: #ffffff;
    padding: 6px; font-size: 16px; outline: none;
}
QComboBox QAbstractItemView::item { padding: 8px 12px; min-height: 28px; border-radius: 6px; }
QComboBox QAbstractItemView::item:hover { background-color: #3a3a6a; }

/* DateEdit */
QDateEdit {
    background-color: #1c1c30; color: #ffffff; border: 2px solid #4a4a70;
    border-radius: 10px; padding: 8px 14px; font-size: 14px; font-weight: 600;
    min-height: 20px; selection-background-color: #4a4a8a;
}
QDateEdit:hover { border-color: #7b7bf7; }
QDateEdit:focus { border-color: #9b9bff; background-color: #2e2e50; }
QDateEdit::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right; width: 30px;
    border-left: 1px solid #4a4a70; border-top-right-radius: 10px;
    border-bottom-right-radius: 10px; background-color: #303055;
}
QDateEdit::down-arrow { image: url("CALENDAR_ICON_PATH"); width: 16px; height: 16px; }
QCalendarWidget { background-color: #ffffff; border: 2px solid #0055a4; border-radius: 8px; min-width: 320px; min-height: 280px; }
QCalendarWidget QAbstractItemView:enabled { background-color: #ffffff; color: #003366; selection-background-color: #007BFF; selection-color: #ffffff; font-size: 16px; font-weight: 600; outline: none; }
QCalendarWidget QAbstractItemView:disabled { color: #b0c4de; background-color: #f7f9fc; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #0055a4; border-top-left-radius: 5px; border-top-right-radius: 5px; min-height: 45px; }
QCalendarWidget QToolButton { color: #ffffff; background-color: transparent; border: none; padding: 8px 12px; font-size: 16px; font-weight: bold; }
QCalendarWidget QToolButton:hover { background-color: #004080; border-radius: 6px; }
QCalendarWidget QToolButton::menu-indicator { image: none; }
QCalendarWidget QMenu { background-color: #ffffff; color: #003366; font-size: 15px; border: 1px solid #0055a4; }
QCalendarWidget QSpinBox { background-color: #ffffff; color: #003366; font-size: 15px; border: 1px solid #0055a4; }

/* Date Nav Buttons */
QPushButton#dateNavBtn {
    background-color: #2a2a48; color: #ffffff; border: 2px solid #4a4a70;
    border-radius: 8px; padding: 6px 14px; font-size: 16px; font-weight: 700; min-height: 20px;
    outline: none;
}
QPushButton#dateNavBtn:hover { border-color: #7b7bf7; color: #ffffff; background-color: #353560; }
QPushButton#dateNavBtn:focus { outline: none; }
QPushButton#todayBtn {
    background-color: rgba(120,100,255,50); color: #ffffff; border: 2px solid #5a5a8a;
    border-radius: 8px; padding: 6px 12px; font-size: 13px; font-weight: 700;
    letter-spacing: 0.5px; min-height: 20px; outline: none;
}
QPushButton#todayBtn:hover { border-color: #9b8cff; background-color: rgba(120,100,255,90); color: #ffffff; }
QPushButton#todayBtn:focus { outline: none; }

/* Inputs */
QLineEdit#amountInput {
    background-color: #1c1c30; color: #ffffff; border: 2px solid #4a4a70;
    border-radius: 10px; padding: 12px 16px; font-size: 18px;
    font-family: 'Consolas', 'Cascadia Code', monospace; font-weight: 600;
    selection-background-color: #4a4a8a; selection-color: #ffffff;
}
QLineEdit#amountInput:hover { border-color: #7b7bf7; }
QLineEdit#amountInput:focus { border-color: #9b9bff; background-color: #2e2e50; }
QLineEdit#amountInput::placeholder { color: #ccccdd; }

/* Tables */
QTableWidget#inputTable {
    background-color: #1c1c30; color: #ffffff; border: 2px solid #4a4a70;
    border-radius: 12px; gridline-color: #444466; font-size: 15px;
    selection-background-color: #4a4a8a; selection-color: #fff; outline: none;
}
QTableWidget#inputTable::item { padding: 6px 14px; border-bottom: 1px solid #3a3a5a; }
QTableWidget#inputTable::item:selected { background-color: #3a3a6a; color: #fff; }
QTableWidget {
    background-color: #1a1a2e; color: #ffffff; border: 2px solid #4a4a6a;
    border-radius: 12px; gridline-color: #444466; font-size: 15px;
    selection-background-color: #4a4a8a; outline: none;
}
QTableWidget::item { padding: 10px 16px; border-bottom: 1px solid #3a3a5a; }
QTableWidget::item:selected { background-color: #3a3a6a; color: #fff; }
QTableWidget::indicator { width: 24px; height: 24px; }
QHeaderView::section {
    background-color: #2a2a48; color: #ffffff; border: none;
    border-bottom: 2px solid #4a4a6a; padding: 10px 16px;
    font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
}

/* Buttons */
QPushButton#removeRowBtn {
    background-color: rgba(240,100,100,0.12); color: #ffcccc; border: 1px solid #554444;
    border-radius: 8px; padding: 7px 16px; font-size: 13px; font-weight: 600;
}
QPushButton#removeRowBtn:hover { background-color: rgba(240,100,100,0.25); border-color: #ff6666; color: #ffdddd; }
QPushButton#clearBtn {
    background-color: transparent; color: #ffffff; border: 2px solid #4a4a70;
    border-radius: 10px; padding: 10px 24px; font-size: 14px; font-weight: 600; min-height: 20px;
}
QPushButton#clearBtn:hover { border-color: #ff6666; color: #ffdddd; background-color: rgba(240,100,100,0.12); }
QPushButton#clearBtn:pressed { background-color: rgba(240,100,100,0.20); }

/* Scrollbar */
QScrollBar:vertical { background: #222240; width: 8px; border-radius: 4px; margin: 2px; }
QScrollBar::handle:vertical { background: #5a5a8a; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #7b7bf7; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* Summary */
QFrame#summaryCard {
    background-color: #202036; border: 1px solid #4a4a6a; border-radius: 14px;
}
QLabel#summaryGrandTotal { color: #bbffbb; font-size: 42px; font-weight: 800; padding: 8px 0; background: transparent; }
QLabel#summaryGrandCaption { color: #ffffff; font-size: 13px; font-weight: 700; letter-spacing: 2px; background: transparent; }
QLabel#summaryRouteName { color: #ffffff; font-size: 14px; font-weight: 600; background: transparent; }
QLabel#summaryRouteValue { color: #ffffff; font-size: 20px; font-weight: 800; background: transparent; }
QLabel#summaryRouteCount { color: #ffffff; font-size: 13px; font-weight: 600; background: transparent; }

/* QMessageBox */
QMessageBox {
    background-color: #202036;
    border: 1px solid #5a5a7a;
}
QMessageBox QLabel {
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
}
QMessageBox QPushButton {
    background-color: #3a3a5a;
    color: #ffffff;
    border: 1px solid #5a5a7a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    min-width: 80px;
}
QMessageBox QPushButton:hover {
    background-color: #4a4a6a;
    border-color: #7b7bf7;
}
"""


# ── Helpers ──────────────────────────────────────────────────────────

def calculate_denomination_breakdown(amounts: list[int]) -> dict:
    grand_total = 0
    aggregated_counts = {d: 0 for d in DENOMINATIONS}
    for amount in amounts:
        if amount <= 0:
            continue
        grand_total += amount
        remaining = amount
        for denom in DENOMINATIONS:
            count, remaining = divmod(remaining, denom)
            aggregated_counts[denom] += count
    return {"grand_total": grand_total, "counts": {d: c for d, c in aggregated_counts.items() if c > 0}}


def format_denomination(value: int) -> str:
    if value >= 100:   return f"Rs. {value:,} Note"
    elif value >= 20:  return f"Rs. {value} Note"
    else:              return f"Rs. {value} Coin"


def _cycle_file(cycle_key: str) -> str:
    """Return the file path for a given cycle key like '2026-02'."""
    os.makedirs(CYCLES_DIR, exist_ok=True)
    return os.path.join(CYCLES_DIR, f"{cycle_key}.json")


def load_meta() -> dict:
    """Load metadata (active_cycle, theme, etc.)."""
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _prune_backups(cycle_key: str):
    """Prune older backups to prevent excessive disk usage while retaining recent history."""
    try:
        pattern = os.path.join(BACKUPS_DIR, f"{cycle_key}.json.*.bak")
        files = glob.glob(pattern)
        now = datetime.now()
        cutoff_recent = (now - timedelta(days=2)).timestamp()  # Keep all 5-min backups for 48 hours
        cutoff_max = (now - timedelta(days=60)).timestamp()     # Purge older than 60 days
        
        daily_kept = set()
        for f in sorted(files, reverse=True):
            mtime = os.path.getmtime(f)
            if mtime < cutoff_max:
                try: os.remove(f)
                except Exception: pass
            elif mtime < cutoff_recent:
                day_tag = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                if day_tag in daily_kept:
                    try: os.remove(f)
                    except Exception: pass
                else:
                    daily_kept.add(day_tag)
    except Exception:
        pass


def create_timed_backup(cycle_key: str, data: dict):
    """Save a timestamped backup (called on 5-min timer and critical actions)."""
    if not cycle_key or not data:
        return
    try:
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        base_name = f"{cycle_key}.json.{now_str}.bak"
        backup_path = os.path.join(BACKUPS_DIR, base_name)
        
        if not os.path.exists(backup_path):
            tmp = backup_path + f".tmp_{os.getpid()}"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, backup_path)
            _prune_backups(cycle_key)
    except Exception as e:
        print(f"[Backup Error] {e}")


def _rolling_backup(filepath: str):
    """Daily timestamped backup for legacy compatibility."""
    if not os.path.exists(filepath):
        return
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    today_tag = date.today().isoformat()
    base_name = os.path.basename(filepath)
    backup_name = f"{base_name}.{today_tag}.bak"
    backup_path = os.path.join(BACKUPS_DIR, backup_name)
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(filepath, backup_path)
        except Exception:
            pass


def _repair_corrupted_json(filepath: str) -> dict:
    """Repair JSON corrupted by sudden power cuts (null bytes, trailing garbage, incomplete arrays)."""
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        
        # 1. Strip trailing null bytes and control whitespace from power loss
        text = raw.decode("utf-8", errors="replace").rstrip("\x00 \r\n\t")
        if not text:
            return {}

        # 2. Try simple clean parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # 3. If file was cut mid-write, trim back to the last complete entry
        last_brace = text.rfind("}")
        while last_brace > 0:
            candidate = text[:last_brace + 1]
            for closing in ["]}", "\n]}", "}", "\n}"]:
                try:
                    return json.loads(candidate + closing)
                except Exception:
                    pass
            last_brace = text.rfind("}", 0, last_brace)
    except Exception as e:
        print(f"[Repair Error] Could not repair {filepath}: {e}")
    return {}


def save_meta(meta: dict):
    """Atomic save for metadata with disk fsync."""
    _rolling_backup(META_FILE)
    tmp = META_FILE + f".tmp_{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, META_FILE)


def _count_entries(data: dict) -> int:
    """Helper to count total payment records across all routes/slots."""
    if not isinstance(data, dict):
        return 0
    total = 0
    for v in data.values():
        if isinstance(v, list):
            total += len(v)
    return total


def load_cycle(cycle_key: str) -> dict:
    """Load cycle data. Only triggers recovery if the file is completely unreadable."""
    path = _cycle_file(cycle_key)
    if not os.path.exists(path):
        return {}

    # ── STANDARD PATH: 100% normal JSON load ─────────────────────────
    # If the file is valid JSON, this is the ONLY code that runs.
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Notice] {path} cannot be read directly ({e}). Checking recovery options...")

    # ── EMERGENCY PATH: File was damaged by sudden power loss ────────
    # 1. Immediately preserve the exact damaged file for safety
    try:
        shutil.copy2(path, path + ".damaged_original.bak")
    except Exception:
        pass

    candidates = []

    # Candidate A: Auto-repaired text (strips null bytes, fixes cut-off arrays)
    repaired = _repair_corrupted_json(path)
    if repaired:
        cnt = _count_entries(repaired)
        if cnt > 0:
            candidates.append((cnt, "repaired file content", repaired))

    # Candidate B: Pre-save backup (.last_good.bak)
    last_good = path + ".last_good.bak"
    if os.path.exists(last_good) and os.path.getsize(last_good) > 10:
        try:
            with open(last_good, "r", encoding="utf-8") as f:
                d = json.load(f)
            cnt = _count_entries(d)
            if cnt > 0:
                candidates.append((cnt, "last-good pre-save backup", d))
        except Exception:
            pass

    # Candidate C: Most recent backups from htc_backups/
    pattern = os.path.join(BACKUPS_DIR, f"{cycle_key}.json.*.bak")
    for bfile in sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:5]:
        if os.path.getsize(bfile) > 10:
            try:
                with open(bfile, "r", encoding="utf-8") as f:
                    d = json.load(f)
                cnt = _count_entries(d)
                if cnt > 0:
                    candidates.append((cnt, f"backup ({os.path.basename(bfile)})", d))
            except Exception:
                pass

    if candidates:
        # Always pick whichever source preserved the HIGHEST number of entries!
        candidates.sort(key=lambda c: c[0], reverse=True)
        best_count, best_source, best_data = candidates[0]
        print(f"[Recovery Safe] Restored {best_count} entries from {best_source}")
        return best_data

    return {}


def save_cycle(data: dict, cycle_key: str):
    """Crash-proof save with disk fsync and empty-data protection."""
    if not cycle_key:
        return
    path = _cycle_file(cycle_key)
    
    # SAFETY GUARD: Never overwrite an existing populated file with an empty dictionary
    if not data and os.path.exists(path) and os.path.getsize(path) > 10:
        try:
            shutil.copy2(path, path + ".empty_prevented.bak")
        except Exception:
            pass
        return

    # Pre-save backup of current state
    if os.path.exists(path) and os.path.getsize(path) > 10:
        try:
            shutil.copy2(path, path + ".last_good.bak")
        except Exception:
            pass

    _rolling_backup(path)
    os.makedirs(CYCLES_DIR, exist_ok=True)
    tmp = path + f".tmp_{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())  # Physical write to disk; survives power cuts
    os.replace(tmp, path)
    create_timed_backup(cycle_key, data)


def _migrate_legacy_to_cycles():
    """One-time migration: split old htc_data.json into per-cycle files."""
    if not os.path.exists(LEGACY_DATA_FILE):
        return
    # Check if already migrated
    if os.path.exists(os.path.join(CYCLES_DIR)) and os.listdir(CYCLES_DIR):
        return  # Already have cycle files, skip
    try:
        with open(LEGACY_DATA_FILE, "r", encoding="utf-8") as f:
            old_data = json.load(f)
    except Exception:
        return

    meta = old_data.pop("_meta", {})
    save_meta(meta)

    # Group entries by cycle
    cycles: dict[str, dict] = {}
    for key, entries in old_data.items():
        if "|" not in key:
            continue
        parts = key.split("|")
        if len(parts) == 3:
            route, cycle, date_str = parts
            if cycle not in cycles:
                cycles[cycle] = {}
            cycles[cycle][key] = entries
        elif len(parts) == 2:
            # Old format route|date — run through migration first
            route, date_str = parts
            cycle = date_str[:7]
            new_key = f"{route}|{cycle}|{date_str}"
            if cycle not in cycles:
                cycles[cycle] = {}
            existing = cycles[cycle].get(new_key, [])
            if isinstance(entries, list):
                existing.extend(entries)
            cycles[cycle][new_key] = existing

    for cycle_key, cycle_data in cycles.items():
        save_cycle(cycle_data, cycle_key)

    # Rename old file so migration doesn't run again
    try:
        os.rename(LEGACY_DATA_FILE, LEGACY_DATA_FILE + ".migrated.bak")
    except Exception:
        pass


def data_key(route: str, cycle_str: str, date_str: str) -> str:
    return f"{route}|{cycle_str}|{date_str}"


def _migrate_slot(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if isinstance(item, dict) and "amount" in item:
            entry = {
                "id": str(item.get("id", "")), 
                "amount": int(item["amount"]),
                "round": int(item.get("round", 1)),
                "note": str(item.get("note", ""))
            }
            result.append(entry)
        elif isinstance(item, (int, float)):
            result.append({"id": "", "amount": int(item), "round": 1, "note": ""})
    return result


# ── Custom Dark Message Box ──────────────────────────────────────────

class DarkMessageBox(QDialog):
    """Frameless dark-themed message box that replaces QMessageBox."""

    ICON_MAP = {
        "question": "❓",
        "warning": "⚠️",
        "info": "ℹ️",
        "error": "❌",
        "success": "✅",
    }

    def __init__(self, parent, title: str, message: str, icon: str = "info",
                 buttons: list[tuple[str, str]] = None, default_btn: int = 0):
        """
        buttons: list of (label, role) where role is 'accept', 'reject', or 'action'.
                 If None, defaults to a single 'OK' button.
        default_btn: index of the default button.
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setModal(True)
        self.setFixedWidth(500)
        self._drag_start = None
        self._clicked_index = -1

        if buttons is None:
            buttons = [("OK", "accept")]

        self.setStyleSheet(
            "DarkMessageBox { background-color: #141420; border: 1.5px solid #4a4a6a; border-radius: 14px; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ──
        header = QWidget()
        header.setStyleSheet(
            "background-color: #10101a; border-top-left-radius: 14px;"
            "border-top-right-radius: 14px; border-bottom: 1px solid #3a3a5a;"
        )
        header.setFixedHeight(48)
        header.setCursor(Qt.CursorShape.SizeAllCursor)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 0, 10, 0)
        hl.setSpacing(10)

        icon_emoji = self.ICON_MAP.get(icon, "ℹ️")
        icon_lbl = QLabel(icon_emoji)
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        hl.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #ffffff; font-size: 15px; font-weight: 700;"
            "letter-spacing: 0.3px; background: transparent;"
        )
        hl.addWidget(title_lbl)
        hl.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #bbbbbb; border: none;"
            "  font-size: 16px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #c0392b; color: #fff; }"
        )
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        root.addWidget(header)

        # ── Body ──
        body = QWidget()
        body.setStyleSheet("background-color: #141420;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 14)
        bl.setSpacing(14)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextFormat(Qt.TextFormat.RichText)
        msg_lbl.setStyleSheet(
            "color: #ffffff; font-size: 16px; font-weight: 600;"
            "line-height: 1.6; background: transparent;"
        )
        bl.addWidget(msg_lbl)
        root.addWidget(body)

        # ── Button bar ──
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            "background-color: #10101a; border-bottom-left-radius: 14px;"
            "border-bottom-right-radius: 14px; border-top: 1px solid #2a2a44;"
        )
        bbl = QHBoxLayout(btn_bar)
        bbl.setContentsMargins(18, 14, 18, 16)
        bbl.setSpacing(12)
        bbl.addStretch()

        self._buttons = []
        for i, (label, role) in enumerate(buttons):
            btn = QPushButton(label)
            btn.setFixedHeight(38)
            btn.setMinimumWidth(100)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if role == "accept":
                btn.setStyleSheet(
                    "QPushButton { background-color: #5b4af7; color: #ffffff; border: none;"
                    "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 700; }"
                    "QPushButton:hover { background-color: #7b6aff; }"
                    "QPushButton:pressed { background-color: #4a3ad6; }"
                )
            elif role == "reject":
                btn.setStyleSheet(
                    "QPushButton { background-color: #3a3a5a; color: #ffffff; border: 1px solid #4a4a6a;"
                    "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 600; }"
                    "QPushButton:hover { background-color: #4a4a6a; color: #ffffff; border-color: #6a6a8a; }"
                )
            elif role == "danger":
                btn.setStyleSheet(
                    "QPushButton { background-color: #a03030; color: #ffdddd; border: none;"
                    "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 700; }"
                    "QPushButton:hover { background-color: #c04040; color: #ffffff; }"
                )
            else:  # action
                btn.setStyleSheet(
                    "QPushButton { background-color: #2a4a3a; color: #bbffcc; border: none;"
                    "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 700; }"
                    "QPushButton:hover { background-color: #3a5a4a; color: #ffffff; }"
                )

            idx = i
            btn.clicked.connect(lambda _, x=idx: self._btn_clicked(x))
            bbl.addWidget(btn)
            self._buttons.append(btn)

        root.addWidget(btn_bar)

        # Set default button focus
        if 0 <= default_btn < len(self._buttons):
            self._buttons[default_btn].setFocus()
            self._buttons[default_btn].setDefault(True)

        self.adjustSize()

    def _btn_clicked(self, index: int):
        self._clicked_index = index
        self.accept()

    def clicked_index(self) -> int:
        return self._clicked_index

    # ── Dragging ──
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_start and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, e):
        self._drag_start = None

    # ── Convenience static methods ──
    @staticmethod
    def ask(parent, title, message, yes_label="Yes", no_label="No",
            icon="question", yes_role="accept", no_role="reject") -> bool:
        dlg = DarkMessageBox(parent, title, message, icon=icon,
                             buttons=[(no_label, no_role), (yes_label, yes_role)],
                             default_btn=0)
        dlg.exec()
        return dlg.clicked_index() == 1

    @staticmethod
    def show_info(parent, title, message, icon="info"):
        dlg = DarkMessageBox(parent, title, message, icon=icon,
                             buttons=[("OK", "accept")])
        dlg.exec()

    @staticmethod
    def show_warning(parent, title, message):
        DarkMessageBox.show_info(parent, title, message, icon="warning")

    @staticmethod
    def show_error(parent, title, message):
        DarkMessageBox.show_info(parent, title, message, icon="error")


class SearchDialog(QDialog):
    """Frameless dark-themed dialog for searching the current cycle."""
    def __init__(self, parent, db: dict, cycle_key: str):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setModal(True)
        self.setFixedSize(700, 500)
        self._db = db
        self._cycle_key = cycle_key
        self._drag_start = None

        self.setStyleSheet(
            "SearchDialog { background-color: #1a1a2e; border: 1.5px solid #4a4a6a; border-radius: 14px; }"
            "QLineEdit { background-color: #252540; color: #ffffff; border: 2px solid #4a4a70; border-radius: 10px; padding: 12px 16px; font-size: 16px; font-weight: 600; }"
            "QLineEdit:focus { border-color: #9b9bff; background-color: #2e2e50; }"
            "QComboBox { background-color: #252540; color: #ffffff; border: 2px solid #4a4a70; border-radius: 10px; padding: 10px 16px; font-size: 14px; font-weight: 600; }"
            "QComboBox::drop-down { border: none; width: 30px; }"
            "QComboBox QAbstractItemView { background-color: #252540; color: #ffffff; border: 1px solid #4a4a70; selection-background-color: #4a4a8a; }"
            "QTableWidget { background-color: #222240; color: #ffffff; border: 2px solid #4a4a6a; border-radius: 12px; gridline-color: #444466; font-size: 15px; selection-background-color: #4a4a8a; }"
            "QHeaderView::section { background-color: #2a2a48; color: #ffffff; border: none; border-bottom: 2px solid #4a4a6a; padding: 8px; font-size: 12px; font-weight: 700; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setStyleSheet("background-color: #10101a; border-top-left-radius: 14px; border-top-right-radius: 14px; border-bottom: 1px solid #3a3a5a;")
        header.setFixedHeight(48)
        header.setCursor(Qt.CursorShape.SizeAllCursor)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 0, 10, 0)
        hl.setSpacing(10)

        icon_lbl = QLabel("🔍")
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        hl.addWidget(icon_lbl)

        title_lbl = QLabel(f"Search in Cycle: {cycle_key}")
        title_lbl.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 700; background: transparent;")
        hl.addWidget(title_lbl)
        hl.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background-color: #c0392b; color: #ffffff; border: none; font-size: 16px; border-radius: 6px; } QPushButton:hover { background-color: #e04a3d; }")
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        root.addWidget(header)

        # Body
        body = QWidget()
        body.setStyleSheet("background-color: #1a1a2e; border-bottom-left-radius: 14px; border-bottom-right-radius: 14px;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 20, 20, 20)
        bl.setSpacing(14)

        # Search Controls
        search_ctrl_ly = QHBoxLayout()
        self.search_type = QComboBox()
        self.search_type.addItem("Search By: Supplier ID", userData="id")
        self.search_type.addItem("Search By: Amount", userData="amount")
        self.search_type.currentIndexChanged.connect(self._trigger_search)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Start typing...")
        self.search_input.textChanged.connect(self._on_search)
        
        search_ctrl_ly.addWidget(self.search_type)
        search_ctrl_ly.addWidget(self.search_input, stretch=1)
        bl.addLayout(search_ctrl_ly)

        actions_ly = QHBoxLayout()
        actions_ly.setSpacing(10)
        
        self.btn_edit = QPushButton("✎ Edit Selected")
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setFixedHeight(34)
        self.btn_edit.setStyleSheet("QPushButton { background-color: #3b3b64; color: white; border: none; border-radius: 6px; padding: 0 16px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #5b5b84; } QPushButton:disabled { background-color: #2a2a3a; color: #555; }")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._edit_selected)
        
        self.btn_delete = QPushButton("🗑 Delete Selected")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setFixedHeight(34)
        self.btn_delete.setStyleSheet("QPushButton { background-color: #643b3b; color: white; border: none; border-radius: 6px; padding: 0 16px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #845b5b; } QPushButton:disabled { background-color: #3a2a2a; color: #555; }")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        
        actions_ly.addWidget(self.btn_edit)
        actions_ly.addWidget(self.btn_delete)
        actions_ly.addStretch()
        bl.addLayout(actions_ly)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(["Date", "Route", "Round", "Supplier ID", "Amount (Rs.)", "Note"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.setShowGrid(False)
        self.results_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        bl.addWidget(self.results_table)

        root.addWidget(body)

        self._on_search("")  # Populate initially
        self.search_input.setFocus()
        
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

    def closeEvent(self, event):
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QApplication, QComboBox
        if event.type() == QEvent.Type.MouseButtonPress:
            if QApplication.activeWindow() == self:
                if not self.geometry().contains(event.globalPosition().toPoint()):
                    widget = QApplication.widgetAt(event.globalPosition().toPoint())
                    w = widget
                    is_safe = False
                    while w:
                        if w == self or isinstance(w, QComboBox):
                            is_safe = True
                            break
                        w = w.parentWidget()
                    if not is_safe:
                        self.reject()
                        return True
        return super().eventFilter(obj, event)
        
    def _trigger_search(self):
        self._on_search(self.search_input.text())

    def _on_search(self, text):
        text = text.strip().lower()
        self.results_table.setRowCount(0)
        
        if not text:
            return
            
        s_type = self.search_type.currentData()
        matches = []
        for key, entries in self._db.items():
            if "|" not in key: continue
            parts = key.split("|")
            if len(parts) == 3:
                r, c, d = parts
                if c == self._cycle_key:
                    for i, entry in enumerate(_migrate_slot(entries)):
                        sid = str(entry.get("id", "")).lower()
                        amt = str(entry.get("amount", "")).lower()
                        
                        match = False
                        if s_type == "id" and text in sid:
                            match = True
                        elif s_type == "amount" and text in amt:
                            match = True
                            
                        if match:
                            matches.append((d, r, entry.get("round", 1), entry.get("id", ""), entry.get("amount", 0), entry.get("note", ""), key, i))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        
        for d, r, rnd, sid, amt, note, fkey, eidx in matches:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(d))
            self.results_table.setItem(row, 1, QTableWidgetItem(r))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"Round {rnd}"))
            sid_item = QTableWidgetItem(str(sid))
            sid_item.setData(Qt.ItemDataRole.UserRole, (fkey, eidx))
            self.results_table.setItem(row, 3, sid_item)
            
            amt_item = QTableWidgetItem(f"{amt:,}")
            amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.results_table.setItem(row, 4, amt_item)
            
            note_item = QTableWidgetItem(note if note else "")
            self.results_table.setItem(row, 5, note_item)
            self.results_table.setRowHeight(row, 36)

    def _on_table_selection_changed(self):
        has_sel = len(self.results_table.selectedItems()) > 0
        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)

    def _get_selected_data(self):
        ranges = self.results_table.selectedRanges()
        if not ranges: return None
        row = ranges[0].topRow()
        item = self.results_table.item(row, 3)
        if not item: return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _delete_selected(self):
        data = self._get_selected_data()
        if not data: return
        self._delete_item(data[0], data[1])

    def _edit_selected(self):
        data = self._get_selected_data()
        if not data: return
        self._edit_item(data[0], data[1])

    def _delete_item(self, full_key: str, entry_idx: int):
        if DarkMessageBox.ask(self, "🗑 Delete Entry", "Are you sure you want to delete this specific entry?", yes_label="Delete", yes_role="danger", icon="warning"):
            entries = _migrate_slot(self._db.get(full_key, []))
            if 0 <= entry_idx < len(entries):
                del entries[entry_idx]
                self._db[full_key] = entries
                self.parent()._save_db()
                if hasattr(self.parent(), '_recalculate_local_reductions'):
                    self.parent()._recalculate_local_reductions()
                self.parent()._load_book()
                self._trigger_search()
                
    def _edit_item(self, full_key: str, entry_idx: int):
        entries = _migrate_slot(self._db.get(full_key, []))
        if not (0 <= entry_idx < len(entries)):
            return
        entry = entries[entry_idx]
        
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dlg.setModal(True)
        dlg.setFixedWidth(400)
        dlg.setStyleSheet("QDialog { background-color: #141420; border: 1.5px solid #4a4a6a; border-radius: 14px; }")
        
        root = QVBoxLayout(dlg)
        root.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Edit Entry")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        root.addWidget(title)
        
        i_sid = QLineEdit(str(entry.get("id", "")))
        i_sid.setStyleSheet("QLineEdit { background-color: #252540; color: white; padding: 10px; border-radius: 6px; font-size: 15px; }")
        root.addWidget(QLabel("Supplier ID:"))
        root.addWidget(i_sid)
        
        i_amt = QLineEdit(str(entry.get("amount", "")))
        i_amt.setStyleSheet("QLineEdit { background-color: #252540; color: white; padding: 10px; border-radius: 6px; font-size: 15px; }")
        root.addWidget(QLabel("Amount:"))
        root.addWidget(i_amt)
        
        lbl_note = QLabel("Note (optional):")
        lbl_note.setStyleSheet("color: #aaaacc;")
        root.addWidget(lbl_note)
        i_note = QLineEdit(str(entry.get("note", "")))
        i_note.setStyleSheet("QLineEdit { background-color: #252540; color: #ffdd88; padding: 10px; border-radius: 6px; font-size: 15px; }")
        root.addWidget(i_note)
        
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_can = QPushButton("Cancel")
        btn_can.setStyleSheet("padding: 8px 16px; background-color: #3a3a5a; color: white; border-radius: 6px;")
        btn_can.clicked.connect(dlg.reject)
        btn_save = QPushButton("Save")
        btn_save.setStyleSheet("padding: 8px 16px; background-color: #5b4af7; color: white; border-radius: 6px;")
        btn_save.clicked.connect(dlg.accept)
        btn_box.addWidget(btn_can)
        btn_box.addWidget(btn_save)
        root.addLayout(btn_box)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_sid = i_sid.text().strip()
            amt_text = i_amt.text().strip().replace(",", "")
            try:
                new_amt = int(float(amt_text))
            except ValueError:
                return
            if new_sid and new_amt > 0:
                entries[entry_idx]["id"] = new_sid
                entries[entry_idx]["amount"] = new_amt
                entries[entry_idx]["note"] = i_note.text().strip()
                self._db[full_key] = entries
                self.parent()._save_db()
                if hasattr(self.parent(), '_recalculate_local_reductions'):
                    self.parent()._recalculate_local_reductions()
                self.parent()._load_book()
                self._trigger_search()
                
    # Dragging logic
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_start and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, e):
        self._drag_start = None


class CheckHighlightDelegate(QStyledItemDelegate):
    """Custom delegate that paints a highlight overlay on rows with checked checkboxes.
    This is needed because Qt stylesheets override QTableWidgetItem.setBackground()."""
    def paint(self, painter, option, index):
        # Let the stylesheet do its normal painting first
        super().paint(painter, option, index)
        # Then paint a highlight overlay on top for checked rows
        table = self.parent()
        if table:
            cb_item = table.item(index.row(), 0)
            if cb_item and cb_item.checkState() == Qt.CheckState.Checked:
                painter.save()
                painter.fillRect(option.rect, QColor(90, 70, 220, 85))
                painter.restore()


class CycleCalendarWidget(QCalendarWidget):
    """Custom calendar that highlights dates which have data in the selected cycle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlighted_dates: set[QDate] = set()

    def set_highlighted_dates(self, dates: set[QDate]):
        self._highlighted_dates = dates
        self.updateCells()

    def paintCell(self, painter: QPainter, rect, date: QDate):
        super().paintCell(painter, rect, date)
        if date in self._highlighted_dates:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Draw a blue dot at the bottom-center of the cell
            dot_radius = 3
            cx = rect.center().x()
            cy = rect.bottom() - dot_radius - 2
            painter.setBrush(QColor(0, 123, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx - dot_radius, cy - dot_radius, dot_radius * 2, dot_radius * 2)
            painter.restore()


def _make_book_table() -> QTableWidget:
    t = QTableWidget()
    t.setObjectName("inputTable")
    t.setColumnCount(6)
    t.setHorizontalHeaderLabels(["", "#", "Route", "Supplier ID", "Amount (Rs.)", "Note"])
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    t.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    t.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    t.setShowGrid(False)
    t.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    t.setItemDelegate(CheckHighlightDelegate(t))
    return t


def _migrate_monthly_keys(db: dict) -> dict:
    """One-time migration: convert route|YYYY-MM keys → route|YYYY-MM-01."""
    monthly_pat = re.compile(r'^(.+)\|(\d{4}-\d{2})$')
    to_rename: list[tuple[str, str]] = []
    for key in list(db.keys()):
        m = monthly_pat.match(key)
        if m:
            route, ym = m.groups()
            new_key = f"{route}|{ym}-01"
            to_rename.append((key, new_key))
    if not to_rename:
        return db
    for old_key, new_key in to_rename:
        existing = _migrate_slot(db.get(new_key, []))
        existing.extend(_migrate_slot(db[old_key]))
        db[new_key] = existing
        del db[old_key]
        
    to_rename_store = []
    for key in list(db.keys()):
        if key.startswith("ගබඩාව|"):
            new_key = key.replace("ගබඩාව|", "Store|", 1)
            to_rename_store.append((key, new_key))
    for old_k, new_k in to_rename_store:
        existing = _migrate_slot(db.get(new_k, []))
        existing.extend(_migrate_slot(db[old_k]))
        db[new_k] = existing
        del db[old_k]
        
    # Note: old migration functions are only used during legacy migration
    # save is handled by _migrate_legacy_to_cycles() now
    return db


def _migrate_to_cycle_keys(db: dict) -> dict:
    pat = re.compile(r'^([^|]+)\|(\d{4}-\d{2}-\d{2})$')
    to_rename = []
    for key in list(db.keys()):
        m = pat.match(key)
        if m:
            route, date_str = m.groups()
            cycle_str = date_str[:7]
            new_key = f"{route}|{cycle_str}|{date_str}"
            to_rename.append((key, new_key))
            continue
    if not to_rename:
        return db
    for old_key, new_key in to_rename:
        existing = _migrate_slot(db.get(new_key, []))
        existing.extend(_migrate_slot(db[old_key]))
        db[new_key] = existing
        del db[old_key]
    # Note: old migration functions are only used during legacy migration
    # save is handled by _migrate_legacy_to_cycles() now
    return db


# ── Web App Fetcher ──────────────────────────────────────────────────

class WebAppFetcher(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, cycle_key: str = None):
        super().__init__()
        self.cycle_key = cycle_key

    def run(self):
        result = {"success": False, "total_payable": 0.0, "suppliers": {}, "error": "", "cycle_key": self.cycle_key}
        try:
            cj = CookieJar()
            opener = urllib_req.build_opener(urllib_req.HTTPCookieProcessor(cj))
            
            # Try localhost first (app runs on same PC as server)
            base_url = "http://localhost:8000"
            try:
                opener.open(f"{base_url}/login", timeout=2)
            except Exception:
                try:
                    base_url = "http://127.0.0.1:8000"
                    opener.open(f"{base_url}/login", timeout=2)
                except Exception:
                    base_url = "http://192.168.1.5:8000"
                
            login_url = f"{base_url}/login"
            data = urllib_parse.urlencode({"username": "operator", "password": "operator123"}).encode('utf-8')
            req = urllib_req.Request(login_url, data=data)
            opener.open(req, timeout=5)
            
            api_url = f"{base_url}/api/operator/payments"
            if self.cycle_key:
                api_url += f"?period_str={self.cycle_key}"
            resp = opener.open(api_url, timeout=30)
            data_json = json.loads(resp.read().decode('utf-8'))
            
            result["total_payable"] = float(data_json.get("total_payable", 0.0))
            result["suppliers"] = {str(r["supplier_id"]).strip(): float(r["net_payable"]) for r in data_json.get("rows", [])}
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        self.finished.emit(result)


# ── Custom Title Bar ─────────────────────────────────────────────────

class TitleBar(QWidget):
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self._parent = parent
        self._drag_start = None
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(0)
        icon_lbl = QLabel("🍃")
        icon_lbl.setStyleSheet("font-size: 15px; padding-right: 6px;")
        layout.addWidget(icon_lbl)
        title_lbl = QLabel("Hindurangala Tea Collectors  —  Cash Flow")
        title_lbl.setObjectName("appTitleBar")
        layout.addWidget(title_lbl)
        layout.addStretch()
        for name, symbol, slot in [
            ("tbMinBtn", "─", parent.showMinimized),
            ("tbMaxBtn", "□", self._toggle_max),
            ("tbCloseBtn", "✕", parent.close),
        ]:
            btn = QPushButton(symbol)
            btn.setObjectName(name)
            btn.setFixedSize(46, 38)
            btn.setCursor(Qt.CursorShape.ArrowCursor)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

    def _toggle_max(self):
        if self._parent.isMaximized(): self._parent.showNormal()
        else: self._parent.showMaximized()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_start and e.buttons() == Qt.MouseButton.LeftButton:
            if self._parent.isMaximized():
                self._parent.showNormal()
                self._drag_start = e.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()
            self._parent.move(e.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, e): self._drag_start = None
    def mouseDoubleClickEvent(self, e): self._toggle_max()


# ── Main Window ──────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowTitle("HTC — Cash Flow")
        self.setWindowIcon(QIcon(resource_path("cashflow.ico")))
        self.setMinimumSize(960, 600)
        _migrate_legacy_to_cycles()  # One-time migration from old format
        self._meta = load_meta()
        self._current_cycle_key = None  # Set after sidebar is built
        self._db = {}  # Will be loaded after cycle controls exist

        root = QWidget()
        root.setObjectName("centralWidget")
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        self._title_bar = TitleBar(self)
        root_lay.addWidget(self._title_bar)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #444466;")
        root_lay.addWidget(sep)

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        body_lay.addWidget(self._build_sidebar())

        main_area = QWidget()
        main_lay = QVBoxLayout(main_area)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.cycle_banner = QLabel("")
        self.cycle_banner.setObjectName("readonlyBanner")
        self.cycle_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cycle_banner.setVisible(False)
        main_lay.addWidget(self.cycle_banner)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_book_page())
        self.stack.addWidget(self._build_breakdown_page())
        self.stack.addWidget(self._build_summary_page())
        main_lay.addWidget(self.stack, stretch=1)

        body_lay.addWidget(main_area, stretch=1)
        root_lay.addWidget(body, stretch=1)

        self._web_app_suppliers = {}
        self._web_app_total = 0.0
        self._web_app_local_reductions = 0.0
        self._web_app_fetched = False  # True once API data is successfully loaded

        # Load the active cycle's data before first page render
        self._load_cycle_data(self._cycle_key())
        self._update_calendar_highlights()
        self._switch_page(0)
        self._fetch_web_app_data()

        # 5-Minute Periodic Auto-Backup Timer
        self._backup_timer = QTimer(self)
        self._backup_timer.timeout.connect(self._run_periodic_backup)
        self._backup_timer.start(5 * 60 * 1000)  # Every 5 minutes

    def _run_periodic_backup(self):
        """5-minute background backup: forces disk sync and saves a timestamped snapshot."""
        try:
            if hasattr(self, '_current_cycle_key') and self._current_cycle_key and self._db:
                self._save_db()
                create_timed_backup(self._current_cycle_key, self._db)
        except Exception:
            pass

    def closeEvent(self, event):
        """Ensure full save and snapshot before closing."""
        try:
            self._save_db()
            if hasattr(self, '_current_cycle_key') and self._current_cycle_key and self._db:
                create_timed_backup(self._current_cycle_key, self._db)
        except Exception:
            pass
        super().closeEvent(event)

    def _fetch_web_app_data(self):
        if hasattr(self, '_fetcher') and self._fetcher.isRunning():
            return
        if hasattr(self, '_to_pay_total'):
            self._to_pay_total.setText("Fetching...")
            self._to_pay_total.setStyleSheet("font-size:24px; color:#aaaaaa;")
        
        ck = self._cycle_key() if hasattr(self, '_cycle_month') else None
        self._fetcher = WebAppFetcher(ck)
        self._fetcher.finished.connect(self._on_fetch_finished)
        self._fetcher.start()

    def _on_fetch_finished(self, result):
        if not hasattr(self, '_to_pay_total'):
            return
            
        # If the user changed the cycle while this fetch was happening
        current_ck = self._cycle_key() if hasattr(self, '_cycle_month') else None
        if result.get("cycle_key") != current_ck:
            # Re-trigger fetch for the new correct cycle
            self._fetch_web_app_data()
            return
            
        if result["success"]:
            self._web_app_suppliers = result["suppliers"]
            self._web_app_total = result["total_payable"]
            self._web_app_fetched = True
            self._recalculate_local_reductions()
        else:
            err = result.get("error", "")
            self._to_pay_total.setText(f"Offline ({err})")
            self._to_pay_total.setStyleSheet("font-size:16px; color:#ffaaaa;")
            print("Fetch Error:", err)

    def _recalculate_local_reductions(self):
        ck = self._cycle_key()
        total_reduction = 0.0
        for key, entries in self._db.items():
            if "|" not in key:
                continue
            parts = key.split("|")
            if len(parts) == 3:
                r, c, kd = parts
                if c == ck:
                    slot = _migrate_slot(entries)
                    for e in slot:
                        total_reduction += e["amount"]
        self._web_app_local_reductions = total_reduction
        self._update_web_app_display()

    def _update_web_app_display(self):
        if not hasattr(self, '_to_pay_total'):
            return
        if hasattr(self, '_is_future_cycle') and self._is_future_cycle():
            self._to_pay_btn.setVisible(False)
            self._to_pay_total.setVisible(False)
            return

        self._to_pay_btn.setVisible(True)
        self._to_pay_total.setVisible(True)
        current_display = self._web_app_total - self._web_app_local_reductions
        if current_display < 0:
            current_display = 0.0
        self._to_pay_total.setText(f"Rs. {current_display:,.2f}")
        self._to_pay_total.setStyleSheet("font-size:24px; color:#ffdd88;")

    # ── Sidebar ──────────────────────────────────────────────────────

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(6)

        logo = QLabel("🍃 HTC Cash Flow")
        logo.setObjectName("sidebarTitle")
        lay.addWidget(logo)
        s1 = QFrame(); s1.setFrameShape(QFrame.Shape.HLine); s1.setFixedHeight(1)
        s1.setStyleSheet("background-color:#444466;")
        lay.addWidget(s1)
        lay.addSpacing(4)

        self._nav_buttons = []
        for i, (icon, label) in enumerate([
            ("📗", "Payment Book"), ("💵", "Cash Breakdown"), ("📊", "Monthly Summary")
        ]):
            btn = QPushButton(f" {icon}  {label}")
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._switch_page(idx))
            lay.addWidget(btn)
            self._nav_buttons.append(btn)

        lay.addSpacing(6)
        s2 = QFrame(); s2.setFrameShape(QFrame.Shape.HLine); s2.setFixedHeight(1)
        s2.setStyleSheet("background-color:#444466;")
        lay.addWidget(s2)
        lay.addSpacing(4)

        dl = QLabel("📅 Payment Cycle")
        dl.setObjectName("sectionLabel")
        lay.addWidget(dl)

        # Month selection
        mr = QHBoxLayout(); mr.setSpacing(4)
        mp = QPushButton("‹"); mp.setObjectName("dateNavBtn"); mp.setFixedWidth(36)
        mp.setCursor(Qt.CursorShape.PointingHandCursor)
        mp.clicked.connect(self._go_prev_cycle)
        mr.addWidget(mp)
        
        self._cycle_month_label = QLabel()
        self._cycle_month_label.setObjectName("dateNavLabel")
        self._cycle_month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cycle_month_label.setStyleSheet("font-size:16px; font-weight:700; color:#ffffff; text-transform:uppercase;")
        mr.addWidget(self._cycle_month_label, stretch=1)
        
        mn = QPushButton("›"); mn.setObjectName("dateNavBtn"); mn.setFixedWidth(36)
        mn.setCursor(Qt.CursorShape.PointingHandCursor)
        mn.clicked.connect(self._go_next_cycle)
        mr.addWidget(mn)
        lay.addLayout(mr)

        # Hidden logic combo to keep calendar states synced exactly as before
        self._cycle_month = QComboBox()
        self._cycle_month.setVisible(False)
        for m in range(1, 13):
            self._cycle_month.addItem(month_name[m], userData=m)
        _curr_y, _curr_m = self._get_active_cycle()
        
        self._cycle_month_label.setText(month_name[_curr_m].upper())
        self._cycle_month.setCurrentIndex(_curr_m - 1)
        self._cycle_month.currentIndexChanged.connect(self._on_cycle_changed)
        lay.addWidget(self._cycle_month)

        # Year: ‹ 2026 ›
        self._year_value = _curr_y
        yr = QHBoxLayout(); yr.setSpacing(4)
        yp = QPushButton("‹"); yp.setObjectName("dateNavBtn"); yp.setFixedWidth(36)
        yp.setCursor(Qt.CursorShape.PointingHandCursor)
        yp.clicked.connect(self._go_prev_year)
        yr.addWidget(yp)
        self._year_label = QLabel(str(self._year_value))
        self._year_label.setObjectName("dateNavLabel")
        self._year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._year_label.setStyleSheet("font-size:16px; font-weight:700; color:#ffffff;")
        yr.addWidget(self._year_label, stretch=1)
        yn = QPushButton("›"); yn.setObjectName("dateNavBtn"); yn.setFixedWidth(36)
        yn.setCursor(Qt.CursorShape.PointingHandCursor)
        yn.clicked.connect(self._go_next_year)
        yr.addWidget(yn)
        lay.addLayout(yr)

        tb = QPushButton("CURRENT CYCLE"); tb.setObjectName("todayBtn")
        tb.setCursor(Qt.CursorShape.PointingHandCursor); tb.clicked.connect(self._go_current_cycle)
        lay.addWidget(tb)

        lay.addSpacing(6)

        cb = QPushButton("🔒 CLOSE BOOK"); cb.setObjectName("todayBtn")
        cb.setStyleSheet("background-color: rgba(220,100,100,100); border-color: #ff6666;")
        cb.setCursor(Qt.CursorShape.PointingHandCursor); cb.clicked.connect(self._close_book)
        lay.addWidget(cb)

        lay.addSpacing(6)
        s3 = QFrame(); s3.setFrameShape(QFrame.Shape.HLine); s3.setFixedHeight(1)
        s3.setStyleSheet("background-color:#444466;")
        lay.addWidget(s3)
        lay.addSpacing(4)

        ddl = QLabel("📆 Date")
        ddl.setObjectName("sectionLabel")
        lay.addWidget(ddl)

        ddr = QHBoxLayout(); ddr.setSpacing(4)
        dpb = QPushButton("‹"); dpb.setObjectName("dateNavBtn"); dpb.setFixedWidth(36)
        dpb.setCursor(Qt.CursorShape.PointingHandCursor); dpb.clicked.connect(self._go_prev_day)
        ddr.addWidget(dpb)

        self.date_edit = QDateEdit()
        self.date_edit.wheelEvent = lambda event: event.ignore()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.dateChanged.connect(self._on_date_changed)
        self.date_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._cycle_calendar = CycleCalendarWidget()
        self.date_edit.setCalendarWidget(self._cycle_calendar)
        ddr.addWidget(self.date_edit, stretch=1)

        dnb = QPushButton("›"); dnb.setObjectName("dateNavBtn"); dnb.setFixedWidth(36)
        dnb.setCursor(Qt.CursorShape.PointingHandCursor); dnb.clicked.connect(self._go_next_day)
        ddr.addWidget(dnb)
        
        lay.addLayout(ddr)

        dtb = QPushButton("TODAY"); dtb.setObjectName("todayBtn")
        dtb.setCursor(Qt.CursorShape.PointingHandCursor); dtb.clicked.connect(self._go_today)
        lay.addWidget(dtb)

        self._sync_date_to_cycle()

        lay.addStretch()
        ft = QLabel("© 2026 HTC")
        ft.setObjectName("subtitleLabel"); ft.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ft)
        return sidebar

    # ── Page 1: Payment Book ─────────────────────────────────────────

    def _build_book_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 20, 28, 14)
        lay.setSpacing(12)

        # Header row
        hdr = QHBoxLayout()
        
        self._to_pay_btn = QPushButton("TO PAY")
        self._to_pay_btn.setObjectName("grandTotalCaption")
        self._to_pay_btn.setStyleSheet("border:none; text-align:left; color:#aaaaaa; padding-top:4px;")
        self._to_pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._to_pay_btn.setToolTip("Click to refresh from Web App")
        self._to_pay_btn.clicked.connect(self._fetch_web_app_data)
        hdr.addWidget(self._to_pay_btn)
        self._to_pay_total = QLabel("Rs. 0")
        self._to_pay_total.setObjectName("grandTotalValue")
        self._to_pay_total.setStyleSheet("font-size:24px; color:#ffdd88;")
        hdr.addWidget(self._to_pay_total)
        
        hdr.addStretch()
        dc = QLabel("TODAY"); dc.setObjectName("grandTotalCaption")
        hdr.addWidget(dc)
        self._daily_total = QLabel("Rs. 0")
        self._daily_total.setObjectName("grandTotalValue")
        self._daily_total.setStyleSheet("font-size:24px;")
        hdr.addWidget(self._daily_total)
        hdr.addSpacing(20)
        mc = QLabel("MONTH"); mc.setObjectName("grandTotalCaption")
        hdr.addWidget(mc)
        self._monthly_total = QLabel("Rs. 0")
        self._monthly_total.setObjectName("grandTotalValue")
        self._monthly_total.setStyleSheet("font-size:24px; color: #aaffaa;")
        hdr.addWidget(self._monthly_total)
        lay.addLayout(hdr)

        # Input row
        inp = QHBoxLayout(); inp.setSpacing(8)
        self._route_combo = QComboBox()
        self._route_combo.wheelEvent = lambda event: event.ignore()
        for route in ALL_ROUTES_ORDERED:
            icon = "🏪" if route == STORE_ROUTE else "🚚"
            self._route_combo.addItem(f"{icon} {route}", userData=route)
        sf = QFont("Noto Sans Sinhala", 14)
        sf.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._route_combo.setFont(sf); self._route_combo.view().setFont(sf)
        inp.addWidget(self._route_combo)
        
        self._round_combo = QComboBox()
        self._round_combo.wheelEvent = lambda event: event.ignore()
        self._round_combo.addItem("Round 1", userData=1)
        self._round_combo.addItem("Round 2", userData=2)
        self._round_combo.addItem("Round 3", userData=3)
        self._round_combo.addItem("Round 4", userData=4)
        self._round_combo.addItem("Round 5", userData=5)
        self._round_combo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        inp.addWidget(self._round_combo)
        
        self._b_id = QLineEdit(); self._b_id.setObjectName("amountInput")
        self._b_id.setPlaceholderText("Supplier ID…")
        self._b_id.returnPressed.connect(self._on_supplier_id_entered)
        inp.addWidget(self._b_id, stretch=1)
        self._b_amt = QLineEdit(); self._b_amt.setObjectName("amountInput")
        self._b_amt.setPlaceholderText("Amount…")
        self._b_amt.returnPressed.connect(lambda: self._b_note.setFocus())
        inp.addWidget(self._b_amt, stretch=1)
        self._b_note = QLineEdit(); self._b_note.setObjectName("amountInput")
        self._b_note.setPlaceholderText("Note (optional) & Enter…")
        self._b_note.setStyleSheet("QLineEdit#amountInput { font-size: 14px; font-family: 'Segoe UI'; }")
        self._b_note.returnPressed.connect(self._add_entry)
        inp.addWidget(self._b_note, stretch=1)
        lay.addLayout(inp)

        # Action Buttons
        action_lay = QHBoxLayout()
        
        self._btn_search_cycle = QPushButton("  🔍 Search Cycle  ")
        self._btn_search_cycle.setStyleSheet("QPushButton { background-color: #2a3a5a; color: #ffffff; border: 1px solid #4a5a7a; border-radius: 6px; padding: 8px 16px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #3b4b6b; }")
        self._btn_search_cycle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_search_cycle.clicked.connect(self._on_search_clicked)
        action_lay.addWidget(self._btn_search_cycle)
        
        action_lay.addStretch()
        
        self._btn_edit_selected = QPushButton("  ✎ Edit Selected  ")
        self._btn_edit_selected.setStyleSheet("QPushButton { background-color: #3b3b64; color: #ffffff; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #4b4b84; }")
        self._btn_edit_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_edit_selected.clicked.connect(self._on_edit_selected)
        
        self._btn_move_selected = QPushButton("  ➜ Move Selected  ")
        self._btn_move_selected.setStyleSheet("QPushButton { background-color: #3b5b3b; color: #ccffcc; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #4b7b4b; }")
        self._btn_move_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_move_selected.clicked.connect(self._on_move_selected)
        
        self._btn_delete_selected = QPushButton("  🗑 Delete Selected  ")
        self._btn_delete_selected.setStyleSheet("QPushButton { background-color: #643b3b; color: #ffcccc; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #844b4b; }")
        self._btn_delete_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_delete_selected.clicked.connect(self._on_delete_selected)
        
        action_lay.addWidget(self._btn_edit_selected)
        action_lay.addWidget(self._btn_move_selected)
        action_lay.addWidget(self._btn_delete_selected)
        lay.addLayout(action_lay)

        # Table
        self._book_table = _make_book_table()
        self._book_table.setMinimumHeight(200)
        self._book_table.cellClicked.connect(self._on_table_cell_clicked)
        self._book_table.itemChanged.connect(self._on_table_item_changed)
        lay.addWidget(self._book_table, stretch=1)
        
        shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._book_table)
        shortcut_del.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut_del.activated.connect(self._on_table_delete_pressed)
        
        shortcut_bs = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self._book_table)
        shortcut_bs.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut_bs.activated.connect(self._on_table_delete_pressed)

        return page

    # ── Page 2: Cash Breakdown ────────────────────────────────────────

    def _build_breakdown_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 20, 28, 14)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("💵  Cash Breakdown")
        title.setObjectName("pageTitle")
        hdr.addWidget(title)
        
        hdr.addSpacing(20)
        self._bd_route_filter = QComboBox()
        self._bd_route_filter.addItem("All Routes", userData="ALL")
        for r in ALL_ROUTES_ORDERED:
            self._bd_route_filter.addItem(r, userData=r)
        self._bd_route_filter.setFont(QFont("Segoe UI", 12))
        self._bd_route_filter.currentIndexChanged.connect(self._refresh_breakdown)
        hdr.addWidget(self._bd_route_filter)
        
        self._bd_round_filter = QComboBox()
        self._bd_round_filter.addItem("All Rounds", userData="ALL")
        for i in range(1, 6):
            self._bd_round_filter.addItem(f"Round {i}", userData=i)
        self._bd_round_filter.setFont(QFont("Segoe UI", 12))
        self._bd_round_filter.currentIndexChanged.connect(self._refresh_breakdown)
        hdr.addWidget(self._bd_round_filter)
        
        hdr.addStretch()
        dc = QLabel("TOTAL"); dc.setObjectName("grandTotalCaption")
        hdr.addWidget(dc)
        self._bd_day_total = QLabel("Rs. 0")
        self._bd_day_total.setObjectName("grandTotalValue")
        self._bd_day_total.setStyleSheet("font-size:26px;")
        hdr.addWidget(self._bd_day_total)
        lay.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}"
                             "QWidget#breakdownInner{background:transparent;}")
        self._bd_container = QWidget()
        self._bd_container.setObjectName("breakdownInner")
        self._bd_layout = QVBoxLayout(self._bd_container)
        self._bd_layout.setContentsMargins(0, 0, 0, 0)
        self._bd_layout.setSpacing(16)
        scroll.setWidget(self._bd_container)
        lay.addWidget(scroll, stretch=1)

        return page

    # ── Page 3: Summary ──────────────────────────────────────────────

    def _build_summary_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(40, 30, 40, 30)
        lay.setSpacing(20)

        title = QLabel("📊  Monthly Summary")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        lay.addSpacing(10)

        # Grand total card
        gc = QFrame(); gc.setObjectName("summaryCard")
        gl = QVBoxLayout(gc); gl.setContentsMargins(30, 24, 30, 24); gl.setSpacing(4)
        gcap = QLabel("💰  MONTHLY GRAND TOTAL")
        gcap.setObjectName("summaryGrandCaption")
        gcap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gl.addWidget(gcap)
        self._sum_grand = QLabel("Rs. 0")
        self._sum_grand.setObjectName("summaryGrandTotal")
        self._sum_grand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gl.addWidget(self._sum_grand)
        lay.addWidget(gc)

        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(30); sh.setOffset(0, 4); sh.setColor(QColor(0, 0, 0, 80))
        gc.setGraphicsEffect(sh)

        lay.addSpacing(10)

        # Per-route cards
        cards_row = QHBoxLayout(); cards_row.setSpacing(14)
        self._sum_values = {}
        self._sum_counts = {}
        route_order = [STORE_ROUTE] + LORRY_ROUTES
        icons = {STORE_ROUTE: "🏪"}
        for route in route_order:
            card = QFrame(); card.setObjectName("summaryCard")
            cl = QVBoxLayout(card); cl.setContentsMargins(18, 14, 18, 14); cl.setSpacing(4)
            ic = icons.get(route, "🚚")
            nm = QLabel(f"{ic}  {route}")
            nm.setObjectName("summaryRouteName")
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm.setFont(QFont("Noto Sans Sinhala", 12))
            cl.addWidget(nm)
            vl = QLabel("Rs. 0")
            vl.setObjectName("summaryRouteValue")
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(vl)
            self._sum_values[route] = vl
            ct = QLabel("0 entries")
            ct.setObjectName("summaryRouteCount")
            ct.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(ct)
            self._sum_counts[route] = ct
            cs = QGraphicsDropShadowEffect()
            cs.setBlurRadius(20); cs.setOffset(0, 3); cs.setColor(QColor(0, 0, 0, 60))
            card.setGraphicsEffect(cs)
            cards_row.addWidget(card)
        lay.addLayout(cards_row)
        lay.addStretch()
        return page

    # ── Navigation ───────────────────────────────────────────────────

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        self._refresh_current_page()

    def _refresh_current_page(self):
        idx = self.stack.currentIndex()
        if idx == 0:   self._load_book()
        elif idx == 1: self._refresh_breakdown()
        elif idx == 2: self._refresh_summary()
        self._update_cycle_banner()

    # ── Cycle ─────────────────────────────────────────────────────────

    def _get_active_cycle(self) -> tuple[int, int]:
        """Returns (year, month)."""
        if "active_cycle" in self._meta:
            try:
                y, m = map(int, self._meta["active_cycle"].split("-"))
                return y, m
            except Exception:
                pass
        
        # Fallback: detect latest cycle from existing data files
        if os.path.isdir(CYCLES_DIR):
            cycle_files = sorted(
                [f[:-5] for f in os.listdir(CYCLES_DIR) if f.endswith(".json")],
                reverse=True
            )
            if cycle_files:
                try:
                    y, m = map(int, cycle_files[0].split("-"))
                    # Auto-save so this doesn't happen again
                    self._meta["active_cycle"] = f"{y:04d}-{m:02d}"
                    save_meta(self._meta)
                    return y, m
                except Exception:
                    pass

        # Last resort: previous month
        today = date.today()
        m = today.month - 1
        y = today.year
        if m < 1:
            m = 12
            y -= 1
        return y, m

    def _set_active_cycle(self, y: int, m: int):
        self._meta["active_cycle"] = f"{y:04d}-{m:02d}"
        save_meta(self._meta)

    def _save_db(self):
        """Save current cycle data to its file."""
        if self._current_cycle_key:
            save_cycle(self._db, self._current_cycle_key)

    def _load_cycle_data(self, cycle_key: str):
        """Save current cycle and load a new one."""
        if self._current_cycle_key and self._current_cycle_key != cycle_key:
            save_cycle(self._db, self._current_cycle_key)
        self._current_cycle_key = cycle_key
        self._db = load_cycle(cycle_key)

    def _close_book(self):
        act_y, act_m = self._get_active_cycle()
        cycle_label = f"{month_name[act_m]} {act_y}"
        
        next_m = act_m + 1
        next_y = act_y
        if next_m > 12:
            next_m = 1
            next_y += 1
        next_label = f"{month_name[next_m]} {next_y}"
        
        if DarkMessageBox.ask(self, "🔒 Close Book",
                f"Are you sure you want to close the book for <b>{cycle_label}</b> "
                f"and start <b>{next_label}</b>?"):
            self._set_active_cycle(next_y, next_m)
            self._go_current_cycle()
            DarkMessageBox.show_info(self, "Book Closed",
                f"Successfully started the <b>{next_label}</b> cycle.", icon="success")

    def _cycle_key(self) -> str:
        """Return 'YYYY-MM' from the sidebar combos."""
        m = self._cycle_month.currentData()
        y = self._year_value
        return f"{y:04d}-{m:02d}"

    def _date_str(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    def _is_current_cycle(self) -> bool:
        act_y, act_m = self._get_active_cycle()
        return (self._cycle_month.currentData() == act_m
                and self._year_value == act_y)

    def _is_future_cycle(self) -> bool:
        act_y, act_m = self._get_active_cycle()
        view_y = self._year_value
        view_m = self._cycle_month.currentData()
        return (view_y > act_y) or (view_y == act_y and view_m > act_m)

    def _sync_date_to_cycle(self):
        """Allow any date regardless of selected cycle month, except future dates."""
        self.date_edit.blockSignals(True)
        self.date_edit.clearMinimumDate()
        self.date_edit.setMaximumDate(QDate.currentDate())
        self.date_edit.blockSignals(False)

    def _go_prev_year(self):
        self._year_value -= 1
        self._year_label.setText(str(self._year_value))
        self._on_cycle_changed()

    def _go_next_year(self):
        self._year_value += 1
        self._year_label.setText(str(self._year_value))
        self._on_cycle_changed()

    def _go_prev_cycle(self):
        m = self._cycle_month.currentData()
        m -= 1
        if m < 1:
            m = 12; self._year_value -= 1
            self._year_label.setText(str(self._year_value))
        mi = self._cycle_month.findData(m)
        if mi >= 0:
            self._cycle_month.blockSignals(True)
            self._cycle_month.setCurrentIndex(mi)
            self._cycle_month.blockSignals(False)
            self._on_cycle_changed()

    def _go_next_cycle(self):
        m = self._cycle_month.currentData()
        m += 1
        if m > 12:
            m = 1; self._year_value += 1
            self._year_label.setText(str(self._year_value))
        mi = self._cycle_month.findData(m)
        if mi >= 0:
            self._cycle_month.blockSignals(True)
            self._cycle_month.setCurrentIndex(mi)
            self._cycle_month.blockSignals(False)
            self._on_cycle_changed()

    def _go_current_cycle(self):
        act_y, act_m = self._get_active_cycle()
        self._year_value = act_y
        self._year_label.setText(str(self._year_value))
        self.date_edit.setDate(QDate.currentDate())
        mi = self._cycle_month.findData(act_m)
        if mi >= 0:
            self._cycle_month.blockSignals(True)
            self._cycle_month.setCurrentIndex(mi)
            self._cycle_month.blockSignals(False)
            self._on_cycle_changed()

    def _on_cycle_changed(self):
        if hasattr(self, '_cycle_month_label'):
            m = self._cycle_month.currentData()
            self._cycle_month_label.setText(month_name[m].upper())
        self._load_cycle_data(self._cycle_key())
        self._sync_date_to_cycle()
        self._update_calendar_highlights()
        if hasattr(self, '_recalculate_local_reductions'):
            self._recalculate_local_reductions()
        if hasattr(self, '_fetch_web_app_data'):
            self._fetch_web_app_data()
        self._refresh_current_page()

    def _go_prev_day(self):
        d = self.date_edit.date().addDays(-1)
        if d >= self.date_edit.minimumDate():
            self.date_edit.setDate(d)

    def _go_next_day(self):
        d = self.date_edit.date().addDays(1)
        if d <= self.date_edit.maximumDate():
            self.date_edit.setDate(d)

    def _go_today(self):
        self._go_current_cycle()

    def _on_date_changed(self):
        self._refresh_current_page()

    def _update_calendar_highlights(self):
        """Scan the database for all dates that have data in the selected cycle
        and highlight them in the calendar popup."""
        if not hasattr(self, '_cycle_calendar'):
            return
        ck = self._cycle_key()
        highlighted = set()
        for key, entries in self._db.items():
            if "|" not in key or key.startswith("_"):
                continue
            parts = key.split("|")
            if len(parts) == 3:
                route, cycle, date_str = parts
                if cycle == ck:
                    migrated = _migrate_slot(entries)
                    if migrated:  # only highlight if there are actual entries
                        try:
                            qd = QDate.fromString(date_str, "yyyy-MM-dd")
                            if qd.isValid():
                                highlighted.add(qd)
                        except Exception:
                            pass
        self._cycle_calendar.set_highlighted_dates(highlighted)

    def _update_cycle_banner(self):
        if self._is_current_cycle():
            self.cycle_banner.setVisible(False)
            is_future = False
        else:
            is_future = self._is_future_cycle()
            ck = self._cycle_key()
            try:
                y, m = ck.split("-")
                label = f"{month_name[int(m)].upper()} {y}"
            except Exception:
                label = ck
            if is_future:
                self.cycle_banner.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px; background-color: rgba(220,50,50,0.85); padding: 10px;")
                self.cycle_banner.setText(f"⛔ FUTURE CYCLE: You must 'Close Book' to start {label}. Inputs locked.")
            else:
                self.cycle_banner.setStyleSheet("color: #ffff88; font-size: 13px; font-weight: 600; background-color: rgba(200,150,30,0.25); border: 1px solid rgba(220,170,40,0.55); padding: 8px 14px;")
                self.cycle_banner.setText(f"⚠  EDITING PAST CYCLE: {label}")
            self.cycle_banner.setVisible(True)
            
        # Lock inputs if future
        lock = not is_future
        if hasattr(self, '_b_id'):
            self._b_id.setEnabled(lock)
            self._b_amt.setEnabled(lock)
            self._b_note.setEnabled(lock)
            self._route_combo.setEnabled(lock)
            self._round_combo.setEnabled(lock)
            if is_future:
                self._b_id.setPlaceholderText("Locked (Close Book first)")
                self._b_amt.setPlaceholderText("")
                self._b_note.setPlaceholderText("")
            else:
                self._b_id.setPlaceholderText("Supplier ID…")
                self._b_amt.setPlaceholderText("Amount…")
                self._b_note.setPlaceholderText("Note (optional) & Enter…")

    # ── Duplicate check ──────────────────────────────────────────────

    def _check_dup(self, sid: str, cycle: str) -> tuple[bool, str, int, str]:
        """Scan all dates in the cycle for duplicate supplier ID.
        Returns (found, route, amount, note)."""
        if not sid or not cycle:
            return (False, "", 0, "")
        for key, entries in self._db.items():
            if "|" not in key:
                continue
            parts = key.split("|")
            if len(parts) == 3:
                r, c, kd = parts
                if c != cycle:
                    continue
                for entry in _migrate_slot(entries):
                    if entry["id"] == sid:
                        return (True, r, entry["amount"], entry.get("note", ""))
        return (False, "", 0, "")

    def _handle_dup_check(self, sid: str, focus_widget) -> bool:
        """Returns True if entry should proceed, False to abort."""
        if not sid:
            return True
        cycle = self._cycle_key()
        found, dup_route, dup_amt, dup_note = self._check_dup(sid, cycle)
        if not found:
            return True
        # Build a human-friendly month label
        try:
            y, m = cycle.split("-")
            cycle_label = f"{month_abbr[int(m)]} {y}"
        except Exception:
            cycle_label = cycle
        note_html = ""
        if dup_note:
            note_html = (f"<br><br>📝 Note: <i style='color:#ffdd88;'>{dup_note}</i>")
        dlg = DarkMessageBox(self, "⚠️ Duplicate Supplier ID",
            f"Supplier <b>{sid}</b> was already paid "
            f"<b>Rs. {dup_amt:,}</b> in the "
            f"<b>{cycle_label}</b> cycle "
            f"via <b>{dup_route}</b>.{note_html}",
            icon="warning",
            buttons=[("Cancel", "reject"), ("Add Anyway", "action")],
            default_btn=0)
        dlg.exec()
        if dlg.clicked_index() != 1:
            focus_widget.setFocus()
            focus_widget.selectAll()
            return False
        return True

    def _parse_amount(self, text: str) -> int | None:
        cleaned = text.strip().replace(",", "").replace(" ", "")
        if not cleaned: return None
        try:
            v = int(float(cleaned))
            return v if v > 0 else None
        except ValueError:
            return None

    # ── Book logic ─────────────────────────────────────────────────────

    def _on_search_clicked(self):
        ck = self._cycle_key()
        dlg = SearchDialog(self, self._db, ck)
        dlg.exec()

    def _current_route(self) -> str:
        return self._route_combo.currentData()

    def _entry_key(self) -> str:
        return data_key(self._current_route(), self._cycle_key(), self._date_str())

    def _load_book(self):
        """Load ALL routes for the current date into the combined table."""
        self._book_table.setRowCount(0)
        idx = 0
        daily = 0
        for route in ALL_ROUTES_ORDERED:
            key = data_key(route, self._cycle_key(), self._date_str())
            entries = _migrate_slot(self._db.get(key, []))
            for i, e in enumerate(entries):
                self._append_book_row(self._book_table, idx, route, e.get("round", 1), e["id"], e["amount"], e.get("note", ""), i)
                idx += 1
                daily += e["amount"]
        self._book_table.scrollToBottom()
        # Daily total
        self._daily_total.setText(f"Rs. {daily:,}")
        # Monthly total
        ck = self._cycle_key()
        monthly = 0
        for key, entries in self._db.items():
            if "|" not in key:
                continue
            parts = key.split("|")
            if len(parts) == 3:
                r, c, kd = parts
                if c == ck:
                    monthly += sum(e["amount"] for e in _migrate_slot(entries))
        self._monthly_total.setText(f"Rs. {monthly:,}")

    def _get_selected_rows_data(self) -> list[tuple[str, int]]:
        selected = []
        for i in range(self._book_table.rowCount()):
            item = self._book_table.item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    selected.append(data)
        return selected

    def _on_edit_selected(self):
        selected = self._get_selected_rows_data()
        if len(selected) != 1:
            DarkMessageBox.show_warning(self, "Edit Entry", "Please select exactly one entry to edit.")
            return
        route, entry_idx = selected[0]
        self._edit_entry(route, entry_idx)

    def _on_delete_selected(self):
        if hasattr(self, '_is_future_cycle') and self._is_future_cycle():
            return
        selected = self._get_selected_rows_data()
        
        # Fallback to logically highlighted row if no checkbox is checked
        if not selected:
            row = self._book_table.currentRow()
            if row >= 0:
                item = self._book_table.item(row, 0)
                if item:
                    data = item.data(Qt.ItemDataRole.UserRole)
                    if data:
                        selected.append(data)
                        
        if not selected:
            DarkMessageBox.show_warning(self, "Delete Entries", "Please select at least one entry to delete.")
            return
            
        msg = "Are you sure you want to delete this entry?" if len(selected) == 1 else f"Are you sure you want to delete <b>{len(selected)}</b> selected entries?"
        if DarkMessageBox.ask(self, "🗑 Delete Entries", msg, yes_label="Delete",
                             yes_role="danger", icon="warning"):
            deleted_anything = False
            for route in set(r for r, _ in selected):
                key = data_key(route, self._cycle_key(), self._date_str())
                entries = _migrate_slot(self._db.get(key, []))
                
                indices_to_delete = sorted([ei for r, ei in selected if r == route], reverse=True)
                for ei in indices_to_delete:
                    if 0 <= ei < len(entries):
                        del entries[ei]
                        deleted_anything = True
                        
                self._db[key] = entries
                
            if deleted_anything:
                self._save_db()
                if hasattr(self, '_recalculate_local_reductions'):
                    self._recalculate_local_reductions()
                self._load_book()

    def _on_move_selected(self):
        if hasattr(self, '_is_future_cycle') and self._is_future_cycle():
            return
        selected = self._get_selected_rows_data()
        if not selected:
            DarkMessageBox.show_warning(self, "Move Entries", "Please select at least one entry to move.")
            return

        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dlg.setModal(True)
        dlg.setFixedWidth(460)
        dlg._drag_start = None
        def _mp(e):
            if e.button() == Qt.MouseButton.LeftButton:
                dlg._drag_start = e.globalPosition().toPoint() - dlg.frameGeometry().topLeft()
        def _mm(e):
            if dlg._drag_start and e.buttons() == Qt.MouseButton.LeftButton:
                dlg.move(e.globalPosition().toPoint() - dlg._drag_start)
        def _mr(e): dlg._drag_start = None
        dlg.mousePressEvent = _mp
        dlg.mouseMoveEvent = _mm
        dlg.mouseReleaseEvent = _mr
        dlg.setStyleSheet(
            "QDialog { background-color: #141420; border: 1.5px solid #4a4a6a; border-radius: 14px; }"
        )
        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr_w = QWidget()
        hdr_w.setStyleSheet(
            "background-color: #10101a; border-top-left-radius: 14px;"
            "border-top-right-radius: 14px; border-bottom: 1px solid #3a3a5a;"
        )
        hdr_w.setFixedHeight(48)
        hdr_w.setCursor(Qt.CursorShape.SizeAllCursor)
        hdr_lay = QHBoxLayout(hdr_w)
        hdr_lay.setContentsMargins(18, 0, 10, 0)
        hdr_lay.setSpacing(10)
        hdr_icon = QLabel("➜")
        hdr_icon.setStyleSheet("font-size: 20px; background: transparent;")
        hdr_lay.addWidget(hdr_icon)
        hdr_title = QLabel("Move Selected Entries")
        hdr_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 700; background: transparent;")
        hdr_lay.addWidget(hdr_title)
        hdr_lay.addStretch()
        hdr_close = QPushButton("✕")
        hdr_close.setFixedSize(36, 32)
        hdr_close.setCursor(Qt.CursorShape.PointingHandCursor)
        hdr_close.setStyleSheet(
            "QPushButton { background: transparent; color: #bbbbbb; border: none; font-size: 16px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #c0392b; color: #fff; }"
        )
        hdr_close.clicked.connect(dlg.reject)
        hdr_lay.addWidget(hdr_close)
        root.addWidget(hdr_w)

        # Body
        body_w = QWidget()
        body_w.setStyleSheet("background-color: #141420;")
        lay = QVBoxLayout(body_w)
        lay.setSpacing(14)
        lay.setContentsMargins(28, 22, 28, 14)

        count_lbl = QLabel(f"Moving <b>{len(selected)}</b> entr{'y' if len(selected) == 1 else 'ies'}")
        count_lbl.setTextFormat(Qt.TextFormat.RichText)
        count_lbl.setStyleSheet("font-size: 17px; font-weight: 600; color: #ccffcc; background: transparent;")
        lay.addWidget(count_lbl)

        lbl_route = QLabel("Move to Route:")
        lbl_route.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; background: transparent;")
        lay.addWidget(lbl_route)
        route_combo = QComboBox()
        route_combo.setStyleSheet(
            "QComboBox { background-color: #1c1c30; color: #ffffff; border: 1.5px solid #4a4a70;"
            "  border-radius: 8px; padding: 10px 14px; font-size: 15px; min-height: 22px; }"
            "QComboBox::drop-down { border: none; width: 30px; }"
            "QComboBox QAbstractItemView { background-color: #1c1c30; color: #ffffff;"
            "  border: 1px solid #5a5a8a; selection-background-color: #4a4a8a; padding: 4px; font-size: 15px; }"
        )
        for route in ALL_ROUTES_ORDERED:
            icon = "🏪" if route == STORE_ROUTE else "🚚"
            route_combo.addItem(f"{icon} {route}", userData=route)
        route_combo.setFont(QFont("Noto Sans Sinhala", 13))
        lay.addWidget(route_combo)

        lbl_round = QLabel("Set Round:")
        lbl_round.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; background: transparent;")
        lay.addWidget(lbl_round)
        round_combo = QComboBox()
        round_combo.setStyleSheet(
            "QComboBox { background-color: #1c1c30; color: #ffffff; border: 1.5px solid #4a4a70;"
            "  border-radius: 8px; padding: 10px 14px; font-size: 15px; min-height: 22px; }"
            "QComboBox::drop-down { border: none; width: 30px; }"
            "QComboBox QAbstractItemView { background-color: #1c1c30; color: #ffffff;"
            "  border: 1px solid #5a5a8a; selection-background-color: #4a4a8a; padding: 4px; font-size: 15px; }"
        )
        round_combo.addItem("Keep Original", userData=0)
        for i in range(1, 6):
            round_combo.addItem(f"Round {i}", userData=i)
        lay.addWidget(round_combo)
        root.addWidget(body_w)

        # Button bar
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            "background-color: #10101a; border-bottom-left-radius: 14px;"
            "border-bottom-right-radius: 14px; border-top: 1px solid #2a2a44;"
        )
        bbl = QHBoxLayout(btn_bar)
        bbl.setContentsMargins(18, 14, 18, 16)
        bbl.setSpacing(12)
        bbl.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #3a3a5a; color: #ffffff; border: 1px solid #4a4a6a;"
            "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background-color: #4a4a6a; color: #ffffff; border-color: #6a6a8a; }"
        )
        cancel_btn.clicked.connect(dlg.reject)
        bbl.addWidget(cancel_btn)

        move_btn = QPushButton("  ➜ Move  ")
        move_btn.setFixedHeight(38)
        move_btn.setMinimumWidth(100)
        move_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        move_btn.setStyleSheet(
            "QPushButton { background-color: #2a6a3a; color: #ffffff; border: none;"
            "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 700; }"
            "QPushButton:hover { background-color: #3a8a4a; }"
        )
        move_btn.clicked.connect(dlg.accept)
        bbl.addWidget(move_btn)
        root.addWidget(btn_bar)

        dlg.adjustSize()

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        target_route = route_combo.currentData()
        target_round = round_combo.currentData()  # 0 = keep original

        # Group selected entries by their source route
        moved = 0
        for src_route in set(r for r, _ in selected):
            src_key = data_key(src_route, self._cycle_key(), self._date_str())
            src_entries = _migrate_slot(self._db.get(src_key, []))
            indices = sorted([ei for r, ei in selected if r == src_route], reverse=True)

            dst_key = data_key(target_route, self._cycle_key(), self._date_str())
            dst_entries = _migrate_slot(self._db.get(dst_key, []))

            for ei in indices:
                if 0 <= ei < len(src_entries):
                    entry = src_entries.pop(ei)
                    if target_round > 0:
                        entry["round"] = target_round
                    dst_entries.append(entry)
                    moved += 1

            self._db[src_key] = src_entries
            self._db[dst_key] = dst_entries

        if moved > 0:
            self._save_db()
            if hasattr(self, '_recalculate_local_reductions'):
                self._recalculate_local_reductions()
            self._load_book()

    def _on_table_delete_pressed(self):
        self._on_delete_selected()

    def _on_table_cell_clicked(self, row: int, column: int):
        if column != 0:
            cb_item = self._book_table.item(row, 0)
            if cb_item:
                if cb_item.checkState() == Qt.CheckState.Checked:
                    cb_item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    cb_item.setCheckState(Qt.CheckState.Checked)

    def _on_table_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0:
            # Force the table to repaint so the delegate draws/removes the highlight
            self._book_table.viewport().update()

    def _append_book_row(self, table: QTableWidget, index: int, route: str, round_val: int, sid: str, amount: int, note: str, entry_idx: int):
        row = table.rowCount()
        table.insertRow(row)
        
        cb_item = QTableWidgetItem()
        cb_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        cb_item.setCheckState(Qt.CheckState.Unchecked)
        cb_item.setData(Qt.ItemDataRole.UserRole, (route, entry_idx))
        table.setItem(row, 0, cb_item)
        
        num = QTableWidgetItem(str(index + 1))
        num.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        num.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        num.setForeground(QColor("#ccccee"))
        num.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        table.setItem(row, 1, num)
        
        route_display = route if round_val == 1 else f"{route} (R{round_val})"
        route_item = QTableWidgetItem(route_display)
        route_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        route_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        route_item.setForeground(QColor(ROUTE_COLORS.get(route, "#b0b0ff")))
        route_item.setFont(QFont("Noto Sans Sinhala", 12))
        table.setItem(row, 2, route_item)
        
        sid_item = QTableWidgetItem(sid)
        sid_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        sid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        sid_item.setForeground(QColor("#ffffff"))
        sid_item.setFont(QFont("Consolas", 13))
        table.setItem(row, 3, sid_item)
        
        amt = QTableWidgetItem(f"{amount:,}")
        amt.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        amt.setForeground(QColor("#ffffff"))
        amt.setFont(QFont("Consolas", 14))
        table.setItem(row, 4, amt)
        
        note_item = QTableWidgetItem(note if note else "")
        note_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        note_item.setForeground(QColor("#ffdd88" if note else "#666688"))
        note_item.setFont(QFont("Segoe UI", 11))
        table.setItem(row, 5, note_item)
        
        table.setRowHeight(row, 42)

    def _edit_entry(self, route: str, entry_idx: int):
        if hasattr(self, '_is_future_cycle') and self._is_future_cycle():
            return
        key = data_key(route, self._cycle_key(), self._date_str())
        entries = _migrate_slot(self._db.get(key, []))
        if 0 <= entry_idx < len(entries):
            entry = entries[entry_idx]
            
            dlg = QDialog(self)
            dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            dlg.setModal(True)
            dlg.setFixedWidth(440)
            dlg._drag_start = None
            def _mp(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    dlg._drag_start = e.globalPosition().toPoint() - dlg.frameGeometry().topLeft()
            def _mm(e):
                if dlg._drag_start and e.buttons() == Qt.MouseButton.LeftButton:
                    dlg.move(e.globalPosition().toPoint() - dlg._drag_start)
            def _mr(e): dlg._drag_start = None
            dlg.mousePressEvent = _mp
            dlg.mouseMoveEvent = _mm
            dlg.mouseReleaseEvent = _mr
            dlg.setStyleSheet(
                "QDialog { background-color: #141420; border: 1.5px solid #4a4a6a; border-radius: 14px; }"
            )
            root = QVBoxLayout(dlg)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            # Header
            hdr_w = QWidget()
            hdr_w.setStyleSheet(
                "background-color: #10101a; border-top-left-radius: 14px;"
                "border-top-right-radius: 14px; border-bottom: 1px solid #3a3a5a;"
            )
            hdr_w.setFixedHeight(48)
            hdr_w.setCursor(Qt.CursorShape.SizeAllCursor)
            hdr_lay = QHBoxLayout(hdr_w)
            hdr_lay.setContentsMargins(18, 0, 10, 0)
            hdr_lay.setSpacing(10)
            hdr_icon = QLabel("✎")
            hdr_icon.setStyleSheet("font-size: 20px; background: transparent;")
            hdr_lay.addWidget(hdr_icon)
            hdr_title = QLabel("Edit Entry")
            hdr_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 700; background: transparent;")
            hdr_lay.addWidget(hdr_title)
            hdr_lay.addStretch()
            hdr_close = QPushButton("✕")
            hdr_close.setFixedSize(36, 32)
            hdr_close.setCursor(Qt.CursorShape.PointingHandCursor)
            hdr_close.setStyleSheet(
                "QPushButton { background: transparent; color: #bbbbbb; border: none; font-size: 16px; border-radius: 6px; }"
                "QPushButton:hover { background-color: #c0392b; color: #fff; }"
            )
            hdr_close.clicked.connect(dlg.reject)
            hdr_lay.addWidget(hdr_close)
            root.addWidget(hdr_w)

            # Body
            body_w = QWidget()
            body_w.setStyleSheet("background-color: #141420;")
            lay = QVBoxLayout(body_w)
            lay.setSpacing(12)
            lay.setContentsMargins(28, 22, 28, 14)

            lbl_sid = QLabel("Supplier ID:")
            lbl_sid.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; background: transparent;")
            lay.addWidget(lbl_sid)
            inp_sid = QLineEdit()
            inp_sid.setText(entry["id"])
            inp_sid.setStyleSheet(
                "QLineEdit { background-color: #1c1c30; color: #ffffff; border: 1.5px solid #4a4a70;"
                "  border-radius: 8px; padding: 10px 14px; font-size: 16px; font-weight: 600; }"
                "QLineEdit:focus { border-color: #7b7bf7; background-color: #2e2e50; }"
            )
            lay.addWidget(inp_sid)

            lbl_amt = QLabel("Amount (Rs.):")
            lbl_amt.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; background: transparent;")
            lay.addWidget(lbl_amt)
            inp_amt = QLineEdit()
            inp_amt.setText(str(entry["amount"]))
            inp_amt.setStyleSheet(
                "QLineEdit { background-color: #1c1c30; color: #ffffff; border: 1.5px solid #4a4a70;"
                "  border-radius: 8px; padding: 10px 14px; font-size: 16px; font-weight: 600;"
                "  font-family: 'Consolas', monospace; }"
                "QLineEdit:focus { border-color: #7b7bf7; background-color: #2e2e50; }"
            )
            lay.addWidget(inp_amt)

            lbl_note = QLabel("Note (optional):")
            lbl_note.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600; background: transparent;")
            lay.addWidget(lbl_note)
            inp_note = QLineEdit()
            inp_note.setText(str(entry.get("note", "")))
            inp_note.setStyleSheet(
                "QLineEdit { background-color: #1c1c30; color: #ffdd88; border: 1.5px solid #4a4a70;"
                "  border-radius: 8px; padding: 10px 14px; font-size: 14px; }"
                "QLineEdit:focus { border-color: #7b7bf7; background-color: #2e2e50; }"
            )
            lay.addWidget(inp_note)
            root.addWidget(body_w)

            # Button bar
            btn_bar = QWidget()
            btn_bar.setStyleSheet(
                "background-color: #10101a; border-bottom-left-radius: 14px;"
                "border-bottom-right-radius: 14px; border-top: 1px solid #2a2a44;"
            )
            bbl = QHBoxLayout(btn_bar)
            bbl.setContentsMargins(18, 14, 18, 16)
            bbl.setSpacing(12)
            bbl.addStretch()

            cancel_btn = QPushButton("Cancel")
            cancel_btn.setFixedHeight(38)
            cancel_btn.setMinimumWidth(100)
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_btn.setStyleSheet(
                "QPushButton { background-color: #3a3a5a; color: #ffffff; border: 1px solid #4a4a6a;"
                "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 600; }"
                "QPushButton:hover { background-color: #4a4a6a; color: #ffffff; border-color: #6a6a8a; }"
            )
            cancel_btn.clicked.connect(dlg.reject)
            bbl.addWidget(cancel_btn)

            save_btn = QPushButton("  ✓ Save  ")
            save_btn.setFixedHeight(38)
            save_btn.setMinimumWidth(100)
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.setStyleSheet(
                "QPushButton { background-color: #5b4af7; color: #ffffff; border: none;"
                "  border-radius: 8px; padding: 0 22px; font-size: 14px; font-weight: 700; }"
                "QPushButton:hover { background-color: #7b6aff; }"
            )
            save_btn.clicked.connect(dlg.accept)
            bbl.addWidget(save_btn)
            root.addWidget(btn_bar)

            dlg.adjustSize()
            
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_sid = inp_sid.text().strip()
                val = self._parse_amount(inp_amt.text())
                if val is not None and new_sid:
                    if new_sid != entry["id"] and not self._handle_dup_check(new_sid, inp_sid):
                        return
                    entries[entry_idx]["id"] = new_sid
                    entries[entry_idx]["amount"] = val
                    entries[entry_idx]["note"] = inp_note.text().strip()
                    self._db[key] = entries
                    self._save_db()
                    if hasattr(self, '_recalculate_local_reductions'):
                        self._recalculate_local_reductions()
                    self._load_book()

    def _delete_entry(self, route: str, entry_idx: int):
        if hasattr(self, '_is_future_cycle') and self._is_future_cycle():
            return
        if DarkMessageBox.ask(self, "🗑 Delete Entry",
                "Are you sure you want to delete this entry?",
                yes_label="Delete", yes_role="danger", icon="warning"):
            key = data_key(route, self._cycle_key(), self._date_str())
            entries = _migrate_slot(self._db.get(key, []))
            if 0 <= entry_idx < len(entries):
                del entries[entry_idx]
                self._db[key] = entries
                self._save_db()
                if hasattr(self, '_recalculate_local_reductions'):
                    self._recalculate_local_reductions()
                self._load_book()

    def _lookup_supplier_net(self, sid: str):
        """Look up a supplier's net_payable from the API data.
        Normalizes IDs so '01', '1', '001' all match correctly.
        Returns the net_payable value if found, or None if not found."""
        if not sid or not hasattr(self, '_web_app_suppliers') or not self._web_app_suppliers:
            return None
        # 1. Try exact match first
        net = self._web_app_suppliers.get(sid, None)
        if net is not None:
            return net
        # 2. Normalize: strip leading zeros and compare
        sid_norm = sid.lstrip('0') or '0'
        for api_id, api_net in self._web_app_suppliers.items():
            api_norm = api_id.lstrip('0') or '0'
            if sid_norm == api_norm:
                return api_net
        return None

    def _is_debt_supplier(self, sid: str) -> bool:
        """Return True if the supplier is NOT in the API data (debt/no payable).
        The API only returns suppliers with positive payable amounts,
        so absence from the list means they have debt or zero balance."""
        if not sid:
            return False
        # Only check if API data was successfully fetched
        if not getattr(self, '_web_app_fetched', False):
            return False  # Can't verify — allow entry when offline
        net = self._lookup_supplier_net(sid)
        # If supplier is not found in API → they have debt or no payable
        return net is None

    def _show_debt_warning(self, sid: str):
        """Show a warning dialog for a supplier not in the payable list."""
        DarkMessageBox.show_warning(self, "⛔ Blocked — Not Payable",
            f"Supplier <b>{sid}</b> is <b>not in the payable list</b> this month."
            f"<br><br>This supplier may have a <b style='color:#ff6666;'>debt</b> "
            f"or <b>zero balance</b>."
            f"<br><br>You <b>cannot</b> enter a payment for this supplier."
            f"<br><span style='color:#aaaaaa;'>Only suppliers with positive payable "
            f"amounts from the tea system are allowed.</span>")
        self._b_id.setFocus()
        self._b_id.selectAll()

    def _on_supplier_id_entered(self):
        """Called when user presses Enter on the Supplier ID field.
        Blocks moving to the amount field if the supplier is in debt."""
        sid = self._b_id.text().strip()
        if not sid:
            self._b_amt.setFocus()
            return
        if self._is_debt_supplier(sid):
            self._show_debt_warning(sid)
            return  # Do NOT move focus to amount field
        self._b_amt.setFocus()

    def _add_entry(self):
        if hasattr(self, '_is_future_cycle') and self._is_future_cycle():
            return
        route = self._current_route()
        sid = self._b_id.text().strip()
        val = self._parse_amount(self._b_amt.text())
        if val is None:
            return
        if not self._handle_dup_check(sid, self._b_id):
            return
        # Block payment if supplier has debt (negative net_payable)
        if self._is_debt_supplier(sid):
            self._show_debt_warning(sid)
            return
        rnd = self._round_combo.currentData()
        key = data_key(route, self._cycle_key(), self._date_str())
        entries = _migrate_slot(self._db.get(key, []))
        entries.append({"id": sid, "amount": val, "round": rnd, "note": self._b_note.text().strip()})
        self._db[key] = entries
        self._save_db()
        if hasattr(self, '_recalculate_local_reductions'):
            self._recalculate_local_reductions()
        self._b_id.clear(); self._b_amt.clear(); self._b_note.clear(); self._b_id.setFocus()
        self._load_book()



    # ── Breakdown logic ───────────────────────────────────────────────

    def _refresh_breakdown(self):
        # Clear existing
        while self._bd_layout.count():
            child = self._bd_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        date_str = self._date_str()
        view_total = 0
        denom_colors = {
            5000: "#ffee55", 1000: "#66ff66", 500: "#cc88ff",
            100: "#ffaa44", 50: "#55aaff", 20: "#ff88cc",
        }
        
        filter_route = self._bd_route_filter.currentData()
        filter_round = self._bd_round_filter.currentData()
        
        cycle_str = self._cycle_key()

        for route in ALL_ROUTES_ORDERED:
            if filter_route != "ALL" and filter_route != route:
                continue

            key = data_key(route, cycle_str, date_str)
            entries = _migrate_slot(self._db.get(key, []))
            if not entries:
                continue
                
            rounds_map = {}
            for e in entries:
                r = e.get("round", 1)
                rounds_map.setdefault(r, []).append(e)

            for rnd in sorted(rounds_map.keys()):
                if filter_round != "ALL" and filter_round != rnd:
                    continue

                round_entries = rounds_map[rnd]
                amounts = [e["amount"] for e in round_entries]
                result = calculate_denomination_breakdown(amounts)
                gt = result["grand_total"]
                view_total += gt
                counts = result["counts"]

                card = QFrame(); card.setObjectName("summaryCard")
                cl = QVBoxLayout(card); cl.setContentsMargins(18, 14, 18, 14); cl.setSpacing(8)

                # Header
                hdr = QHBoxLayout()
                icon = "🏪" if route == STORE_ROUTE else "🚚"
                title_text = f"{icon}  {route}" if rnd == 1 else f"{icon}  {route}  -  Round {rnd}"
                nm = QLabel(title_text)
                nm.setObjectName("summaryRouteName")
                nm.setFont(QFont("Noto Sans Sinhala", 14))
                hdr.addWidget(nm)
                hdr.addStretch()
                vl = QLabel(f"Rs. {gt:,}")
                vl.setObjectName("summaryRouteValue")
                hdr.addWidget(vl)
                ct = QLabel(f"  ({len(round_entries)} entries)")
                ct.setObjectName("summaryRouteCount")
                hdr.addWidget(ct)
                cl.addLayout(hdr)

                # Denom table
                dt = QTableWidget()
                dt.setColumnCount(2)
                dt.setHorizontalHeaderLabels(["Denomination", "Count"])
                dt.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                dt.verticalHeader().setVisible(False)
                dt.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
                dt.setShowGrid(False)
                rows = [(d, counts[d]) for d in DENOMINATIONS if d in counts]
                dt.setRowCount(len(rows))
                for ri, (denom, count) in enumerate(rows):
                    di = QTableWidgetItem(format_denomination(denom))
                    di.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    di.setForeground(QColor(denom_colors.get(denom, "#ffffff")))
                    di.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
                    dt.setItem(ri, 0, di)
                    ci = QTableWidgetItem(str(count))
                    ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    ci.setForeground(QColor("#ffffff"))
                    ci.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
                    dt.setItem(ri, 1, ci)
                    dt.setRowHeight(ri, 40)
                dt.setFixedHeight(len(rows) * 40 + 34)
                cl.addWidget(dt)

                # Print button
                btn_text = f"🖨  Print {route}" if rnd == 1 else f"🖨  Print {route} (R{rnd})"
                pb = QPushButton(btn_text)
                pb.setObjectName("todayBtn")
                pb.setStyleSheet("padding: 8px 20px; font-size: 14px;")
                pb.setCursor(Qt.CursorShape.PointingHandCursor)
                pb.setFont(QFont("Noto Sans Sinhala", 12))
                pb.clicked.connect(lambda _, r=route, rd=rnd: self._print_route(r, rd))
                cl.addWidget(pb, alignment=Qt.AlignmentFlag.AlignRight)

                sh = QGraphicsDropShadowEffect()
                sh.setBlurRadius(20); sh.setOffset(0, 3); sh.setColor(QColor(0, 0, 0, 60))
                card.setGraphicsEffect(sh)
                self._bd_layout.addWidget(card)

        if self._bd_layout.count() == 0:
            empty = QLabel("No entries match your selection for this date")
            empty.setObjectName("summaryRouteCount")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("padding: 40px; font-size: 16px;")
            self._bd_layout.addWidget(empty)

        self._bd_layout.addStretch()
        self._bd_day_total.setText(f"Rs. {view_total:,}")

    # ── Print ────────────────────────────────────────────────────────

    def _print_route(self, route: str, round_val: int = 1):
        date_str = self._date_str()
        cycle_str = self._cycle_key()
        key = data_key(route, cycle_str, date_str)
        all_entries = _migrate_slot(self._db.get(key, []))
        entries = [e for e in all_entries if e.get("round", 1) == round_val]
        amounts = [e["amount"] for e in entries]
        result = calculate_denomination_breakdown(amounts)
        gt = result["grand_total"]
        counts = result["counts"]

        denom_rows = ""
        for d in DENOMINATIONS:
            if d in counts:
                label = format_denomination(d)
                denom_rows += (
                    f'<tr>'
                    f'<td style="padding:12px 20px;font-size:24px;'
                    f'border:1px solid #888;">{label}</td>'
                    f'<td style="padding:12px 20px;font-size:26px;font-weight:bold;'
                    f'text-align:center;border:1px solid #888;">{counts[d]}</td></tr>\n'
                )

        route_display = route if round_val == 1 else f"{route} (Round {round_val})"

        html = f"""
        <html><head><meta charset="utf-8"></head>
        <body style="font-family:'Noto Sans Sinhala','Segoe UI',sans-serif;
                     padding:20px 30px; color:#1a1a2e;">
          <h1 style="font-size:44px; text-align:center; margin:0 0 4px 0;">
            {route_display}
          </h1>
          <p style="font-size:26px; text-align:center; color:#333; margin:4px 0 14px 0;">
            {date_str}
          </p>
          <hr style="border:1px solid #999;">
          <h2 style="font-size:34px; text-align:center; margin:12px 0;">
            Total: Rs. {gt:,}
          </h2>
          <hr style="border:1px solid #999; margin-bottom:14px;">
          <table style="width:55%; border-collapse:collapse;
                        border:2px solid #666; margin-left:18%;">
            <tr style="background:#ddd;">
              <th style="padding:8px 16px; text-align:left; font-size:20px;
                  font-weight:700; border:1px solid #888;">Denomination</th>
              <th style="padding:8px 16px; text-align:center; font-size:20px;
                  font-weight:700; border:1px solid #888;">Count</th>
            </tr>
            {denom_rows}
          </table>
        </body></html>
        """

        _PRINT_DIALOG_STYLE = """
            QDialog { background-color: #1a1a2e; border: 1px solid #3a3a5a; }
            QLabel { color: #ffffff; font-size: 15px; font-weight: 600; }
            QProgressBar { background-color: #2a2a4a; border: 1px solid #3a3a5a;
                border-radius: 6px; text-align: center; color: #e0e0ff; }
            QProgressBar::chunk { background-color: #7b6cf7; border-radius: 5px; }
        """

        connect_dlg = QDialog(self)
        connect_dlg.setWindowTitle("Connecting")
        connect_dlg.setFixedSize(300, 100)
        connect_dlg.setModal(True)
        connect_dlg.setStyleSheet(_PRINT_DIALOG_STYLE)
        cl = QVBoxLayout(connect_dlg); cl.setSpacing(10)
        cl_msg = QLabel("\U0001f50c  Connecting to printer...")
        cl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(cl_msg)
        cl_bar = QProgressBar(); cl_bar.setRange(0, 0)
        cl.addWidget(cl_bar)
        connect_dlg.show()
        QApplication.processEvents()

        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        dialog = QPrintDialog(printer, self)
        connect_dlg.close()

        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return

        print_dlg = QDialog(self)
        print_dlg.setWindowTitle("Printing")
        print_dlg.setFixedSize(300, 100)
        print_dlg.setModal(True)
        print_dlg.setStyleSheet(_PRINT_DIALOG_STYLE)
        pl = QVBoxLayout(print_dlg); pl.setSpacing(10)
        pl_msg = QLabel("\U0001f5a8  Printing...")
        pl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl.addWidget(pl_msg)
        pl_bar = QProgressBar(); pl_bar.setRange(0, 0)
        pl.addWidget(pl_bar)
        print_dlg.show()
        QApplication.processEvents()

        try:
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print(printer)
        except Exception as e:
            DarkMessageBox.show_error(self, "Print Error", f"The printer reported an error:<br>{str(e)}")
        finally:
            print_dlg.close()

    # ── Summary logic ────────────────────────────────────────────────

    def _refresh_summary(self):
        ck = self._cycle_key()  # 'YYYY-MM'
        grand = 0
        for route in ROUTES:
            # Sum ALL dates in the cycle for this route
            route_total = 0; route_count = 0
            for key, entries in self._db.items():
                if "|" not in key:
                    continue
                r, kd = key.split("|", 1)
                if r == route and kd[:7] == ck:
                    slot = _migrate_slot(entries)
                    route_total += sum(e["amount"] for e in slot)
                    route_count += len(slot)
            grand += route_total
            if route in self._sum_values:
                self._sum_values[route].setText(f"Rs. {route_total:,}")
                self._sum_counts[route].setText(
                    f"{route_count} {'entry' if route_count == 1 else 'entries'}")
        self._sum_grand.setText(f"Rs. {grand:,}")

    # ── Window ───────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)


# ── Entry point ─────────────────────────────────────────────────────

def resource_path(relative_path):
    """Get path to resource, works for dev and for PyInstaller bundle."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


_single_instance_mutex = None


def main():
    global _single_instance_mutex

    # ── Single Instance Enforcement (Windows Mutex) ──────────────────────
    try:
        import ctypes
        from ctypes import wintypes
        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        # Create named system-wide mutex
        _single_instance_mutex = kernel32.CreateMutexW(None, False, "HTC_CashFlow_SingleInstance_Mutex")
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            # App is already running: find and bring the existing window to front
            hwnd = user32.FindWindowW(None, "HTC — Cash Flow")
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE (un-minimize if minimized)
                user32.SetForegroundWindow(hwnd)
            sys.exit(0)
    except Exception:
        pass

    # Windows taskbar: set AppUserModelID BEFORE QApplication
    # so Windows associates our icon with the taskbar entry.
    try:
        import ctypes
        from ctypes import wintypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.HRESULT
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HTC.CashFlow.App.1")
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # Global exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        import traceback
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Critical Error")
        msg_box.setText("An unexpected error occurred.\nThe application will now close.")
        msg_box.setDetailedText(error_msg)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        sys.exit(1)
        
    sys.excepthook = handle_exception

    app.setFont(QFont("Segoe UI", 10))
    # Replace dynamic absolute paths in the stylesheet
    final_stylesheet = STYLESHEET.replace("CALENDAR_ICON_PATH", resource_path("cal.svg").replace("\\", "/"))
    app.setStyleSheet(final_stylesheet)
    icon = QIcon(resource_path("cashflow.ico"))
    app.setWindowIcon(icon)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()