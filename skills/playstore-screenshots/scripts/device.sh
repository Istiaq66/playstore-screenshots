#!/bin/sh
# Prepare or restore an Android emulator/device for store screenshots.
#   device.sh setup [hhmm]   1080x1920 screen, clean demo status bar (clock, full wifi + battery, no notifications)
#   device.sh restore        undo both
# Env: ADB (path to adb; default: Android SDK on Windows, else `adb`), SERIAL (optional device serial).
ADB=${ADB:-/c/Users/$USERNAME/AppData/Local/Android/Sdk/platform-tools/adb.exe}
[ -x "$ADB" ] || ADB=adb
[ -n "$SERIAL" ] && ADB="$ADB -s $SERIAL"
export MSYS_NO_PATHCONV=1   # Git Bash would otherwise rewrite /sdcard-style args into Windows paths

demo() { $ADB shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }

case "$1" in
  setup)
    $ADB shell wm size 1080x1920
    $ADB shell service call notification 1 >/dev/null 2>&1   # clear notifications (hides leftover status icons)
    $ADB shell settings put global sysui_demo_allowed 1
    demo exit; demo enter
    demo clock -e hhmm "${2:-0925}"
    demo battery -e level 100 -e plugged false
    demo network -e wifi show -e level 4 -e fully true
    demo network -e mobile hide
    demo notifications -e visible false
    $ADB shell wm size
    ;;
  restore)
    demo exit
    $ADB shell settings put global sysui_demo_allowed 0
    $ADB shell wm size reset
    $ADB shell wm size
    ;;
  *) echo "usage: device.sh setup [hhmm] | restore"; exit 1 ;;
esac
