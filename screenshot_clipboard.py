#!/usr/bin/env python3

import datetime
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Optional

try:
    import fcntl  # type: ignore[import]
except ImportError:  # pragma: no cover
    fcntl = None


class ScreenshotAutomation:
    def __init__(self) -> None:
        self.temp_dir = os.path.expanduser("~/Pictures/Screenshots")
        self.log_file = os.path.expanduser("~/.screenshot_automation.log")
        self.retention_hours = 24
        self.lock_file = os.path.expanduser("~/.screenshot_automation.lock")
        self.lock_handle = None
        self.desktop_env = None
        self.flameshot_path = None
        self.xclip_path = None
        self.logger = self._create_logger()

    def _create_logger(self) -> logging.Logger:
        logger = logging.getLogger("screenshot_automation")
        if logger.handlers:
            return logger
        logger.setLevel(logging.INFO)
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def run(self) -> int:
        start = time.time()
        self.logger.info("run_start platform=%s", sys.platform)
        if not sys.platform.startswith("linux"):
            self.logger.error("unsupported_platform platform=%s", sys.platform)
            return 10
        self.desktop_env = self.detect_desktop_environment()
        if self.desktop_env:
            self.logger.info("desktop_environment=%s", self.desktop_env)
        else:
            self.logger.info("desktop_environment=unknown")
        try:
            self.acquire_lock()
        except RuntimeError as exc:
            self.logger.error("lock_failed error=%s", exc)
            return 11
        try:
            code = self.validate_dependencies()
            if code != 0:
                return code
            self.ensure_temp_dir()
            path = self.capture_screenshot()
            if not path:
                return 20
            self.logger.info("screenshot_saved path=%s", path)
            self.copy_to_clipboard(path)
            self.cleanup_old_screenshots()
            elapsed = time.time() - start
            self.logger.info("run_complete seconds=%.3f", elapsed)
            return 0
        finally:
            self.release_lock()

    def detect_desktop_environment(self) -> Optional[str]:
        candidates = [
            os.environ.get("XDG_CURRENT_DESKTOP"),
            os.environ.get("DESKTOP_SESSION"),
            os.environ.get("GDMSESSION"),
        ]
        for value in candidates:
            if value:
                return value
        return None

    def validate_dependencies(self) -> int:
        self.flameshot_path = shutil.which("flameshot")
        if not self.flameshot_path:
            self.logger.error("missing_dependency name=flameshot")
            return 1
        self.logger.info("dependency_ok name=flameshot path=%s", self.flameshot_path)
        self.xclip_path = shutil.which("xclip")
        if not self.xclip_path:
            self.logger.warning("missing_dependency name=xclip using_flameshot_clipboard_only=true")
        else:
            self.logger.info("dependency_ok name=xclip path=%s", self.xclip_path)
        python_path = sys.executable
        self.logger.info("runtime_python path=%s", python_path)
        return 0

    def ensure_temp_dir(self) -> None:
        os.makedirs(self.temp_dir, exist_ok=True)
        self.logger.info("temp_dir_ready path=%s", self.temp_dir)

    def capture_screenshot(self) -> str | None:
        if not self.flameshot_path:
            self.logger.error("capture_error reason=no_flameshot_path")
            return None
        start_time = time.time()
        cmd = [
            self.flameshot_path,
            "full",
            "-c",
            "-p",
            self.temp_dir,
        ]
        self.logger.info("capture_command cmd=%s", " ".join(cmd))
        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.logger.error("capture_error reason=timeout seconds=5")
            return None
        stdout_text = completed.stdout.decode(errors="ignore").strip()
        stderr_text = completed.stderr.decode(errors="ignore").strip()
        if completed.returncode != 0:
            self.logger.error(
                "capture_error reason=flameshot_failed code=%s stderr=%s stdout=%s",
                completed.returncode,
                stderr_text,
                stdout_text,
            )
            return None
        path = self._find_latest_screenshot(start_time)
        if not path:
            self.logger.warning("capture_warning reason=no_file_detected directory=%s", self.temp_dir)
            return None
        return path

    def _find_latest_screenshot(self, min_mtime: float) -> Optional[str]:
        latest_path = None
        latest_mtime = 0.0
        try:
            entries = list(os.scandir(self.temp_dir))
        except FileNotFoundError:
            return None
        for entry in entries:
            if not entry.is_file():
                continue
            name = entry.name.lower()
            if not (name.endswith(".png") or name.endswith(".jpg") or name.endswith(".jpeg")):
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime < min_mtime:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_path = entry.path
        return latest_path

    def copy_to_clipboard(self, path: str) -> None:
        if not path:
            return
        if not self.xclip_path:
            self.logger.info("clipboard_info xclip_present=false using_flameshot_clipboard_only=true")
            return
        cmd = [
            self.xclip_path,
            "-selection",
            "clipboard",
            "-t",
            "image/png",
            "-i",
            path,
        ]
        self.logger.info("clipboard_command cmd=%s", " ".join(cmd))
        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.logger.warning("clipboard_warning reason=timeout seconds=3")
            return
        stdout_text = completed.stdout.decode(errors="ignore").strip()
        stderr_text = completed.stderr.decode(errors="ignore").strip()
        if completed.returncode != 0:
            self.logger.warning(
                "clipboard_warning reason=xclip_failed code=%s stderr=%s stdout=%s",
                completed.returncode,
                stderr_text,
                stdout_text,
            )
        else:
            self.logger.info("clipboard_success provider=xclip")

    def cleanup_old_screenshots(self) -> None:
        now = time.time()
        cutoff = now - float(self.retention_hours) * 3600.0
        removed = 0
        try:
            entries = list(os.scandir(self.temp_dir))
        except FileNotFoundError:
            return
        for entry in entries:
            if not entry.is_file():
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime >= cutoff:
                continue
            try:
                os.remove(entry.path)
                removed += 1
            except OSError as exc:
                self.logger.warning("cleanup_warning path=%s error=%s", entry.path, exc)
        if removed:
            self.logger.info("cleanup_complete removed=%d", removed)

    def acquire_lock(self) -> None:
        lock_dir = os.path.dirname(self.lock_file)
        if lock_dir and not os.path.isdir(lock_dir):
            os.makedirs(lock_dir, exist_ok=True)
        self.lock_handle = open(self.lock_file, "w")
        try:
            if fcntl is not None:
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            try:
                self.lock_handle.close()
            finally:
                self.lock_handle = None
            raise RuntimeError(str(exc))
        self.lock_handle.write(str(os.getpid()))
        self.lock_handle.flush()
        self.logger.info("lock_acquired path=%s", self.lock_file)

    def release_lock(self) -> None:
        if not self.lock_handle:
            return
        try:
            if fcntl is not None:
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            self.lock_handle.close()
        except OSError:
            pass
        self.lock_handle = None
        self.logger.info("lock_released path=%s", self.lock_file)


def main() -> int:
    app = ScreenshotAutomation()
    try:
        code = app.run()
    except Exception as exc:  # pragma: no cover
        logger = getattr(app, "logger", None)
        if isinstance(logger, logging.Logger):
            logger.exception("unhandled_exception error=%s", exc)
        else:
            sys.stderr.write(f"unhandled_exception: {exc}\n")
        code = 99
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
