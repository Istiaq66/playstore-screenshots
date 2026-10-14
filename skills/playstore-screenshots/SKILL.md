---
name: playstore-screenshots
description: Capture an Android app's screens from an emulator or device and turn them into captioned Google Play Store phone screenshots (1080x1920, brand-colored background, bold caption above an inset screen running off the bottom edge — the Subh Warrior style). Use this whenever the user wants Play Store / store listing screenshots, "screenshots for the playstore", marketing screenshots, captioned phone mockups, or wants to redo/refresh store screenshots for a Flutter or native Android app, even if they only say "take screenshots of the app like <other app>".
---

# Play Store screenshots

Produces two sets in the app repo:

```
store/screenshots/phone/            raw 1080x1920 captures
store/screenshots/phone-captioned/  upload these to Play Console
```

Scripts live in this skill's `scripts/` folder. `SK` below means this skill's base directory (shown when the skill loads; for a plugin install it sits in the plugin cache). Call scripts by absolute path. They are POSIX sh + Python 3 with Pillow (`python -m pip install pillow` if missing). On Windows run them from the Bash tool (Git Bash), and pass paths to Windows Python through `cygpath -w`.

## 0. Start the token meter

Run this from the app repo before anything else, so the final report covers only this run:

```sh
python -I $SK/scripts/tokens.py start
```

## 1. Look before touching anything

- `adb devices` — need one running emulator/device. If none, list AVDs (`emulator -list-avds`) and ask which to boot.
- Confirm the app is installed and current. If the repo has commits newer than the installed build (`dumpsys package <id> | grep lastUpdateTime`), offer to rebuild/install first.
- Find brand colors in the code (theme / color constants). Background = the strongest brand color, caption = a high-contrast color from the palette, decor circle = caption color or an accent. A dark app on a dark background loses the screen edge, so prefer the bright brand color as the background.
- If an earlier store set exists (`store/`, `fastlane/`, a sibling project's `store/screenshots`), read a couple of images to match its style and captions tone.

## 2. Ask about the data shown

Screenshots go public. Launch the app, capture the home screen, and look: whose name, email, photos, weight/BMI, empty states? Ask the user once whether to use the signed-in account as-is, a fresh demo account seeded with realistic data, or tidy the current account. Don't change their real data without that answer. Whatever they pick, leave out screens that show an email address, phone number, or other personal identifiers (Profile/Settings/Account) unless they ask for them.

## 3. Prepare the device

```sh
sh $SK/scripts/device.sh setup 0925     # 1080x1920 + demo status bar at 9:25
```

This clears notifications (leftover icons like a missed call otherwise stay in the status bar), shows full wifi + battery, hides the mobile-data icon. Relaunch the app afterwards (`am force-stop` then `monkey -p <id> -c android.intent.category.LAUNCHER 1`) and wait ~8 s for the splash before tapping, so the layout reflows to the new size.

## 4. Navigate and capture

```sh
sh $SK/scripts/go.sh <scratch>/raw/home.png
sh $SK/scripts/go.sh <scratch>/raw/diary.png tap 323 1725
sh $SK/scripts/go.sh <scratch>/raw/search.png tap 450 370 text "bench press" hidekb
```

Each call runs the actions, saves the full capture, and writes `peek.png` (360x640) next to it. Read `peek.png`, not the full image, to save context; **multiply peek coordinates by 3** for the next tap.

Things that bit last time:
- `uiautomator dump` fails on Flutter apps with any looping animation ("could not get idle state"). Navigate by coordinates from peeks instead.
- The hardware Back key can skip screens or drop out of the app to whatever was open before. Tap the app's on-screen back arrow.
- Starting flows (a workout, a checkout) may persist drafts. Prefer flows you can back out of, and tell the user what state you left behind.
- Network features (AI chat, App Check, payments) often fail on emulators ("Couldn't verify this app with Google" = App Check without a debug token). Don't ship an error screen; drop that shot and mention why.
- Entering a little realistic input (weights on sets, a search term) makes a screen read much better than defaults like "BW" or empty lists.

Pick at most **8** screens (Play's phone limit), strongest first: the home/dashboard, the core action (logging, tracking), something visual (library, detail), progress/streaks. Tell a story; skip settings, legal, and login screens.

Copy the chosen captures into `store/screenshots/phone/NN-name.png`.

## 5. Caption and compose

Write captions: 2–6 words, benefit-first, sentence case, no trailing period, at most two lines (e.g. "Track every set with a rest timer", "Log meals in seconds"). Only claim what the screen or code proves (count items rather than guessing "1000+").

Write a spec and render:

```json
{"out": "<repo>/store/screenshots/phone-captioned",
 "background": "#BBF247", "text": "#151515", "decor": "#151515",
 "shots": [{"name": "01-home", "file": "<repo>/store/screenshots/phone/01-home.png", "caption": "Your whole day at a glance"}]}
```

```sh
python -I $SK/scripts/compose.py spec.json      # Windows python: pass paths via `cygpath -w`
```

`font` is optional (defaults to bundled Plus Jakarta Sans ExtraBold, OFL). `decor` may be `null`. The script prints size, KB and any problem (caption too long, image too narrow/short). Output is RGB PNG with no alpha, which Play accepts.

Review all outputs with `python $SK/scripts/sheet.py sheet.png f1.png f2.png ...` (contact sheet of up to ~4 per image) and Read the sheet. Fix captions that wrap badly or screens that look empty.

## 6. Restore and report

```sh
sh $SK/scripts/device.sh restore
python -I $SK/scripts/tokens.py report      # from the same directory as `start`
```

`tokens.py` reads the Claude Code session log (subagents included) and prints calls, input, cache write, cache read and output tokens per model, with the cost at API list prices. Put its table in the report. On a Claude subscription nothing is billed per token, so call the figure the API-equivalent cost. If a model shows "no price", say the total leaves it out.

Tell the user: the token and cost table, where the files are, which screens were chosen and why, which were skipped (personal data, errors), anything left on the device (drafts, logged data), and data caveats (e.g. a "0%" progress ring or "overweight" label visible). Don't commit store images unless asked — some repos deliberately keep them untracked.
