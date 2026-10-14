[app]
title = Arise
package.name = arise
package.domain = org.arise
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = .github,bin,.buildozer,java,res
version = 0.1.0
requirements = python3,kivy==2.3.0,pyjnius,android,plyer,openssl,certifi
orientation = portrait
fullscreen = 0

android.permissions = INTERNET,SEND_SMS,CALL_PHONE,QUERY_ALL_PACKAGES,VIBRATE,ACTIVITY_RECOGNITION,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION
# pin python-for-android to a stable release (Python 3.11) - master now builds Python 3.14
p4a.branch = v2024.01.21
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.add_src = java
android.add_resources = res/xml:xml

[buildozer]
log_level = 2
warn_on_root = 1
