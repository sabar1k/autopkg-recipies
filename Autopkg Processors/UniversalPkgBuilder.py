from autopkglib import Processor, ProcessorError, call_pkg_creator
import os
import shutil
import subprocess
import plistlib

__all__ = ["UniversalPkgBuilder"]

class UniversalPkgBuilder(Processor):
    description = (
        "Creates a universal installer package using Intel and Apple Silicon .app versions, with a preinstall script, and builds using PkgCreator."
    )

    input_variables = {
        "application_name": {
            "required": True,
            "description": "Base name of the app (e.g. 'Miro.app')"
        },
        "apple_path": {
            "required": True,
            "description": "Path to the Apple Silicon version of the .app"
        },
        "intel_path": {
            "required": True,
            "description": "Path to the Intel version of the .app"
        },
        "match_versions": {
            "required": False,
            "description": "Set to False to skip version/bundle ID match check.",
            "default": True
        }
    }

    output_variables = {
        "universal_pkg_path": {
            "description": "Path to the created universal package."
        },
        "version": {
            "description": "App version used in the package."
        },
        "identifier": {
            "description": "Bundle identifier used in the package."
        }
    }

    def get_app_metadata(self, app_path):
        info_plist = os.path.join(app_path, "Contents", "Info.plist")
        if not os.path.exists(info_plist):
            raise ProcessorError(f"Missing Info.plist at: {info_plist}")
        with open(info_plist, "rb") as f:
            plist = plistlib.load(f)
        return {
            "version": plist.get("CFBundleShortVersionString") or plist.get("CFBundleVersion"),
            "identifier": plist.get("CFBundleIdentifier"),
        }

    def main(self):
        app_name = self.env["application_name"]
        apple_app = self.env["apple_path"]
        intel_app = self.env["intel_path"]
        match_versions = self.env.get("match_versions", True)

        # Get metadata
        apple_meta = self.get_app_metadata(apple_app)
        intel_meta = self.get_app_metadata(intel_app)

        if match_versions:
            if apple_meta != intel_meta:
                raise ProcessorError(f"Version or identifier mismatch between architectures:\nApple: {apple_meta}\nIntel: {intel_meta}")

        # Use Apple values
        version = apple_meta["version"]
        identifier = apple_meta["identifier"]

        # Working dirs
        work_dir = os.path.join(self.env.get("RECIPE_CACHE_DIR", "/tmp"), "universal_pkgbuild")
        scripts_dir = os.path.join(work_dir, "Scripts")
        apple_dst = os.path.join(scripts_dir, "Apple", app_name)
        intel_dst = os.path.join(scripts_dir, "Intel", app_name)

        # Clean previous
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(os.path.dirname(apple_dst), exist_ok=True)
        os.makedirs(os.path.dirname(intel_dst), exist_ok=True)

        shutil.copytree(apple_app, apple_dst)
        shutil.copytree(intel_app, intel_dst)

        # Create preinstall script
        preinstall_path = os.path.join(scripts_dir, "preinstall")
        with open(preinstall_path, "w") as f:
            f.write(f"""#!/bin/zsh
app_name=\"{app_name}\"
local_dir=$(dirname \"$0\")
intel_check=$(sysctl -n machdep.cpu.brand_string | grep -oi "Intel")

if [[ -n \"$intel_check\" ]]; then
    cp -pR \"$local_dir/Intel/$app_name\" "/Applications"
else
    cp -pR \"$local_dir/Apple/$app_name\" "/Applications"
fi
touch "/Applications/$app_name"
exit 0
""")
        os.chmod(preinstall_path, 0o755)

        # Use PkgCreator
        pkg_path = os.path.join(self.env.get("RECIPE_CACHE_DIR", "."), f"{app_name}-{version}.pkg")
        pkg_request = {
            "version": version,
            "identifier": identifier,
            "scripts": scripts_dir,
            "payload": ""  # payload-free
        }

        call_pkg_creator(pkg_request, pkg_path)

        self.env["universal_pkg_path"] = pkg_path
        self.env["version"] = version
        self.env["identifier"] = identifier
        self.output(f"✅ Created universal package at: {pkg_path}")
