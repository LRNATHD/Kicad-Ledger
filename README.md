# KiCad-Ledger

A small GUI that tracks components you own, so you never order a board without also being certain you own all the components again.

- **100% Local & Private**: Stores your parts in a local SQLite database (`data/inventory.db`). No cloud, no accounts, no telemetry.
- **System Tray + Hotkey**: Lives quietly in your Windows system tray. Press `Ctrl+Shift+I` while KiCad is focused to pop it up, or click the tray icon (you can disable the hotkey from the tray menu if you prefer tray-only).
- **Auto-Detects Your Open KiCad Board**: Automatically finds your active `.kicad_pcb` / `.kicad_sch` when opened.
- **Smart Part & Value Matching**: Equates `100nF` = `0.1uF`, `4k7` = `4.7k`, `0805` = `2012Metric`, strips reel/LCSC suffixes (`TP4057_C725791` → `TP4057`), and flags higher-voltage compatible capacitors.
- **Distributor Order Imports**: Imports CSV order histories from **LCSC**, **Mouser**, **DigiKey**, or combined/custom order CSVs.
- **"I Own This" Button**: Mark custom or uncatalogued parts as owned right from the verification table so they stay saved for future boards.

---

## Installation (Windows + KiCad 10)

KiCad ships with Python and `wxPython` pre-installed, so **no extra packages or `pip install` are needed**.

1. **Clone the repository**
   ```cmd
   git clone https://github.com/LRNATHD/Kicad-Ledger.git
   cd Kicad-Ledger
   ```

2. **Run `KiCad-Ledger.exe`**
   - Double-click `KiCad-Ledger.exe` to start it in your system tray.
   - Press `Ctrl+Shift+I` while KiCad is open to pop up the window, or click the tray icon.
   - Right-click the tray icon to toggle **Enable Hotkey (Ctrl+Shift+I)** or **Start with Windows**.

*(Using a different KiCad version or non-Windows OS? Make sure Python 3.9+ with `wxPython>=4.2.0` is installed and run `python run_gui.py`.)*

---

## Basic Workflow

1. **Import Your Parts**: Open the **Import Orders** tab, browse for an LCSC / Mouser / DigiKey / combined order CSV, and click **Confirm & Save to Local Inventory Database**.
2. **Verify a Board**: Open your project in KiCad and press `Ctrl+Shift+I` (or click **Detect Open Board** / **Open .kicad_pcb / .kicad_sch**).
3. **Mark Manual / Misc Parts**: Select any part you already have on hand and click **✓ I Own This** to save it to your local database for future boards.
4. **Order What's Missing**: Click **Copy Missing to Clipboard** or **Export Missing CSV** to generate a shopping list of only what you're short on.

---

## License

MIT — see [LICENSE](LICENSE).
