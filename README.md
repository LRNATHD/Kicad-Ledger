<h1 align="center">
  <br>
  ⚡ KiCad-StockCheck ⚡
  <br>
</h1>

<h4 align="center">
  Fast, 100% on-device component inventory checker and KiCad board BOM verifier.
</h4>

<p align="center">
  <img src="https://img.shields.io/badge/KiCad-6%20|%207%20|%208%20|%209%20|%2010-314CB0.svg?logo=kicad&logoColor=white" alt="KiCad Versions">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Privacy-100%25%20On--Device-success.svg?logo=shield" alt="Privacy">
  <img src="https://img.shields.io/badge/Git--Safe-User%20Data%20Protected-brightgreen.svg" alt="Git Protection">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<p align="center">
  <a href="#-key-features">Key Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-distributor-order-imports">Order Imports</a> •
  <a href="#-smart-normalization-engine">Normalization</a> •
  <a href="#-kicad-board-verification">Board Verifier</a> •
  <a href="#-privacy--git-safety">Privacy Guarantee</a> •
  <a href="#-troubleshooting">FAQ</a>
</p>

---

## 🎯 Overview

**KiCad-StockCheck** is a local-first electronics inventory manager and board checker tailored for KiCad designers. 

Instead of juggling Excel spreadsheets, searching physical bins by hand, or using cloud services that track your bill of materials, **KiCad-StockCheck** runs completely on your machine. With a single keybind that **only fires when KiCad is open**, it instantly pops up over your schematic or PCB, cross-references all components against your real physical stock, and alerts you to missing parts before you start assembly.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ KiCad-StockCheck — Demo Board (Fulfillment: 91.3%)                     [✕]             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [📁 Open Board] [🔄 Re-Verify]   Total: 34 | ✓ In Stock: 14 | ⚠ Low: 1 | ❌ Missing: 1  │
├────────────┬────────┬───────────┬──────────────┬─────────┬──────────────┬──────────────┤
│ Status     │ Needed │ Available │ Value        │ Package │ References   │ Match Note   │
├────────────┼────────┼───────────┼──────────────┼─────────┼──────────────┼──────────────┤
│ ✓ In Stock │ 4      │ 100       │ 10k          │ 0805    │ R1, R2, R3,R4│ Exact [Tray1]│
│ ✓ In Stock │ 4      │ 50        │ 100nF        │ 0805    │ C1, C2, C3,C4│ Exact 50V X7R│
│ ✓ In Stock │ 1      │ 5         │ STM32F401CEU6│ QFN-48  │ U1           │ Clean MPN    │
│ ⚠ Low Stock│ 2      │ 1         │ 4.7k         │ 0805    │ R5, R6       │ Short by 1!  │
│ ❌ Missing  │ 1      │ 0         │ 220k         │ 0805    │ R8           │ 0 in stock   │
├────────────┴────────┴───────────┴──────────────┴─────────┴──────────────┴──────────────┤
│ [📋 Copy Missing to Clipboard]   [💾 Export Missing CSV]   [📦 Search Stash (Ctrl+F)]   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- 🎹 **KiCad-Only Keybind Popup**: Press your hotkey (`Ctrl+Shift+I` or `F8`), and the HUD pops up instantly. If you are in Chrome, VS Code, or gaming, the hotkey is completely ignored and will not interfere with other apps.
- 🧩 **Deep KiCad Integration**: Run as a native KiCad Action Plugin (right on the PCB Editor toolbar) or as a background daemon across Eeschema and PCBnew.
- 📦 **Imports Mouser, LCSC & DigiKey Orders**: Automatically parses and imports order history CSVs from major distributors into your local inventory with one click.
- 🧠 **Package & Size Aware**: Knows that `Resistor_SMD:R_0805_2012Metric` matches `0805` and `2012Metric`. Distinguishes between `0805`, `0603`, `0402`, `1206`, `SOT-23`, `SOIC-8`, `QFN-32`, etc.
- 🔢 **Intelligent SI Unit Normalization**: Automatically converts and equates equivalent notation:
  - `0.1uF` == `100nF` == `100n`
  - `4k7` == `4.7k` == `4700Ω`
  - `0R05` == `0.05Ω`
- 🔬 **All Components Supported**: Not just resistors and capacitors! Handles Microcontrollers (STM32, ESP32, RP2040), LDOs, MOSFETs, Diodes, Crystals, USB Connectors, and Custom ICs by MPN and footprint.
- ⚡ **Alternative & Compatibility Detection**: Identifies safe substitutes (e.g. higher-voltage-rated MLCC capacitors in the same footprint).
- 🔒 **100% On-Device Privacy**: No accounts, no internet access, no analytics, no external servers.
- 🛡️ **Git-Safe By Design**: Zero risk of leaking receipts or personal databases. `.gitignore` strictly protects your `inventory.db` and invoices.

---

## 🚀 Quick Start

### Option 1: Direct Batch Launcher (Windows)
Double-click `run.bat` in the repository root. It automatically uses KiCad's bundled Python and launches the GUI:

```cmd
run.bat
```

### Option 2: KiCad PCB Action Plugin (Recommended)
Install the plugin directly into KiCad PCB Editor:

```cmd
install_plugin.bat
```
*(Or run `python install_kicad_plugin.py`)*

1. Open **KiCad PCB Editor**.
2. Click **Tools → External Plugins → Refresh Plugins**.
3. Look for the **StockCheck** icon on the top toolbar!
4. *(Optional)* Assign a hotkey in **Preferences → Hotkeys** (search for "StockCheck").

