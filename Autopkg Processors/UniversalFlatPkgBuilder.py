from autopkglib import Processor, ProcessorError
import os
import shutil
import subprocess

__all__ = ["UniversalFlatPkgBuilder"]

class UniversalFlatPkgBuilder(Processor):
    """Creates a flat package with both Intel and ARM versions of a macOS app, 
    and includes a postinstall script that installs the correct one based on architecture."""

    description = __doc__

    input_variables = {
        "app_name": {
            "required": True,
            "description": "The name of the application (e.g., 'IntelliJ IDEA CE.app')"
        },
        "intel_app_path": {
            "required": True,
            "description": "Path to the Intel version of the .app"
        },
        "arm_app_path": {
            "required": True,
            "description": "Path to the ARM version of the .app"
        },
        "pkg_output_path": {
            "required": True,
            "description": "Full path (including .pkg filename) where the flat package should be created"
        }
    }

    output_variables = {}

    def main(self):
        app_name = self.env["app_name"]
        intel_app = self.env["intel_app_path"]
        arm_app = self.env["arm_app_path"]
        pkg_output_path = self.env["pkg_output_path"]

        # Set up working directories
        work_dir = os.path.join(self.env["RECIPE_CACHE_DIR"], "universal_pkgbuild")
        payload_dir = os.path.join(work_dir, "root")
        scripts_dir = os.path.join(work_dir, "scripts")
        intel_dest = os.path.join(payload_dir, "Intel", app_name)
        arm_dest = os.path.join(payload_dir, "Apple", app_name)

        # Cleanup old build directories
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(payload_dir)
        os.makedirs(scripts_dir)

        # Copy both app versions
        shutil.copytree(intel_app, intel_dest)
        shutil.copytree(arm_app, arm_dest)

        # Create a generic postinstall script
        postinstall_script = os.path.join(scripts_dir, "postinstall")
        with open(postinstall_script, "w") as f:
            f.write(f"""#!/bin/zsh
# Populate PKG names
app_name="{app_name}"
apple_app="Apple/$app_name"
intel_app="Intel/$app_name"

# Get local directory
local_dir=$(dirname $0)

# Identify Mac processor type
intel_check=$(/usr/sbin/sysctl -n machdep.cpu.brand_string | /usr/bin/grep -oi "Intel")

if [[ -n "$intel_check" ]]; then
    /bin/cp -R "$local_dir/$intel_app" "/Applications"
else
    /bin/cp -R "$local_dir/$apple_app" "/Applications"
fi

# Refresh icon cache
/usr/bin/touch "/Applications/$app_name"

exit 0
""")
        os.chmod(postinstall_script, 0o755)

        # Build the flat package
        cmd = [
            "/usr/bin/pkgbuild",
            "--identifier", f"com.universal.pkg.{app_name.replace('.app', '').lower()}",
            "--version", "1.0",
            "--scripts", scripts_dir,
            "--root", payload_dir,
            pkg_output_path
        ]
        self.output(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        self.output(f"✅ Universal flat package created at: {pkg_output_path}")
    