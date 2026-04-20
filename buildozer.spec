[app]
title = Ronaldo Medeiros Fisiologista
package.name = ronaldomedeirosfisiologista
package.domain = com.operantlab
source.dir = .
source.include_exts = py,ttf,png,jpg
source.exclude_dirs = p4a_recipes,painel,.git,bin
# firebase_sync.py e firebase_config.py incluídos como .py (proteção via Firestore Rules)
icon.filename = %(source.dir)s/icon_rm.png
version = 2.8

requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,certifi,ffpyplayer

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.release_artifact = apk

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

# Assinatura do APK release
android.keystore = /mnt/c/Users/madm/keystore/ronaldo.jks
android.keyalias = ronaldomedeiros
android.keystore_passwd = RonFisio@2024!Mdf
android.keyalias_passwd = RonFisio@2024!Mdf

# Proteção: obfusca a camada Java do wrapper
android.enable_proguard = True

# Proteção: remove símbolos de debug das bibliotecas nativas
android.strip = True

# Proteção: desativa logs em produção
android.logcat_filters = *:S

[buildozer]
log_level = 2
warn_on_root = 1
cython = ~/.local/share/pipx/venvs/buildozer/bin/cython
