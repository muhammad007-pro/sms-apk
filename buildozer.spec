[app]
title = SMS AutoSender
package.name = sms_autosender
package.domain = org.uz.sms
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xlsx,xls,csv
version = 0.1
requirements = python3,kivy,pandas,openpyxl,jnius,android,numpy

orientation = portrait
fullscreen = 0
android.permissions = SEND_SMS, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, RECEIVE_SMS

# Muhim: NDK va API versiyalarini barqarorlashtirish
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_path = 
android.sdk_path = 

# Grafik va arxitektura
android.archs = armeabi-v7a, arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
