# Screenshot on Ctrl+1 – Screenshot Automation Tool

Production-ready screenshot automation for **Windows** and **Linux** desktops.

- **One-key screenshot**: Fullscreen capture → clipboard
- **GUI Widget**: Always-on-top `+1` button (cross-platform)
- **CLI automation**: Headless script for hotkey integration (Linux)
- **Multi-distro**: Debian/Ubuntu, Fedora, Arch (or manual)
- **Robust**: Dependency checks, timeouts, logging, cleanup, basic locking

This repo provides:
- `screenshot_widget.py` – **GUI widget** with always-on-top `+1` button (Windows & Linux)
- `screenshot_hotkey_global.py` – **Windows global hotkey** (Ctrl+`) for fullscreen screenshot → clipboard
- `screenshot_clipboard.py` – CLI orchestration script (Linux)
- `install_screenshot_automation.sh` – installer that deploys the CLI script to `/usr/local/bin/screenshot-automate`

---

## Quick Start: GUI Widget (Windows & Linux)

The easiest way to use this tool is the **always-on-top widget**:

```bash
# Install dependencies (Windows)
pip install Pillow keyboard

# Run the widget
python screenshot_widget.py
```

A small window with a green **+1** button appears. Click it, or press **Ctrl+`** while the widget window is focused, to:
1. Hide the widget
2. Capture fullscreen
3. Copy to clipboard
4. Show the widget again (button flashes ✓ on success)

Press **Esc** to close the widget.

**Screenshots are saved to:** `~/Pictures/Screenshots/`

---

## 1. Requirements

### For GUI Widget & Global Hotkey (Windows)
- Python 3.8+
- **Pillow** (`pip install Pillow`)
- **keyboard** (`pip install keyboard`)

### For GUI Widget (Linux)
- Python 3.8+
- **Flameshot** (`sudo apt install flameshot`)
- Tkinter (usually included with Python)

### For CLI Script (Linux only)
- **Flameshot** (screenshot engine)
- **xclip** (clipboard integration, optional but recommended)
- **Python 3**

The installer will try to install missing packages on:
- Debian/Ubuntu
- Fedora/RHEL/CentOS
- Arch Linux

---

## 2. One-Command Installation (Linux CLI)

On your Linux machine, run:

```bash
curl -fsSL https://raw.githubusercontent.com/qaaph-zyld/screenshot_tool/main/install_screenshot_automation.sh | bash
```

What this does:
- Installs `flameshot`, `xclip`, and `python3` when possible
- Downloads `screenshot_clipboard.py`
- Installs it as `/usr/local/bin/screenshot-automate`

After this, you can bind your desktop shortcut (e.g. `Ctrl+1`) to:

```bash
/usr/local/bin/screenshot-automate
```

---

## 3. Manual Installation

If you prefer to clone the repo or download files manually:

```bash
# Clone the repo
git clone https://github.com/qaaph-zyld/screenshot_tool.git
cd screenshot_tool

# Make the installer executable
chmod +x install_screenshot_automation.sh

# Run the installer
./install_screenshot_automation.sh
```

This will install the script to `/usr/local/bin/screenshot-automate`.

---

## 4. Configure the Keyboard Shortcut

### 4.1 GNOME (Ubuntu, Fedora, etc.)

Bind `Ctrl+1` to the script via `gsettings`:

```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/']"

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ name 'Screenshot Automate'

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ command '/usr/local/bin/screenshot-automate'

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ binding '<Primary>1'
```

Now `Ctrl+1` will trigger the script.

### 4.2 KDE Plasma

Example binding via `kwriteconfig5`:

```bash
mkdir -p ~/.config

kwriteconfig5 --file ~/.config/kglobalshortcutsrc \
  --group "screenshot-automate.desktop" \
  --key "_launch" "Ctrl+1,none,Screenshot Automate"
```

Then restart Plasma or log out/in for the shortcut to take effect.

### 4.3 Any Desktop Environment (Manual)

Most DEs support custom shortcuts via GUI settings:

1. Open **System Settings → Keyboard → Custom Shortcuts** (or similar)
2. Add a new custom shortcut
3. **Name**: `Screenshot Automate`
4. **Command**: `/usr/local/bin/screenshot-automate`
5. **Shortcut**: Press `Ctrl+1`

---

## 5. How It Works

### Execution Flow

1. Desktop hotkey (e.g. `Ctrl+1`) is pressed
2. Desktop environment executes `/usr/local/bin/screenshot-automate`
3. Python script:
   - Validates dependencies (`flameshot`, optionally `xclip`)
   - Ensures screenshot directory exists (default: `~/Pictures/Screenshots`)
   - Invokes Flameshot for a fullscreen screenshot, with clipboard copy enabled
   - Uses `xclip` as a redundant clipboard copy (if available)
   - Cleans up screenshots older than 24 hours
   - Logs everything to `~/.screenshot_automation.log`

### Performance Targets

- Latency: typically ~200–400 ms from keypress to clipboard
- Memory: < 50 MB peak
- Storage: old screenshots auto-cleaned (24 h retention)

---

## 6. Testing the Installation

After installation on Linux:

```bash
# Manual test run
/usr/local/bin/screenshot-automate

# Tail the log
tail -f ~/.screenshot_automation.log

# Verify clipboard contents by writing to a file
xclip -selection clipboard -o > test.png
```

- If `test.png` opens as an image, clipboard integration works.
- Any errors will be logged in `~/.screenshot_automation.log` with clear messages.

---

## 7. Customization

You can customize behavior by editing `screenshot_clipboard.py` before installation or in `/usr/local/bin/screenshot-automate` after installation.

### 7.1 Screenshot Directory

Default directory inside the script:

```python
self.temp_dir = os.path.expanduser('~/Pictures/Screenshots')
```

Change this path to use another directory.

### 7.2 Retention Period / Cleanup

Default retention is 24 hours:

```python
self.retention_hours = 24
```

To **disable auto-cleanup**, you can comment out the cleanup call in `run()`:

```python
# self.cleanup_old_screenshots()
```

### 7.3 Log File Location

Logs are written to:

```python
self.log_file = os.path.expanduser('~/.screenshot_automation.log')
```

Change this to redirect logs elsewhere.

---

## 8. Error Handling & Exit Codes

The script is designed to fail fast and log clearly:

- Validates platform (Linux only)
- Verifies `flameshot` is installed (required)
- Uses `xclip` when present, but still works without it
- Protects against hangs via timeouts
- Uses a lock file to avoid overlapping runs

Example exit codes (non-exhaustive):

- `0` – success
- `1` – missing required dependency (e.g. `flameshot`)
- `10` – unsupported platform (non-Linux)
- `11` – could not acquire lock
- `20` – screenshot capture failed
- `99` – unexpected/unhandled exception

See `~/.screenshot_automation.log` for details in failure cases.

---

## 9. Features Implemented

- ✅ **GUI Widget** – Always-on-top `+1` button (Windows & Linux), shortcut **Ctrl+`** while focused
- ✅ **Windows global hotkey** – Background script with **Ctrl+`** anywhere
- ✅ One-key screenshot capture on Linux (e.g. `Ctrl+1` bound to `/usr/local/bin/screenshot-automate`)
- ✅ Automatic clipboard copy
- ✅ Cross-platform support (Windows via Pillow, Linux via Flameshot)
- ✅ Multi-distro support in installer (Ubuntu/Fedora/Arch)
- ✅ Automated installation to `/usr/local/bin`
- ✅ Error logging and recovery
- ✅ Auto-cleanup of old screenshots (Linux CLI)
- ✅ Dependency verification
- ✅ Desktop environment detection (for logging/diagnostics)

On Windows, **click the `+1` button**, press **Ctrl+` with the widget focused**, or run the **global hotkey script** and press **Ctrl+` anywhere** – then just paste your screenshot.
