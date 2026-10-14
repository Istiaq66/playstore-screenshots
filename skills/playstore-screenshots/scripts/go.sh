#!/bin/sh
# Run input actions on the device, then capture the screen.
#   go.sh <out.png> [action]...
# Actions:  tap X Y | swipe X1 Y1 X2 Y2 | text "words here" | back | hidekb | wait SECS
# Writes <out.png> (full 1080x1920) and <dir of out>/peek.png (360x640 preview to Read;
# multiply preview coordinates by 3 to get tap coordinates).
# Env: ADB, SERIAL, PY (python command; default `python`).
ADB=${ADB:-/c/Users/$USERNAME/AppData/Local/Android/Sdk/platform-tools/adb.exe}
[ -x "$ADB" ] || ADB=adb
[ -n "$SERIAL" ] && ADB="$ADB -s $SERIAL"
PY=${PY:-python}
export MSYS_NO_PATHCONV=1
HERE=$(cd "$(dirname "$0")" && pwd)
winpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else echo "$1"; fi; }

out=$1; shift
[ -z "$out" ] && { echo "usage: go.sh <out.png> [tap X Y|swipe X1 Y1 X2 Y2|text STR|back|hidekb|wait S]..."; exit 1; }
mkdir -p "$(dirname "$out")"
while [ $# -gt 0 ]; do
  case $1 in
    tap)    $ADB shell input tap "$2" "$3"; shift 3; sleep 3 ;;
    swipe)  $ADB shell input swipe "$2" "$3" "$4" "$5" 600; shift 5; sleep 2 ;;
    text)   $ADB shell input text "$(printf %s "$2" | sed 's/ /%s/g')"; shift 2; sleep 1 ;;
    back)   $ADB shell input keyevent 4; shift; sleep 2 ;;
    hidekb) $ADB shell input keyevent 111; shift; sleep 1 ;;
    wait)   sleep "$2"; shift 2 ;;
    *) echo "unknown action: $1"; exit 1 ;;
  esac
done
$ADB exec-out screencap -p > "$out"
"$PY" -I "$(winpath "$HERE/sheet.py")" "$(winpath "$(dirname "$out")/peek.png")" "$(winpath "$out")"
