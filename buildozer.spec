[app]
title = Ronaldo Medeiros
package.name = ronaldo_medeiros
package.domain = com.ronaldomedeiros
# Extensões de arquivos incluídos
source.include_exts = py,ttf,TTF,png,jpg,mp4,json,xml

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
# Deixa o Kivy escolher o melhor player nativo disponível
# No Android ele usará o 'android', no iOS o 'avplayer'
# android.video_player = mediaplayer

[buildozer]
log_level = 2
warn_on_root = 1
