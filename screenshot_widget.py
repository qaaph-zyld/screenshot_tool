#!/usr/bin/env python3
"""
Always-on-top screenshot widget with a '+1' button.
Click the button, or press Ctrl+` while the widget is focused, to capture a screenshot.
Works on Windows and Linux.
"""

import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Optional

# Attempt to import PIL for clipboard on Windows
try:
    from PIL import ImageGrab  # type: ignore
except ImportError:
    ImageGrab = None

# Attempt to import win32clipboard for Windows clipboard
try:
    import win32clipboard  # type: ignore
    from io import BytesIO
except ImportError:
    win32clipboard = None


class ScreenshotWidget:
    """Small always-on-top widget with a '+1' button to trigger screenshots."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("+1")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        # Make window small
        self.root.geometry("60x40")

        # Style the button
        self.button = tk.Button(
            self.root,
            text="+1",
            font=("Arial", 14, "bold"),
            command=self.on_click,
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        )
        self.button.pack(expand=True, fill="both", padx=2, pady=2)

        # Ensure the widget starts focused so shortcuts work immediately
        self.root.lift()
        self.root.focus_force()
        self.button.focus_set()

        # Bind keyboard shortcut: Ctrl+` while widget is focused
        self.root.bind("<Key>", self._on_key)

        # Platform detection
        self.platform = platform.system().lower()

    def _on_key(self, event) -> None:
        # Close widget with Escape
        if event.keysym == "Escape":
            self.root.quit()
            return

        # On most Tk builds, Control is bit 0x4 in event.state
        try:
            ctrl_down = bool(event.state & 0x4)
        except Exception:
            ctrl_down = False

        if ctrl_down and event.char == "`":
            self.on_click()

    def on_click(self) -> None:
        """Handle button click - hide window, capture screenshot, show window."""
        # Disable button to prevent double-clicks
        self.button.config(state="disabled", text="...")

        # Hide the widget so it doesn't appear in the screenshot
        self.root.withdraw()
        self.root.update()

        # Small delay to ensure window is hidden
        time.sleep(0.15)

        # Run capture in a thread to keep UI responsive
        thread = threading.Thread(target=self._capture_and_restore, daemon=True)
        thread.start()

    def _capture_and_restore(self) -> None:
        """Capture screenshot and restore widget."""
        try:
            success = self._capture_screenshot()
            self.root.after(0, lambda: self._restore_widget(success))
        except Exception as e:
            self.root.after(0, lambda: self._restore_widget(False, str(e)))

    def _restore_widget(self, success: bool, error: Optional[str] = None) -> None:
        """Restore widget after capture."""
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.button.focus_set()
        self.button.config(state="normal", text="+1")

        if success:
            # Brief visual feedback
            self.button.config(bg="#2196F3", text="✓")
            self.root.after(500, lambda: self.button.config(bg="#4CAF50", text="+1"))
        elif error:
            messagebox.showerror("Screenshot Error", error)

    def _capture_screenshot(self) -> bool:
        """Capture screenshot based on platform."""
        if self.platform == "windows":
            return self._capture_windows()
        elif self.platform == "linux":
            return self._capture_linux()
        else:
            return False

    def _capture_windows(self) -> bool:
        """Capture screenshot on Windows using PIL and copy to clipboard."""
        if ImageGrab is None:
            raise RuntimeError("Pillow (PIL) is required. Install with: pip install Pillow")

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
            self._copy_image_to_clipboard_win32(screenshot)
        else:
            # Fallback: try using PowerShell
            self._copy_to_clipboard_powershell(filepath)

        return True

    def _copy_image_to_clipboard_win32(self, image) -> None:
        """Copy PIL image to Windows clipboard using win32clipboard."""
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

    def _copy_to_clipboard_powershell(self, filepath: str) -> None:
        """Copy image to clipboard using PowerShell (fallback)."""
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

    def _capture_linux(self) -> bool:
        """Capture screenshot on Linux using the existing automation script or flameshot."""
        # First, try to use the installed screenshot-automate script
        automate_path = "/usr/local/bin/screenshot-automate"
        if os.path.isfile(automate_path) and os.access(automate_path, os.X_OK):
            result = subprocess.run([automate_path], capture_output=True, timeout=10)
            return result.returncode == 0

        # Fallback: use flameshot directly
        flameshot = self._which("flameshot")
        if flameshot:
            temp_dir = os.path.expanduser("~/Pictures/Screenshots")
            os.makedirs(temp_dir, exist_ok=True)
            result = subprocess.run(
                [flameshot, "full", "-c", "-p", temp_dir],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0

        raise RuntimeError("flameshot not found. Install with: sudo apt install flameshot")

    def _which(self, cmd: str) -> Optional[str]:
        """Find command in PATH."""
        import shutil
        return shutil.which(cmd)

    def run(self) -> None:
        """Start the widget."""
        self.root.mainloop()


def main() -> int:
    """Entry point."""
    try:
        widget = ScreenshotWidget()
        widget.run()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
