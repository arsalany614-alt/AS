[app]

# (str) Title of your application
title = SENTRA AS

# (str) Package name
package.name = sentra_as

# (str) Package domain (needed for android packaging)
package.domain = org.sentra

# (str) Source code directory
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,wav,mp4,db

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.jpg

# (list) List of directory to exclude
#source.exclude_dirs = tests, bin, venv, .git

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,kivymd,cryptography

# (str) Supported orientations (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = DeclaredName:object_to_enter_in_service_path

#
# Android specific
#

# (list) Android permissions
android.permissions = RECORD_AUDIO, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 21

# (bool) Use --private data directory (True, default) or --dir public directory (False)
android.private_storage = True

# (list) Android architectures to build for (e.g. armeabi-v7a, arm64-v8a, x86, x86_64)
android.archs = armeabi-v7a, arm64-v8a

# (bool) Allow backup of app data
android.allow_backup = True

#
# Python for android (p4a) specific
#

# (str) The directory where buildozer will store the final APK
bin_dir = ./bin

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = false, 1 = true)
warn_on_root = 1
