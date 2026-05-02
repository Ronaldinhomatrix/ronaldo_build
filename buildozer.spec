[app]
title = Ronaldo Medeiros
package.name = ronaldomedeirosfisiologista
package.domain = com.operantlab
source.dir = .
source.include_exts = py,ttf,TTF,png,jpg,mp4,json
source.exclude_dirs = p4a_recipes,painel,.git,bin
icon.filename = %(source.dir)s/icon_rm.png
version = 3.15

# Requirements limpos - removendo p4a-ffmpeg se existir para usar player nativo
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,certifi,openssl,sqlite3,requests,android,pyasn1,idna,charset-normalizer,pyjnius

# Garante que o Android use o backend nativo
android.video_player = mediaplayer

orientation = portrait
fullscreen = 0
# Permissões para API 34
android.permissions = INTERNET,READ_MEDIA_VIDEO,POST_NOTIFICATIONS
android.release_artifact = apk

android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
