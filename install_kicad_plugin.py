"""Installer for KiCad-StockCheck Action Plugin into KiCad."""

import os
import sys
import shutil
from typing import Tuple, List


def find_kicad_plugin_dirs() -> List[str]:
    """Find all KiCad plugin search directories across versions."""
    dirs = []
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return dirs

    kicad_base = os.path.join(appdata, "kicad")
    if not os.path.exists(kicad_base):
        return dirs

    # Check versioned directories: 10.0, 9.0, 8.0, 7.0, 6.0
    for item in os.listdir(kicad_base):
        full = os.path.join(kicad_base, item)
        if os.path.isdir(full):
            # Check if directory name looks like a version (e.g., 10.0, 8.0)
            target = os.path.join(full, "scripting", "plugins")
            dirs.append(target)
            target2 = os.path.join(full, "plugins")
            dirs.append(target2)

    # Legacy / unversioned path
    dirs.append(os.path.join(kicad_base, "scripting", "plugins"))
    return dirs


def install_plugin() -> Tuple[bool, str]:
    """Install plugin stub into KiCad scripting plugins directories."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    plugin_src = os.path.join(repo_root, "plugins", "stockcheck_action.py")
    
    if not os.path.exists(plugin_src):
        return False, f"Source plugin file not found: {plugin_src}"

    candidate_dirs = find_kicad_plugin_dirs()
    installed_paths = []

    stub_content = f'''"""KiCad-StockCheck Loader Plugin."""
import sys
import os

repo_path = r"{repo_root}"
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

try:
    import plugins.stockcheck_action
except Exception as e:
    import pcbnew
    # Log error if any
    print(f"Failed to load StockCheck plugin: {{e}}")
'''

    for pdir in candidate_dirs:
        try:
            # We target the versioned scripting/plugins or plugins folders
            os.makedirs(pdir, exist_ok=True)
            dest_file = os.path.join(pdir, "stockcheck_action.py")
            with open(dest_file, "w", encoding="utf-8") as f:
                f.write(stub_content)
            installed_paths.append(dest_file)
        except Exception as e:
            continue

    if installed_paths:
        paths_str = "\n".join(installed_paths[:3])
        msg = f"Successfully installed KiCad-StockCheck plugin to:\n{paths_str}\n\nRestart KiCad or press 'Refresh Plugins' in KiCad PCB Editor."
        return True, msg
    else:
        return False, "Could not find any KiCad user directory in %APPDATA%\\kicad."


if __name__ == "__main__":
    success, message = install_plugin()
    print(message)
    sys.exit(0 if success else 1)
