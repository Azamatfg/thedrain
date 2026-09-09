#!/usr/bin/env bash
# thedrain installer.  Usage:
#   curl -fsSL https://raw.githubusercontent.com/Azamatfg/thedrain/main/install.sh | bash
set -euo pipefail

REPO="Azamatfg/thedrain"
DEST="${THEDRAIN_HOME:-$HOME/.thedrain}"
BIN_DIR="${THEDRAIN_BIN:-$HOME/.local/bin}"
GREEN=$'\033[38;5;118m'; DIM=$'\033[2m'; RED=$'\033[38;5;203m'; R=$'\033[0m'

say()  { printf "%s\n" "$*"; }
ok()   { printf "  ${GREEN}✓${R} %s\n" "$*"; }
die()  { printf "  ${RED}✗${R} %s\n" "$*" >&2; exit 1; }

printf "\n  ${GREEN}thedrain${R} ${DIM}— what Claude did for you today${R}\n\n"

command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.9+ and retry."
PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)' \
  || die "python3 $PYV found, 3.9+ required."
ok "python3 $PYV"

command -v git >/dev/null 2>&1 || die "git not found."

if [ -d "$DEST/.git" ]; then
  git -C "$DEST" pull --quiet --ff-only && ok "updated $DEST"
else
  rm -rf "$DEST"
  git clone --quiet --depth 1 "https://github.com/$REPO.git" "$DEST" \
    || die "could not clone https://github.com/$REPO"
  ok "installed to $DEST"
fi

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/drain" <<SH
#!/usr/bin/env bash
exec python3 "$DEST/drain.py" "\$@"
SH
chmod +x "$BIN_DIR/drain"
ok "command 'drain' → $BIN_DIR/drain"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    printf "\n  ${DIM}%s is not on your PATH. Add it:${R}\n" "$BIN_DIR"
    printf "    echo 'export PATH=\"%s:\$PATH\"' >> ~/.zshrc && source ~/.zshrc\n" "$BIN_DIR"
    ;;
esac

printf "\n  ${DIM}run it:${R}  drain\n\n"
