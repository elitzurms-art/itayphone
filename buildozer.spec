[app]

# --- identity --------------------------------------------------------------
title = ItayPhone
package.name = itayphone
package.domain = org.elitzur
version = 0.1

# --- sources ---------------------------------------------------------------
# The whole project is packaged; main.py at the root is the entry point and
# adds src/ to sys.path. Fonts (ttf) and images ship inside the apk too.
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,wav
source.include_patterns = src/itayphone/assets/*, src/itayphone/assets/fonts/*

# --- python / libs ---------------------------------------------------------
# python-bidi pinned to the last pure-python release (0.5+ is Rust-based and
# changes the API). pyjnius+plyer give us the native Android features.
requirements = python3,kivy==2.3.1,pillow,python-bidi==0.4.2,pyjnius,plyer

# --- presentation ----------------------------------------------------------
orientation = portrait
fullscreen = 1

# --- android ---------------------------------------------------------------
android.permissions = INTERNET, CALL_PHONE, SEND_SMS, CAMERA, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE, BLUETOOTH, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, ACCESS_FINE_LOCATION, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

# Useful Android module bridges for runtime permissions / storage helpers.
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
