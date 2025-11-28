#!/usr/bin/env bash
set -euo pipefail

RAW_BASE="https://raw.githubusercontent.com/qaaph-zyld/screenshot_tool/main"
PY_SCRIPT_NAME="screenshot_clipboard.py"
TARGET_PATH="/usr/local/bin/screenshot-automate"

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

detect_distro() {
  if [ -r /etc/os-release ]; then
    . /etc/os-release
    if [ "${ID_LIKE:-}" != "" ]; then
      echo "$ID $ID_LIKE"
    else
      echo "$ID"
    fi
  else
    echo ""
  fi
}

install_packages() {
  local need_flameshot=0
  local need_xclip=0
  local need_python=0
  if ! command_exists flameshot; then
    need_flameshot=1
  fi
  if ! command_exists xclip; then
    need_xclip=1
  fi
  if ! command_exists python3; then
    need_python=1
  fi
  if [ "$need_flameshot" -eq 0 ] && [ "$need_xclip" -eq 0 ] && [ "$need_python" -eq 0 ]; then
    return 0
  fi
  local info
  info="$(detect_distro)"
  if echo "$info" | grep -qiE 'debian|ubuntu'; then
    $SUDO apt-get update -y
    local pkgs=""
    if [ "$need_flameshot" -eq 1 ]; then
      pkgs="$pkgs flameshot"
    fi
    if [ "$need_xclip" -eq 1 ]; then
      pkgs="$pkgs xclip"
    fi
    if [ "$need_python" -eq 1 ]; then
      pkgs="$pkgs python3"
    fi
    if [ -n "$pkgs" ]; then
      $SUDO apt-get install -y $pkgs
    fi
  elif echo "$info" | grep -qiE 'fedora|rhel|centos'; then
    local pkgs=""
    if [ "$need_flameshot" -eq 1 ]; then
      pkgs="$pkgs flameshot"
    fi
    if [ "$need_xclip" -eq 1 ]; then
      pkgs="$pkgs xclip"
    fi
    if [ "$need_python" -eq 1 ]; then
      pkgs="$pkgs python3"
    fi
    if [ -n "$pkgs" ]; then
      $SUDO dnf install -y $pkgs
    fi
  elif echo "$info" | grep -qi 'arch'; then
    local pkgs=""
    if [ "$need_flameshot" -eq 1 ]; then
      pkgs="$pkgs flameshot"
    fi
    if [ "$need_xclip" -eq 1 ]; then
      pkgs="$pkgs xclip"
    fi
    if [ "$need_python" -eq 1 ]; then
      pkgs="$pkgs python"
    fi
    if [ -n "$pkgs" ]; then
      $SUDO pacman -Sy --noconfirm $pkgs
    fi
  else
    echo "Unsupported or unknown distribution. Install flameshot, xclip, and python3 manually."
  fi
}

download_script() {
  curl -fsSL "$RAW_BASE/$PY_SCRIPT_NAME" -o "/tmp/$PY_SCRIPT_NAME"
}

install_script() {
  $SUDO mv "/tmp/$PY_SCRIPT_NAME" "$TARGET_PATH"
  $SUDO chmod +x "$TARGET_PATH"
}

main() {
  install_packages
  download_script
  install_script
  echo "Installed screenshot automation to $TARGET_PATH"
  echo "Configure your desktop environment to map Ctrl+1 to $TARGET_PATH"
}

main "$@"
