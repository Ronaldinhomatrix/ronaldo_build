[app]
title = Ronaldo Medeiros
package.name = ronaldo_medeiros
package.domain = com.ronaldomedeiros
source.dir = .
source.include_exts = py,ttf,TTF,png,jpg,mp4,json
source.exclude_dirs = p4a_recipes,painel,.git,bin
icon.filename = %(source.dir)s/icon_rm.png
version = 1.2

# Requirements limpos: Removido ffpyplayer para usar o motor nativo do celular
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,certifi,openssl,sqlite3,requests,android,pyasn1,idna,charset-normalizer

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_VIDEO
android.release_artifact = apk

# API 31 para estabilidade máxima na abertura do app
android.api = 31
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
