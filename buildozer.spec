[app]
title = Ronaldo Medeiros
package.name = ronaldo_medeiros
package.domain = com.ronaldomedeiros
source.dir = .
source.include_exts = py,ttf,TTF,png,jpg,mp4,json,xml
source.exclude_dirs = p4a_recipes,painel,.git,bin
icon.filename = %(source.dir)s/icon_rm.png
version = 3.18

# Requirements: removido pyobjus que causava erro no build Android
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,certifi,openssl,sqlite3,requests,android,pyasn1,idna,charset-normalizer,pyjnius,urllib3,plyer

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_VIDEO,POST_NOTIFICATIONS

# Configuração do FileProvider para o Android
android.add_src = xml
android.manifest.application_extra_xml = xml/file_paths.xml
android.release_artifact = apk
android.api = 34
android.minapi = 21
android.ndk = 25b

# Compilando para arquiteturas modernas
android.archs = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
