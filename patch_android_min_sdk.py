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
        print(f"Patched minSdkVersion in: {file_path}")
        return True
    return False


def main() -> None:
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    targets = [
        (
            os.path.join(src_dir, "chrome/android/chrome_public_apk_tmpl.gni"),
            [("min_sdk_version = 34", "min_sdk_version = 29")],
        ),
        (
            os.path.join(src_dir, "chrome/android/trichrome.gni"),
            [("min_sdk_version = 34", "min_sdk_version = 29")],
        ),
        (
            os.path.join(src_dir, "android_webview/system_webview_apk_tmpl.gni"),
            [("min_sdk_version = 34", "min_sdk_version = 29")],
        ),
        (
            os.path.join(
                src_dir,
                "chrome/android/expectations/trichrome_library_64_32_apk.AndroidManifest.expected",
            ),
            [('android:minSdkVersion="34"', 'android:minSdkVersion="29"')],
        ),
        (
            os.path.join(
                src_dir,
                "chrome/android/expectations/trichrome_library_64_apk.AndroidManifest.expected",
            ),
            [('android:minSdkVersion="34"', 'android:minSdkVersion="29"')],
        ),
    ]

    for file_path, replacements in targets:
        patch_file(file_path, replacements)

    # Also dynamically scan relevant directories if they exist for any remaining hardcoded min_sdk_version = 34
    scan_dirs = [
        os.path.join(src_dir, "chrome/android"),
        os.path.join(src_dir, "android_webview"),
        os.path.join(src_dir, "vanadium"),
    ]

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, _, files in os.walk(scan_dir):
            for file_name in files:
                if file_name.endswith((".gni", ".gn")):
                    full_path = os.path.join(root, file_name)
                    patch_file(
                        full_path,
                        [
                            (
                                "min_sdk_version = 34",
                                "min_sdk_version = 29",
                            )
                        ],
                    )
                elif file_name.endswith(".expected"):
                    full_path = os.path.join(root, file_name)
                    patch_file(
                        full_path,
                        [
                            (
                                'android:minSdkVersion="34"',
                                'android:minSdkVersion="29"',
                            )
                        ],
                    )

    print("minSdkVersion downgrade patch check complete (target minSdk: 29 / Android 10).")


if __name__ == "__main__":
    main()
