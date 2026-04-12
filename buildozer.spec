[app]
title = Ronaldo Medeiros Fisiologista
package.name = ronaldomedeirosfisiologista
package.domain = com.operantlab
source.dir = .
source.include_exts = py,ttf,png,jpg
# Excluir fontes sensíveis do APK (compilados via Cython para .so)
source.exclude_patterns = firebase_sync.py,firebase_config.py
icon.filename = %(source.dir)s/icon_rm.png
version = 2.4

requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,certifi,ffpyplayer,firebase_sync,firebase_config

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
cython = ~/.local/share/pipx/venvs/buildozer/bin/cython
p4a.local_recipes = ./p4a_recipes

[app:android]
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = apk

# Proteção: obfusca a camada Java do wrapper
android.enable_proguard = True

# Proteção: remove símbolos de debug das bibliotecas nativas
android.strip = True

# Proteção: desativa logs em produção
android.logcat_filters = *:S
