#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/aozocchi/deactra.git"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/deactra"
BIN_DIR="$HOME/.local/bin"
VENV_DIR="$APP_DIR/.venv"

log()  { printf '\033[1;32m[deactra]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 ||
  fail "Git is required. Install Git and run this installer again."

# Find a Python version supported by Deactra.
PYTHON=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' 2>/dev/null; then
    PYTHON="$(command -v "$candidate")"
    break
  fi
done

[[ -n "$PYTHON" ]] || fail "Python 3.10+ is required."

mkdir -p "$(dirname "$APP_DIR")" "$BIN_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
  log "Updating existing checkout..."
  git -C "$APP_DIR" pull --ff-only ||
    fail "Could not update $APP_DIR. Resolve local changes and retry."
elif [[ -e "$APP_DIR" ]]; then
  fail "$APP_DIR exists but is not a Git repository. Move it and retry."
else
  log "Cloning Deactra..."
  git clone "$REPO_URL" "$APP_DIR" ||
    fail "Git clone failed."
fi

log "Using Python: $("$PYTHON" --version)"
log "Creating virtual environment..."

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON" -m venv "$VENV_DIR" ||
    fail "Could not create virtual environment. Install your OS Python venv support."
fi

log "Installing Deactra..."
"$VENV_DIR/bin/python" -m pip install "$APP_DIR" ||
  fail "Package installation failed."

# Do not silently overwrite a real executable owned by another tool.
if [[ -e "$BIN_DIR/deactra" && ! -L "$BIN_DIR/deactra" ]]; then
  fail "$BIN_DIR/deactra already exists and is not a symlink. Back it up first."
fi

ln -sfn "$VENV_DIR/bin/deactra" "$BIN_DIR/deactra"

# Add the command directory to the user's shell PATH.
case "${SHELL##*/}" in
  fish)
    if command -v fish >/dev/null 2>&1; then
      fish -c 'fish_add_path --universal "$HOME/.local/bin"' ||
        log "Add ~/.local/bin to Fish PATH manually if needed."
    fi
    ;;
  bash)
    RC="$HOME/.bashrc"
    touch "$RC"
    grep -Fq '# Deactra PATH' "$RC" ||
      printf '\n# Deactra PATH\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$RC"
    ;;
  zsh)
    RC="$HOME/.zshrc"
    touch "$RC"
    grep -Fq '# Deactra PATH' "$RC" ||
      printf '\n# Deactra PATH\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$RC"
    ;;
  *)
    log "Add $BIN_DIR to your shell PATH if it is not already present."
    ;;
esac

export PATH="$BIN_DIR:$PATH"

log "Installation complete!"
if command -v deactra >/dev/null 2>&1; then
  deactra --version || deactra --help
else
  log "Open a new terminal, then run: deactra --help"
fi
