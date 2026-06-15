[app]
title = My Awesome App
package.name = asapp
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3, kivy==2.3.0, kivymd==1.2.0, requests, pillow, materialyoucolor, exceptiongroup, asyncgui, asynckivy
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.api = 34
android.minapi = 24
android.ndk_api = 24
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
