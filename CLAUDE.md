<div dir="rtl">

# ItayPhone — מדריך לקלוד

סמארטפון DIY מבוסס Raspberry Pi: ממשק Python/Kivy בעברית (RTL) בעיצוב iOS/אנדרואיד, מודם SIM7600 לשיחות/SMS, ו-Waydroid לאפליקציות אנדרואיד. ראה `README.md`, `PLAN.md`.

## הרצה ופיתוח
- **הרצה ללא חומרה:** `cd src && python3 -m itayphone.main --mock` (מודם מדומה). `--mock --demo` = בדיקת מודם headless.
- **בדיקות:** `python -m pytest -q` מהשורש (לא דורשות Kivy/חומרה).
- **חלון:** borderless בכל הפלטפורמות (ב-Windows גם `SetWindowRgn` לפינות מעוגלות אמיתיות — דרך `Window.get_window_info()`, לא FindWindow). גודל טלפון 360×720.

## מבנה
- `src/itayphone/main.py` — נקודת כניסה, הגדרות חלון, בניית modem/contacts/history/camera/waydroid/system.
- `modem/` — SIM7600 (AT), transport (serial + Mock), models.
- `ui/app.py` — ה-App: ScreenManager + overlays (Control Center, tints, device_frame, home_bar). ניווט: `go(screen)`.
- `ui/theme.py` — **לב העיצוב.** ראה למטה.
- `ui/screens/` — home (launcher iOS), dialer/recents/contacts (סגנון אנדרואיד שחור, טאבים), messages, call, camera, gallery, wifi, bluetooth.
- `contacts/`, `history.py`, `camera.py`, `waydroid.py`, `system.py` (Wi-Fi/BT/בקרה).

## עברית (RTL) — קריטי
Kivy/SDL2 לא עושה bidi. **חובה לעטוף כל מחרוזת עברית ב-`H(...)`** (מ-`theme`) שמריץ את אלגוריתם ה-bidi. ב-markup, לעטוף רק את החלק העברי (לא את התגיות).

## אימוג'י — קריטי
פונט האימוג'י (Noto Color Emoji ב-Pi) הוא **bitmap ולא מתכווץ ב-Kivy** → אימוג'י כטקסט יוצאים ענקיים. לכן: `theme.emoji_image(glyph)` מרנדר אימוג'י כתמונה (Pillow) בגודל נכון. **אל תשים אימוג'י כטקסט-Kivy** — השתמש ב-`emoji_image`/`ios_icon`/`_squircle`. גליפים מונוכרום (⌫ ◀) → פונט `SYM`.

## עיצוב (theme.py)
- פונטים: `FONT`=Heb, `EMOJI` (צבעוני), `SYM` (מונוכרום). מירשמים ב-`apply_theme`.
- `gradient_bg`, `frost` (פאנל מתוסך), `ios_icon` (אריח עם תמונה+כיתוב+badge), `dock`, `top_bar` (כותרת מימין + back משמאל).
- `device_frame` — overlay: רק נקב מצלמה (punch-hole) למעלה; פינות מעוגלות מגיעות מ-SetWindowRgn (Windows) ולא מצוירות שחורות.
- `control_center` — גרירה מלמעלה; פאנל עוקב-אצבע. ה-dim הוא Widget (לא Button! Button מושבת בולע נגיעות).
- `home_bar` — פס בית תחתון (גרירה מלמעלה למעלה = בית).

## Raspberry Pi (חי)
ראה זיכרון: `itayphone-pi-deploy.md`, `itayphone-waydroid.md`, `itayphone-lite-kiosk-plan.md`.
- SSH: `ssh -i /c/Users/moshe/.ssh/itayphone_pi itay@192.168.1.234`. sudo בלי סיסמה. OS: RPi OS (Debian 13/trixie), arm64, Python 3.13, Kivy 2.3.1 (apt).
- פריסה: בונים `itayphone.tar.gz`, scp, `tar -xzf ~/`, מפעילים מחדש.
- הרצת GUI מרחוק: `DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 nohup python3 -m itayphone.main --mock`.
- **Waydroid:** מותקן; GPU+binder עובדים. lineage-20 קורס ב-init (mutex/codec @ phase 550) → מעבר ל-lineage-18.1. הרצת session = systemd user service. אימוג'י/אפליקציות: `~/apks/*.apk`.
- **תוכנית:** מעבר ל-Pi OS Lite + kiosk (מהירות/RAM).

## עבודה מול הרפו
המשתמש עורך קבצים במקביל — לקרוא קובץ לפני עריכה (הוא משתנה). לשמור עברית בטקסטים. להריץ `pytest` אחרי שינויים.

</div>
