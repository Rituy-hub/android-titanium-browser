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
            "Patched AndroidManifest.xml: set android:extractNativeLibs=\"true\" for Android 10 compatibility."
        )


def main() -> None:
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    targets = [
        (
            os.path.join(src_dir, "chrome/android/chrome_public_apk_tmpl.gni"),
            [
                ("min_sdk_version = 34", "min_sdk_version = 29"),
                ("target_sdk_version = 37", "target_sdk_version = 34"),
                ("target_sdk_version = 36", "target_sdk_version = 34"),
                ("target_sdk_version = 35", "target_sdk_version = 34"),
            ],
        ),
        (
            os.path.join(src_dir, "chrome/android/trichrome.gni"),
            [
                ("min_sdk_version = 34", "min_sdk_version = 29"),
                ("target_sdk_version = 37", "target_sdk_version = 34"),
                ("target_sdk_version = 36", "target_sdk_version = 34"),
                ("target_sdk_version = 35", "target_sdk_version = 34"),
            ],
        ),
        (
            os.path.join(src_dir, "android_webview/system_webview_apk_tmpl.gni"),
            [
                ("min_sdk_version = 34", "min_sdk_version = 29"),
                ("target_sdk_version = 37", "target_sdk_version = 34"),
                ("target_sdk_version = 36", "target_sdk_version = 34"),
                ("target_sdk_version = 35", "target_sdk_version = 34"),
            ],
        ),
        (
            os.path.join(
                src_dir,
                "chrome/android/expectations/trichrome_library_64_32_apk.AndroidManifest.expected",
            ),
            [
                ('android:minSdkVersion="34"', 'android:minSdkVersion="29"'),
                ('android:targetSdkVersion="37"', 'android:targetSdkVersion="34"'),
            ],
        ),
        (
            os.path.join(
                src_dir,
                "chrome/android/expectations/trichrome_library_64_apk.AndroidManifest.expected",
            ),
            [
                ('android:minSdkVersion="34"', 'android:minSdkVersion="29"'),
                ('android:targetSdkVersion="37"', 'android:targetSdkVersion="34"'),
            ],
        ),
    ]

    for file_path, replacements in targets:
        patch_file(file_path, replacements)

    # Also dynamically scan relevant directories if they exist for any remaining hardcoded min_sdk_version = 34 or targetSdkVersion = 37
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
                    patch_file(
                        full_path,
                        [
                            ("min_sdk_version = 34", "min_sdk_version = 29"),
                            ("target_sdk_version = 37", "target_sdk_version = 34"),
                            ("target_sdk_version = 36", "target_sdk_version = 34"),
                            ("target_sdk_version = 35", "target_sdk_version = 34"),
                            ("default_min_sdk_version = 34", "default_min_sdk_version = 29"),
                            ("default_target_sdk_version = 37", "default_target_sdk_version = 34"),
                            ("default_target_sdk_version = 36", "default_target_sdk_version = 34"),
                            ("default_target_sdk_version = 35", "default_target_sdk_version = 34"),
                        ],
                    )
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

    print("SDK version downgrade (minSdk: 29 / targetSdk: 34) & extractNativeLibs check complete.")


if __name__ == "__main__":
    main()