### Option 3: Background Hotkey Daemon
To have the HUD pop up with `Ctrl+Shift+I` whenever KiCad is your active window:

```cmd
run_hotkey.bat
```

---

## 📥 Distributor Order Imports

Easily import orders from Mouser, LCSC, and DigiKey without retyping part numbers.

| Distributor | How to Export Order CSV | Auto-Extracted Fields |
| :--- | :--- | :--- |
| **LCSC** | Go to *My Orders → Order Details → Export Order (CSV)* | LCSC Part # (`Cxxxx`), MPN, Package, Quantity, Description, Unit Price |
| **Mouser** | Go to *Order History → View Order → Download Order (CSV)* | Mouser Part #, MFR Part #, Package/Case, Qty Shipped, Unit Price |
| **DigiKey** | Go to *Orders & History → Order Details → Download CSV* | DigiKey Part #, MFR Part #, Package, Quantity, Unit Price |
| **Custom / CSV** | Any CSV with headers `Value`, `Package`, `Quantity`, `MPN` | Manual stock, storage drawer bins, custom parts |

### 1-Click Testing with Included Samples
Want to test immediately? In the **Import Orders** tab, click:
- `Load Sample LCSC Order`
- `Load Sample Mouser Order`
- `Load Sample DigiKey Order`

Then click **✓ Confirm & Save to Local Inventory Database**.

---

## 🧠 Smart Normalization Engine

### 1. Passive Values
KiCad-StockCheck normalizes all engineering multipliers to base SI units:

| Board Value | Inventory Value | Match Status | Note |
| :--- | :--- | :---: | :--- |
| `100nF` | `0.1uF` | `✓ MATCH` | Automatically recognized as $10^{-7}\text{ F}$ |
| `4k7` | `4.7k` | `✓ MATCH` | Letter decimal recognized as $4700\ \Omega$ |
| `0R05` | `50mΩ` | `✓ MATCH` | Sub-ohm current-sense resistor |
| `10uF 16V` | `10uF 50V` | `⚡ COMPATIBLE` | Higher voltage capacitor in same package |

### 2. Footprint / Package Aliasing
Cross-references imperial and metric EIA designations, stripping KiCad library prefixes:

| KiCad Footprint String | Canonical Package | Compatible Footprint |
| :--- | :---: | :--- |
| `Resistor_SMD:R_0805_2012Metric` | `0805` | `0805`, `2012`, `2012Metric` |
| `Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm` | `0603` | `0603`, `1608`, `1608Metric` |
| `Package_TO_SOT_SMD:SOT-23-3` | `SOT-23` | `SOT-23`, `SOT-23-3` |
| `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` | `SOIC-8` | `SOIC-8`, `SOP-8` |
| `Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm` | `QFN-32` | `QFN-32`, `VQFN-32` |

### 3. Active Components & ICs
For microcontrollers, regulators, and diodes:
- **Clean MPN Matching**: Automatically strips reel/tape suffixes (`-TR`, `REEL`, `#PBF`, `/NOPB`). For example, board symbol `STM32F401CEU6` matches stock item `STM32F401CEU6TR`.
- **LCSC SKU Matching**: If you use an `LCSC` custom property (e.g. `C2040`), StockCheck performs an instant direct lookup.

---

## 🔍 KiCad Board Verification

Load any `.kicad_pcb` or `.kicad_sch` file, or open StockCheck directly from inside PCB Editor:

1. **Fulfillment Percentage**: Instant overview of board manufacturability.
2. **Missing Component Alert**: Pinpoints exactly how many units you are short.
3. **Clipboard Export**: One click to copy a formatted list of missing parts directly into Mouser / LCSC BOM builder carts.
4. **CSV Export**: Generate a procurement shopping list for ordering.

---

## 🔒 Privacy & Git Safety

### 100% On-Device Guarantee
- **No Cloud Communication**: Never connects to an external server or API.
- **Zero Telemetry**: No tracking, analytics, or background pings.
- **Local SQLite Storage**: Your physical parts database is stored at `data/inventory.db`.

### Git Exclusion Architecture
When contributing to this repository or pushing to GitHub, your personal inventory data will **never** be committed. The `.gitignore` file strictly blocks:

```gitignore
*.db
*.sqlite
data/
orders/
invoices/
*.receipt.csv
config.json
```

---

## 🧪 Testing

Run the included automated test suite anytime using KiCad's Python:

```cmd
"C:\Program Files\KiCad\10.0\bin\python.exe" run_tests.py
```

All unit tests verify:
- Resistor, capacitor, and inductor parsing and equivalence.
- Imperial/metric SMD footprint matching.
- Mouser, LCSC, and DigiKey CSV order importers.
- KiCad S-expression `.kicad_pcb` file parser.
- End-to-end stock verification engine.

---

## ⌨️ Keyboard Shortcuts & Configuration

| Action | Shortcut | Condition |
| :--- | :--- | :--- |
| **Open StockCheck HUD** | `Ctrl+Shift+I` or `F8` | **Only when KiCad is focused** |
| **Filter by Missing** | `Alt+M` | In StockCheck window |
| **Search Inventory** | `Ctrl+F` | In StockCheck window |
| **Close HUD** | `Esc` | In StockCheck window |

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.
Free for personal, academic, and commercial PCB design.
