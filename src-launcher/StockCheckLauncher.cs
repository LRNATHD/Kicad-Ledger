using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace KiCadStockCheck
{
    public class StockCheckTrayApp
    {
        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll")]
        private static extern short GetAsyncKeyState(int vKey);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll")]
        private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

        [DllImport("user32.dll")]
        private static extern bool AllowSetForegroundWindow(int dwProcessId);

        [DllImport("kernel32.dll")]
        private static extern uint GetCurrentThreadId();

        private const int ASFW_ANY = -1;

        private static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
        private static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
        private const uint SWP_NOMOVE = 0x0002;
        private const uint SWP_NOSIZE = 0x0001;
        private const uint SWP_SHOWWINDOW = 0x0040;

        private const int SW_RESTORE = 9;
        private const int SW_SHOW = 5;

        private const int VK_SHIFT = 0x10;
        private const int VK_CONTROL = 0x11;
        private const int VK_I = 0x49;
        private const int VK_F8 = 0x77;

        private static Mutex _appMutex;
        private NotifyIcon _trayIcon;
        private ContextMenuStrip _trayMenu;
        private ToolStripMenuItem _menuStartup;
        private Thread _hotkeyThread;
        private System.Windows.Forms.Timer _promoteTimer;
        private bool _running = true;

        private string _repoDir;
        private string _pythonwPath;
        private Process _guiProcess;

        public static void StaticLog(string msg)
        {
            try
            {
                string p = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "launcher.log");
                File.AppendAllText(p, string.Format("[{0:yyyy-MM-dd HH:mm:ss}] {1}\r\n", DateTime.Now, msg));
            }
            catch { }
        }

        [STAThread]
        public static void Main(string[] args)
        {
            StaticLog("Main() started.");
            bool createdNew = false;
            try
            {
                _appMutex = new Mutex(true, "KiCad_StockCheck_Tray_Mutex_v1", out createdNew);
            }
            catch (Exception ex)
            {
                StaticLog("Mutex error: " + ex.Message);
            }

            if (!createdNew)
            {
                StaticLog("Existing instance detected. Bringing window to front and exiting.");
                IntPtr existingWnd = FindStockCheckWindow();
                if (existingWnd != IntPtr.Zero)
                {
                    ShowWindow(existingWnd, SW_RESTORE);
                    SetForegroundWindow(existingWnd);
                }
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            var app = new StockCheckTrayApp();
            app.Initialize();

            StaticLog("Entering Application.Run() message loop.");
            Application.Run();
            StaticLog("Application.Run() loop ended.");
        }

        public void Initialize()
        {
            _repoDir = AppDomain.CurrentDomain.BaseDirectory;
            StaticLog("Initializing in: " + _repoDir);

            _pythonwPath = @"C:\Program Files\KiCad\10.0\bin\pythonw.exe";
            if (!File.Exists(_pythonwPath))
            {
                _pythonwPath = "pythonw.exe";
            }

            InitTray();
            StaticLog("Tray icon created and visible.");

            // Timer to promote tray icon to taskbar in Windows 11 registry
            _promoteTimer = new System.Windows.Forms.Timer();
            _promoteTimer.Interval = 2000;
            _promoteTimer.Tick += (s, e) =>
            {
                PromoteTrayIconInRegistry();
            };
            _promoteTimer.Start();

            // Background hotkey listener
            _hotkeyThread = new Thread(HotkeyListenerLoop) { IsBackground = true };
            _hotkeyThread.Start();
            StaticLog("Hotkey listener active. Listening for Ctrl+Shift+I and F8 when KiCad is focused.");
        }

        private void InitTray()
        {
            _trayMenu = new ContextMenuStrip();

            var itemOpen = new ToolStripMenuItem("Open KiCad-Ledger", null, (s, e) => ShowOrLaunchUI());
            itemOpen.Font = new Font(itemOpen.Font, FontStyle.Bold);
            _trayMenu.Items.Add(itemOpen);

            _trayMenu.Items.Add("Verify Active KiCad Board", null, (s, e) => ShowOrLaunchUI());
            _trayMenu.Items.Add("Search Inventory", null, (s, e) => ShowOrLaunchUI());
            _trayMenu.Items.Add("Import Orders...", null, (s, e) => ShowOrLaunchUI());

            _trayMenu.Items.Add(new ToolStripSeparator());

            _menuStartup = new ToolStripMenuItem("Start with Windows", null, (s, e) => ToggleStartup());
            _menuStartup.Checked = IsStartupEnabled();
            _trayMenu.Items.Add(_menuStartup);

            _trayMenu.Items.Add(new ToolStripSeparator());

            _trayMenu.Items.Add("Exit", null, (s, e) => ExitApplication());

            Icon trayIco = null;
            string iconPath = Path.Combine(_repoDir, "assets", "icon.ico");
            if (File.Exists(iconPath))
            {
                try { trayIco = new Icon(iconPath); } catch { }
            }

            if (trayIco == null)
            {
                trayIco = SystemIcons.Application;
            }

            _trayIcon = new NotifyIcon
            {
                Icon = trayIco,
                Text = "KiCad-Ledger (Ctrl+Shift+I)",
                Visible = true,
                ContextMenuStrip = _trayMenu
            };

            _trayIcon.DoubleClick += (s, e) => ShowOrLaunchUI();
            _trayIcon.Click += (s, e) =>
            {
                var me = e as MouseEventArgs;
                if (me != null && me.Button == MouseButtons.Left)
                {
                    ShowOrLaunchUI();
                }
            };
        }

        private void HotkeyListenerLoop()
        {
            bool wasPressed = false;

            while (_running)
            {
                try
                {
                    bool ctrl = (GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0;
                    bool shift = (GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0;
                    bool iKey = (GetAsyncKeyState(VK_I) & 0x8000) != 0;
                    bool f8Key = (GetAsyncKeyState(VK_F8) & 0x8000) != 0;

                    bool hotkeyPressed = (ctrl && shift && iKey) || f8Key;

                    if (hotkeyPressed && !wasPressed)
                    {
                        wasPressed = true;
                        if (IsKiCadActive())
                        {
                            StaticLog("Hotkey pressed with KiCad active! Triggering UI popup.");
                            ShowOrLaunchUI();
                        }
                        else
                        {
                            StaticLog("Hotkey pressed, but foreground window is not KiCad.");
                        }
                    }
                    else if (!hotkeyPressed)
                    {
                        wasPressed = false;
                    }

                    Thread.Sleep(15);
                }
                catch
                {
                    Thread.Sleep(100);
                }
            }
        }

        private bool IsKiCadActive()
        {
            IntPtr hwnd = GetForegroundWindow();
            if (hwnd == IntPtr.Zero) return false;

            try
            {
                uint pid = 0;
                GetWindowThreadProcessId(hwnd, out pid);
                if (pid != 0)
                {
                    string procName = Process.GetProcessById((int)pid).ProcessName.ToLowerInvariant();
                    if (procName.Contains("kicad") || procName.Contains("pcbnew") || procName.Contains("eeschema"))
                    {
                        return true;
                    }
                }
            }
            catch { }

            var sb = new StringBuilder(512);
            GetWindowText(hwnd, sb, sb.Capacity);
            string title = sb.ToString().ToLowerInvariant();

            string[] kicadKeywords = {
                "kicad",
                "schematic editor",
                "pcb editor",
                "eeschema",
                "pcbnew",
                "footprint editor",
                "symbol editor"
            };

            foreach (var kw in kicadKeywords)
            {
                if (title.Contains(kw)) return true;
            }
            return false;
        }

        private void ShowOrLaunchUI()
        {
            IntPtr existingWnd = FindStockCheckWindow();

            if (existingWnd != IntPtr.Zero)
            {
                ForceForeground(existingWnd);
                return;
            }

            string scriptPath = Path.Combine(_repoDir, "run_gui.py");
            if (!File.Exists(scriptPath))
            {
                MessageBox.Show("Could not find run_gui.py in: " + _repoDir, "KiCad-StockCheck Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            try
            {
                StaticLog("Launching GUI via pythonw.exe...");
                AllowSetForegroundWindow(ASFW_ANY);
                var psi = new ProcessStartInfo
                {
                    FileName = _pythonwPath,
                    Arguments = "\"" + scriptPath + "\"",
                    WorkingDirectory = _repoDir,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                _guiProcess = Process.Start(psi);
            }
            catch (Exception ex)
            {
                StaticLog("Error launching GUI: " + ex.Message);
                MessageBox.Show("Failed to launch StockCheck GUI:\n" + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void ForceForeground(IntPtr hWnd)
        {
            IntPtr fg = GetForegroundWindow();
            uint dummy;
            uint fgTid = fg != IntPtr.Zero ? GetWindowThreadProcessId(fg, out dummy) : 0;
            uint curTid = GetCurrentThreadId();
            bool attached = false;
            if (fgTid != 0 && fgTid != curTid)
            {
                attached = AttachThreadInput(curTid, fgTid, true);
            }
            try
            {
                ShowWindow(hWnd, SW_RESTORE);
                SetWindowPos(hWnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW);
                SetWindowPos(hWnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW);
                SetForegroundWindow(hWnd);
            }
            finally
            {
                if (attached)
                {
                    AttachThreadInput(curTid, fgTid, false);
                }
            }
        }

        private static IntPtr FindStockCheckWindow()
        {
            IntPtr found = IntPtr.Zero;
            Process[] procs = Process.GetProcesses();
            foreach (var p in procs)
            {
                try
                {
                    if (p.MainWindowHandle != IntPtr.Zero && p.MainWindowTitle.StartsWith("KiCad-Ledger", StringComparison.OrdinalIgnoreCase))
                    {
                        found = p.MainWindowHandle;
                        break;
                    }
                }
                catch { }
            }
            return found;
        }

        private string GetStartupShortcutPath()
        {
            string startup = Environment.GetFolderPath(Environment.SpecialFolder.Startup);
            return Path.Combine(startup, "KiCad_Ledger.lnk");
        }

        private bool IsStartupEnabled()
        {
            return File.Exists(GetStartupShortcutPath());
        }

        private void ToggleStartup()
        {
            string shortcutPath = GetStartupShortcutPath();
            bool current = IsStartupEnabled();

            if (current)
            {
                try { File.Delete(shortcutPath); } catch { }
            }
            else
            {
                CreateStartupShortcut(shortcutPath);
            }

            _menuStartup.Checked = IsStartupEnabled();
        }

        private void CreateStartupShortcut(string shortcutPath)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                dynamic shell = Activator.CreateInstance(shellType);
                dynamic shortcut = shell.CreateShortcut(shortcutPath);
                shortcut.TargetPath = Path.Combine(_repoDir, "KiCad-Ledger.exe");
                shortcut.WorkingDirectory = _repoDir;
                shortcut.Description = "KiCad-Ledger Component Inventory & Board Verifier";
                shortcut.IconLocation = Path.Combine(_repoDir, "assets", "icon.ico");
                shortcut.Save();
            }
            catch { }
        }

        public void PromoteTrayIconInRegistry()
        {
            try
            {
                using (RegistryKey baseKey = Registry.CurrentUser.OpenSubKey(@"Control Panel\NotifyIconSettings", true))
                {
                    if (baseKey == null) return;

                    foreach (string subName in baseKey.GetSubKeyNames())
                    {
                        using (RegistryKey sub = baseKey.OpenSubKey(subName, true))
                        {
                            if (sub != null)
                            {
                                object p = sub.GetValue("ExecutablePath");
                                if (p != null && p.ToString().IndexOf("StockCheck", StringComparison.OrdinalIgnoreCase) >= 0)
                                {
                                    object current = sub.GetValue("IsPromoted");
                                    if (current == null || (int)current != 1)
                                    {
                                        sub.SetValue("IsPromoted", 1, RegistryValueKind.DWord);
                                        StaticLog(string.Format("Promoted tray icon in NotifyIconSettings\\{0} (IsPromoted = 1)", subName));
                                    }
                                }
                            }
                        }
                    }
                }
            }
            catch { }
        }

        private void ExitApplication()
        {
            _running = false;
            if (_promoteTimer != null)
            {
                _promoteTimer.Stop();
                _promoteTimer.Dispose();
            }

            if (_trayIcon != null)
            {
                _trayIcon.Visible = false;
                _trayIcon.Dispose();
            }

            try
            {
                if (_guiProcess != null && !_guiProcess.HasExited)
                {
                    _guiProcess.Kill();
                }
            }
            catch { }

            Application.Exit();
        }
    }
}
