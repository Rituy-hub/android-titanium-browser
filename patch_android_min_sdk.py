#!/usr/bin/env python3
import os
import re
import sys


def patch_file(file_path: str, replacements: list) -> bool:
    if not os.path.isfile(file_path):
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = content
    for old_str, new_str in replacements:
        new_content = new_content.replace(old_str, new_str)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Patched SDK version in: {file_path}")
        return True
    return False


def patch_target_sdk_in_gni(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        return False
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = content
    # 1. 替换 min_sdk_version = 34 为 29
    new_content = re.sub(r"min_sdk_version\s*=\s*34", "min_sdk_version = 29", new_content)
    new_content = re.sub(
        r"default_min_sdk_version\s*=\s*34", "default_min_sdk_version = 29", new_content
    )

    # 2. 如果存在 min_sdk_version = 29，但未定义 target_sdk_version = 34，则注入 target_sdk_version = 34
    if "target_sdk_version = 34" not in new_content:
        def inject_target_sdk(match):
            indent = match.group(1)
            return f"{indent}min_sdk_version = 29\n{indent}target_sdk_version = 34"

        new_content = re.sub(
            r"([ \t]*)min_sdk_version\s*=\s*29", inject_target_sdk, new_content
        )

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Patched and injected target_sdk_version = 34 in: {file_path}")
        return True
    return False


def patch_manifest_extract_native_libs(src_dir: str) -> None:
    manifest_path = os.path.join(src_dir, "chrome/android/java/AndroidManifest.xml")
    if not os.path.isfile(manifest_path):
        return
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Android 10 (API 29) throws PackageParserException / "解析软件包时出现问题"
    # if extractNativeLibs="false" but native libraries (.so) inside APK are compressed (Deflate)
    # or not 4KB/16KB aligned. Setting extractNativeLibs="true" allows Android 10 to extract .so
    # to app dir cleanly and bypasses zip alignment/compression parsing rejection.
    new_content = content.replace(
        'android:extractNativeLibs="false"', 'android:extractNativeLibs="true"'
    )
    if new_content != content:
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(
            'Patched AndroidManifest.xml: set android:extractNativeLibs="true" for Android 10 compatibility.'
        )


def main() -> None:
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    key_gni_targets = [
        os.path.join(src_dir, "chrome/android/chrome_public_apk_tmpl.gni"),
        os.path.join(src_dir, "chrome/android/trichrome.gni"),
        os.path.join(src_dir, "android_webview/system_webview_apk_tmpl.gni"),
        os.path.join(src_dir, "vanadium/chromium_src/chrome/android/BUILD.gn"),
    ]

    for gni_file in key_gni_targets:
        patch_target_sdk_in_gni(gni_file)

    # Patch build/config/android/config.gni if default_android_sdk_version is set to higher SDK
    config_gni = os.path.join(src_dir, "build/config/android/config.gni")
    if os.path.isfile(config_gni):
        with open(config_gni, "r", encoding="utf-8") as f:
            cfg = f.read()
        new_cfg = re.sub(
            r"default_android_sdk_version\s*=\s*\d+",
            "default_android_sdk_version = 34",
            cfg,
        )
        if new_cfg != cfg:
            with open(config_gni, "w", encoding="utf-8") as f:
                f.write(new_cfg)
            print(f"Patched default_android_sdk_version to 34 in: {config_gni}")

    # Patch expectations so expectation checking will not fail the build
    expectations_dirs = [
        os.path.join(src_dir, "chrome/android/expectations"),
        os.path.join(src_dir, "android_webview/expectations"),
    ]
    for exp_dir in expectations_dirs:
        if os.path.isdir(exp_dir):
            for root, _, files in os.walk(exp_dir):
                for file_name in files:
                    if file_name.endswith(".expected"):
                        exp_path = os.path.join(root, file_name)
                        with open(exp_path, "r", encoding="utf-8") as f:
                            c = f.read()
                        nc = re.sub(
                            r'android:minSdkVersion="\d+"',
                            'android:minSdkVersion="29"',
                            c,
                        )
                        nc = re.sub(
                            r'android:targetSdkVersion="\d+"',
                            'android:targetSdkVersion="34"',
                            nc,
                        )
                        if nc != c:
                            with open(exp_path, "w", encoding="utf-8") as f:
                                f.write(nc)
                            print(f"Patched AndroidManifest expectations in: {exp_path}")

    # Scan relevant directories dynamically for any remaining hardcoded min/target SDK versions
    scan_dirs = [
        os.path.join(src_dir, "chrome/android"),
        os.path.join(src_dir, "android_webview"),
        os.path.join(src_dir, "vanadium"),
        os.path.join(src_dir, "build/config/android"),
    ]

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, _, files in os.walk(scan_dir):
            for file_name in files:
                full_path = os.path.join(root, file_name)
                if file_name.endswith((".gni", ".gn")):
                    patch_target_sdk_in_gni(full_path)
                elif file_name.endswith(".expected") or file_name == "AndroidManifest.xml":
                    patch_file(
                        full_path,
                        [
                            ('android:minSdkVersion="34"', 'android:minSdkVersion="29"'),
                            ('android:targetSdkVersion="37"', 'android:targetSdkVersion="34"'),
                            ('android:targetSdkVersion="36"', 'android:targetSdkVersion="34"'),
                            ('android:targetSdkVersion="35"', 'android:targetSdkVersion="34"'),
                        ],
                    )

    # Ensure extractNativeLibs="true"
    patch_manifest_extract_native_libs(src_dir)

    print("SDK version injection (minSdk: 29 / targetSdk: 34) & extractNativeLibs check complete.")


if __name__ == "__main__":
    main()
