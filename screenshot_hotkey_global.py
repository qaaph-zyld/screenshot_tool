#!/usr/bin/env python3
"""Global Ctrl+` screenshot hotkey for Windows.

Run this script on Windows to register a global **Ctrl+`** hotkey that:
- Captures a fullscreen screenshot
- Saves it to ~/Pictures/Screenshots
- Copies it to the clipboard

Requires:
- Python 3.8+
- Pillow (PIL):  pip install Pillow
- keyboard:      pip install keyboard

Exit the script with Ctrl+Shift+Q.
"""

import os
import platform
import sys
import threading
import time
from typing import Optional

try:
    from PIL import ImageGrab  # type: ignore
except ImportError:
    ImageGrab = None

try:
    import win32clipboard  # type: ignore
    from io import BytesIO
except ImportError:
    win32clipboard = None


def _copy_image_to_clipboard_win32(image) -> None:
    """Copy PIL image to Windows clipboard using win32clipboard."""
    if win32clipboard is None:
        return
    output = BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]  # Remove BMP header
    output.close()

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


def _copy_to_clipboard_powershell(filepath: str) -> None:
    """Copy image to clipboard using PowerShell (fallback)."""
    import subprocess

    ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
$image = [System.Drawing.Image]::FromFile("{filepath}")
[System.Windows.Forms.Clipboard]::SetImage($image)
'''
    subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True,
        timeout=5,
    )


def capture_screenshot() -> Optional[str]:
    """Capture fullscreen screenshot and copy it to the clipboard.

    Returns the saved file path on success, or None on error.
    """
    if ImageGrab is None:
        print("Pillow (PIL) is required. Install with: pip install Pillow", file=sys.stderr)
        return None

    # Capture the screen
    screenshot = ImageGrab.grab()

    # Save to temp file
    temp_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
    os.makedirs(temp_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(temp_dir, f"screenshot_{timestamp}.png")
    screenshot.save(filepath, "PNG")

    # Copy to clipboard
    if win32clipboard is not None:
        _copy_image_to_clipboard_win32(screenshot)
    else:
        _copy_to_clipboard_powershell(filepath)

    print(f"[screenshot_hotkey_global] Captured screenshot -> {filepath}")
    return filepath


def run_hotkey_loop() -> int:
    """Register global Ctrl+` hotkey and block until exit.

    Exit hotkey: Ctrl+Shift+Q
    """
    if platform.system().lower() != "windows":
        print("This global hotkey script is only supported on Windows.", file=sys.stderr)
        return 10

    try:
        import keyboard  # type: ignore
    except ImportError:
        print("The 'keyboard' package is required. Install with: pip install keyboard", file=sys.stderr)
        return 1

    print("[screenshot_hotkey_global] Running on Windows")
    print(" - Global hotkey:  Ctrl+`  (capture screenshot)")
    print(" - Exit hotkey:    Ctrl+Shift+Q")

    lock = threading.Lock()

    def handler() -> None:
        if not lock.acquire(blocking=False):
            # Capture already in progress
            return
        try:
            capture_screenshot()
        finally:
            lock.release()

    # Register hotkeys. Some layouts use 'grave' as the key name; register both.
    keyboard.add_hotkey("ctrl+`", handler)
    keyboard.add_hotkey("ctrl+grave", handler)

    # Exit with Ctrl+Shift+Q
    keyboard.add_hotkey("ctrl+shift+q", lambda: keyboard.press_and_release("esc"))

    # Block until Esc is pressed (triggered by Ctrl+Shift+Q)
    keyboard.wait("esc")
    print("[screenshot_hotkey_global] Exiting")
    return 0


def main() -> int:
    try:
        return run_hotkey_loop()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # pragma: no cover
        print(f"Unhandled error: {exc}", file=sys.stderr)
        return 99


if __name__ == "__main__":
    raise SystemExit(main())
