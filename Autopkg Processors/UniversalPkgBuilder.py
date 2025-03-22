from autopkglib import Processor, ProcessorError
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
        "version": {
            "required": True,
            "description": "Version string for the package"
        },
        "identifier": {
            "required": True,
            "description": "Bundle identifier for the package"
        }
    }

    output_variables = {
        "universal_pkg_path": {
            "description": "Path to the created universal package."
        }
    }

    def main(self):
        app_name = self.env["application_name"]
        apple_app = self.env["apple_path"]
        intel_app = self.env["intel_path"]
        version = self.env["version"]
        identifier = self.env["identifier"]

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

        # Use PkgCreator via autopkgserver
        pkg_path = os.path.join(self.env.get("RECIPE_CACHE_DIR", "."), f"{app_name}-{version}.pkg")
        pkg_request = {
            "version": version,
            "identifier": identifier,
            "scripts": scripts_dir,
            "payload": ""  # Payload-free install
        }

        try:
            from autopkglib import call_pkg_creator
        except ImportError:
            raise ProcessorError("PkgCreator support is not available. Make sure autopkgserver is running.")

        # Call the shared PkgCreator interface
        call_pkg_creator(pkg_request, pkg_path)

        self.env["universal_pkg_path"] = pkg_path
        self.output(f"✅ Created universal package at: {pkg_path}")
