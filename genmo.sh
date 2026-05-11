#!/usr/bin/env bash
#example usage: ./genmo.sh en_US

set -euo pipefail

CMD="msgfmt"

if ! command -v "$CMD" >/dev/null 2>&1; then
  echo "$CMD not found. Attempting to install gettext..."

  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y gettext
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y gettext
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y gettext
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm gettext
  else
    echo "No supported package manager found (apt, dnf, yum, pacman). Please install 'gettext' manually." >&2
    exit 2
  fi

  if ! command -v "$CMD" >/dev/null 2>&1; then
    echo "Installation failed or $CMD still not found." >&2
    exit 3
  fi

  echo "$CMD installed successfully: $(command -v $CMD)"
fi


DOMAIN="prod"
INFNAME="$DOMAIN.po"
OUTFNAME="$DOMAIN.mo"

LOCALE=$1
if [[ -z $LOCALE ]]; then LOCALE=$(locale|grep LANGUAGE|cut -d= -f2|cut -d: -f1); fi

DIR="locale/$LOCALE/LC_MESSAGES"

INFILE="$DIR/$INFNAME"

OUTFILE="$DIR/$OUTFNAME"

[ -d $DIR ] || mkdir -p $DIR

ARGS=("--directory=$DIR" "--output-file=$OUTFILE" "$INFNAME")

if [ ${#ARGS[@]} -eq 0 ]; then
  echo "No arguments provided for msgfmt. Example usage: $0 -o output.mo input.po" >&2
  exit 4
fi

msgfmt --directory=$DIR --output-file=$OUTFILE $INFNAME
#exec "$CMD" "${ARGS[@]}"
