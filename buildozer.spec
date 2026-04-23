[app]
title = Ronaldo Medeiros
package.name = ronaldo_medeiros
package.domain = com.ronaldomedeiros
source.dir = .
source.include_exts = py,ttf,png,jpg,mp4,json
source.exclude_dirs = p4a_recipes,painel,.git,bin
icon.filename = %(source.dir)s/icon_rm.png
version = 1.1

# Adicionado 'android' e 'pyasn1' para estabilidade e SSL
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,certifi,ffpyplayer,ffmpeg,openssl,sqlite3,requests,urllib3,android,pyasn1

orientation = portrait
fullscreen = 0
# Permissões atualizadas
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_VIDEO
android.release_artifact = apk

android.api = 31
android.minapi = 21
android.ndk = 25b
# Incluindo ambas para compatibilidade total
android.archs = armeabi-v7a, arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
