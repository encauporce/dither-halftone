#!/usr/bin/env bash
# ==============================================================================
# One-Click ADB Deployment Script for Dither Halftone (抖动网点)
# Targets: macOS / Linux / Git Bash
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SHADER_DIR="/sdcard/mpv/shaders"
TARGET_CONFIG_DIR="/sdcard/mpv"

echo -e "\033[1;36m======================================================================\033[0m"
echo -e "\033[1;36m 抖动网点 (Dither Halftone) - ADB 部署脚本 (Bash) \033[0m"
echo -e "\033[1;36m======================================================================\033[0m"

# 1. Check ADB
if ! command -v adb &> /dev/null; then
    echo -e "\033[1;31m[-] Error: 'adb' command not found in PATH!\033[0m"
    echo "Please install Android platform-tools and ensure adb is accessible."
    exit 1
fi

# 2. Check Device
DEVICES=$(adb devices | grep -w "device" || true)
if [ -z "$DEVICES" ]; then
    echo -e "\033[1;33m[!] No authorized Android device detected via ADB!\033[0m"
    echo "Please verify:"
    echo "  1. Developer options and USB debugging are enabled on your Hisense A7."
    echo "  2. The phone screen is unlocked and ADB authorization prompt is accepted."
    echo "  3. USB cable is firmly connected or wireless debugging is active."
    exit 1
fi

DEVICE_ID=$(echo "$DEVICES" | head -n 1 | awk '{print $1}')
echo -e "\033[1;32m[+] Connected device detected: ${DEVICE_ID}\033[0m"

# 3. Create Remote Directories
echo -e "\033[1;33m[*] Creating remote directories on device...\033[0m"
adb -s "${DEVICE_ID}" shell "mkdir -p ${TARGET_SHADER_DIR}"

# 4. Push halftone.glsl
if [ ! -f "${SCRIPT_DIR}/halftone.glsl" ]; then
    echo -e "\033[1;31m[-] Error: ${SCRIPT_DIR}/halftone.glsl not found!\033[0m"
    exit 1
fi

echo -e "\033[1;33m[*] Pushing halftone.glsl to ${TARGET_SHADER_DIR}/halftone.glsl ...\033[0m"
adb -s "${DEVICE_ID}" push "${SCRIPT_DIR}/halftone.glsl" "${TARGET_SHADER_DIR}/halftone.glsl"

# 5. Push mpv.conf if present
if [ -f "${SCRIPT_DIR}/mpv.conf" ]; then
    echo -e "\033[1;33m[*] Pushing mpv.conf to ${TARGET_CONFIG_DIR}/mpv.conf ...\033[0m"
    adb -s "${DEVICE_ID}" push "${SCRIPT_DIR}/mpv.conf" "${TARGET_CONFIG_DIR}/mpv.conf"
fi

# 6. Verify
echo -e "\033[1;33m[*] Verifying remote files...\033[0m"
adb -s "${DEVICE_ID}" shell "ls -l ${TARGET_SHADER_DIR}/halftone.glsl"

echo -e "\033[1;32m======================================================================\033[0m"
echo -e "\033[1;32m [SUCCESS] DeepInk Shader deployed successfully to your Hisense A7!\033[0m"
echo -e " Open mpv-android on your phone and play any video to experience it!"
echo -e "\033[1;32m======================================================================\033[0m"
