# KiCad-Ledger

A small GUI that tracks components you own, so you never order a board without also being certain you own all the components again.

- **100% Local & Private**: Stores your parts in a local SQLite database (`data/inventory.db`). No cloud, no accounts, no telemetry.
- **Auto-Detects Your Open KiCad Board**: Automatically finds your active `.kicad_pcb` / `.kicad_sch` when opened.
- **Smart Part & Value Matching**: Equates `100nF` = `0.1uF`, `4k7` = `4.7k`, `0805` = `2012Metric`, strips reel/LCSC suffixes (`TP4057_C725791` → `TP4057`), and flags higher-voltage compatible capacitors.
- **Distributor Order Imports**: Imports CSV order histories from **LCSC**, **Mouser**, **DigiKey**, or combined/custom order CSVs.
- **"I Own This" Button**: Mark custom or uncatalogued parts (like AliExpress batteries or generic connectors) as owned right from the verification table so they stay saved for future boards.

---

## Quick Start (Windows + KiCad 10)

KiCad ships with Python and `wxPython` pre-installed, so **no extra packages or `pip install` are required**.

1. **Clone the repository**
   ```cmd
   git clone https://github.com/LRNATHD/Kicad-Ledger.git
   cd Kicad-Ledger
   ```

2. **Launch KiCad-Ledger**
   - **Tray & Hotkey Launcher (Recommended)**: Double-click `KiCad-Ledger.exe`.
     - Press `Ctrl+Shift+I` or `F8` while KiCad is focused to pop up **KiCad-Ledger** over your board.
     - Right-click the tray icon and check **Start with Windows** to run it automatically at login.
   - **Standalone Window**: Double-click `run.bat`.

3. **Optional: Add to KiCad PCB Editor Toolbar**
   - Run `install_plugin.bat`.
   - In KiCad PCB Editor, click **Tools → External Plugins → Refresh Plugins** (or restart KiCad).

*(Using a different KiCad version or non-Windows OS? Make sure Python 3.9+ with `wxPython>=4.2.0` is installed and run `python run_gui.py`.)*

---

## Basic Workflow

1. **Import Your Parts**: Open the **Import Orders** tab, browse for an LCSC / Mouser / DigiKey / combined order CSV, and click **Confirm & Save to Local Inventory Database**.
2. **Verify a Board**: Open your project in KiCad and press `Ctrl+Shift+I` (or `F8`), or click **Detect Open Board** / **Open .kicad_pcb / .kicad_sch** in the **Board Verifier** tab.
3. **Mark Manual / Misc Parts**: Select any part you already have on hand (e.g., batteries, connectors, hardware) and click **✓ I Own This** to save it to your local database for future boards.
4. **Order What's Missing**: Click **Copy Missing to Clipboard** or **Export Missing CSV** to generate a shopping list of only what you're short on.

---

## Running Tests

```cmd
"C:\Program Files\KiCad\10.0\bin\python.exe" run_tests.py
```

---

## License

MIT — see [LICENSE](LICENSE).
