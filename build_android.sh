#!/bin/bash
# Script de build do APK Android para WSL Ubuntu
# Execute dentro do WSL: bash build_android.sh

set -e

PROJETO_WIN="/mnt/c/Users/madm/ronaldo_build"
PROJETO_WSL="$HOME/ronaldo_build"

echo "=== 1. Copiando projeto para o filesystem Linux ==="
# Preserva .buildozer para não recompilar SDK/NDK do zero a cada build
mkdir -p "$PROJETO_WSL"
rsync -a --delete \
    --exclude='.buildozer' \
    --exclude='bin' \
    --exclude='__pycache__' \
    "$PROJETO_WIN/" "$PROJETO_WSL/"
cd "$PROJETO_WSL"

echo "=== 2. Instalando dependências do sistema ==="
# Garante sudo sem senha para este usuário (evita travar em apt)
echo "$(whoami) ALL=(ALL) NOPASSWD:ALL" | sudo -S tee /etc/sudoers.d/builduser > /dev/null 2>&1 || true
# Aguarda liberação de eventual lock do apt/dpkg
sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock /var/lib/apt/lists/lock 2>/dev/null || true
sudo dpkg --configure -a 2>/dev/null || true
sudo apt-get update -qq
sudo apt-get install -y -qq \
    git zip unzip openjdk-17-jdk \
    python3-pip python3-venv \
    autoconf automake libtool pkg-config \
    libffi-dev libssl-dev libsqlite3-dev \
    libncurses5-dev libncursesw5-dev \
    zlib1g-dev libbz2-dev libreadline-dev \
    ccache

echo "=== 3. Instalando buildozer e cython ==="
export PIP_BREAK_SYSTEM_PACKAGES=1
pip3 install --user --upgrade --break-system-packages buildozer "cython<3.0"

export PATH="$HOME/.local/bin:$PATH"

echo "=== 3b. Criando keystore de release (se não existir) ==="
KEYSTORE_DIR="/mnt/c/Users/madm/keystore"
KEYSTORE_PATH="$KEYSTORE_DIR/ronaldo.jks"
mkdir -p "$KEYSTORE_DIR"
if [ ! -f "$KEYSTORE_PATH" ]; then
    echo "Gerando keystore..."
    keytool -genkey -v \
        -keystore "$KEYSTORE_PATH" \
        -alias ronaldomedeiros \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -storepass "RonFisio@2024!Mdf" \
        -keypass "RonFisio@2024!Mdf" \
        -dname "CN=Ronaldo Medeiros, OU=OperantLab, O=OperantLab, L=Brasil, S=Brasil, C=BR"
    echo "========================================"
    echo "KEYSTORE CRIADA: $KEYSTORE_PATH"
    echo "SENHA: RonFisio@2024!Mdf"
    echo "Guarde esta senha — necessária para atualizar o app no futuro!"
    echo "========================================"
fi

echo "=== 4. Gerando APK (release) ==="
# Remove APKs antigos para garantir que o script copie o correto
rm -f "$PROJETO_WSL/bin/"*.apk
# Força recópia dos arquivos fonte (preserva SDK/NDK/Python compilados)
rm -rf "$PROJETO_WSL/.buildozer/android/app"
buildozer android release

echo "=== 5. Assinando e copiando APK para Windows ==="
UNSIGNED=$(ls -t bin/*.apk 2>/dev/null | head -1)
if [ -z "$UNSIGNED" ]; then
    echo "ERRO: APK não encontrado em bin/"
    exit 1
fi

# Localiza apksigner e zipalign no SDK baixado pelo buildozer
APKSIGNER=$(find ~/.buildozer/android/platform/android-sdk/build-tools -name "apksigner" 2>/dev/null | sort -V | tail -1)
ZIPALIGN=$(find ~/.buildozer/android/platform/android-sdk/build-tools -name "zipalign" 2>/dev/null | sort -V | tail -1)

if [ -z "$APKSIGNER" ]; then
    echo "ERRO: apksigner não encontrado no SDK."
    exit 1
fi

ALIGNED="$PROJETO_WSL/bin/aligned.apk"
SIGNED="$PROJETO_WSL/bin/signed-release.apk"

echo "Alinhando APK..."
"$ZIPALIGN" -f 4 "$UNSIGNED" "$ALIGNED"

echo "Assinando APK com keystore..."
"$APKSIGNER" sign \
    --ks "$KEYSTORE_PATH" \
    --ks-key-alias ronaldomedeiros \
    --ks-pass pass:"RonFisio@2024!Mdf" \
    --key-pass pass:"RonFisio@2024!Mdf" \
    --out "$SIGNED" \
    "$ALIGNED"

rm -f "$ALIGNED"

echo "Verificando assinatura..."
"$APKSIGNER" verify --verbose "$SIGNED" | grep -E "Verified|error" || true

cp "$SIGNED" "$PROJETO_WIN/Instalador/RonaldoMedeirosFisiologista_v2.8.apk"
echo "APK assinado copiado para: C:\Users\madm\ronaldo_build\Instalador\RonaldoMedeirosFisiologista_v2.8.apk"

echo "=== Build concluido com sucesso! ==="
