<div dir="rtl">

# ItayPhone 📱

סמארטפון DIY מבוסס **Raspberry Pi 5** עם מערכת ופיצ'רים משלנו.

- **חומרה:** Pi 5 (8GB) + Waveshare SIM7600G-H 4G HAT + מסך DSI 5" מגע + UPS X1202 (סוללה) + Camera Module 3.
- **תוכנה:** Raspberry Pi OS (64-bit) + ממשק Python/Kivy שאנחנו כותבים + **Waydroid** (אנדרואיד בקונטיינר לאפליקציות כמו וואטסאפ).
- **תקשורת:** שיחות, SMS ודאטה דרך ה-SIM7600 בעזרת פקודות AT.

ראה `PLAN.md` לתכנון המלא ו-`SHOPPING_LIST.md` לרשימת הרכיבים.

## מבנה הפרויקט

```
src/itayphone/
  main.py            # נקודת כניסה (תומך ב---mock להרצה בלי חומרה)
  config.py          # הגדרות
  modem/             # שכבת התקשורת הסלולרית
    transport.py     #   שכבת AT גולמית (serial) + Mock לבדיקות
    sim7600.py       #   ממשק high-level: שיחות, SMS, רשת
    models.py        #   מבני נתונים: SMS, Call, NetworkStatus
  ui/                # ממשק Kivy
    app.py
    screens/         #   מסך בית, חייגן, הודעות
  contacts/          # אחסון אנשי קשר
tests/               # בדיקות (רצות בלי חומרה, עם Mock)
install.sh           # התקנה על Raspberry Pi OS
```

## הרצה מהירה (בלי חומרה — מצב Mock)

```bash
pip install -r requirements.txt
python -m itayphone.main --mock
```

מצב Mock מדמה את ה-SIM7600, כך שאפשר לפתח ולבדוק את הלוגיקה והממשק עוד לפני שהחומרה מגיעה.

## הרצה על החומרה (Raspberry Pi)

```bash
sudo ./install.sh
python -m itayphone.main --port /dev/ttyUSB2
```

## סטטוס

✅ שלד התוכנה נבנה ונבדק (7/7 בדיקות עוברות, `--mock --demo` עובד).
🚧 ממתינים לרכיבים → הרכבה → bring-up → הרחבת הממשק.

</div>
