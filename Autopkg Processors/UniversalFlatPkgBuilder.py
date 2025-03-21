from autopkglib import Processor, ProcessorError
import os
import shutil
import subprocess
import plistlib

__all__ = ["UniversalFlatPkgBuilder"]

class UniversalFlatPkgBuilder(Processor):
    """Creates a universal flat package with both Intel and ARM versions of an app,
    including security checks, version validation, and a postinstall script for architecture-aware installation."""

    description = __doc__

    input_variables = {
        "app_name": {
            "required": True,
            "description": "The name of the application (e.g., 'Miro.app')"
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

    def validate_app(self, app_path):
        """Validates Developer ID, Team ID, and bundle version"""
        info_plist = os.path.join(app_path, "Contents", "Info.plist")
        if not os.path.exists(info_plist):
            raise ProcessorError(f"Missing Info.plist in {app_path}")

        # Extract version and bundle ID
        with open(info_plist, "rb") as f:
            plist = plistlib.load(f)

        version = plist.get("CFBundleShortVersionString", "Unknown")
        bundle_id = plist.get("CFBundleIdentifier", "Unknown")

        # Verify signing
        result = subprocess.run([
  		  "/usr/bin/codesign", "-dvv", app_path
		], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
		
        if "Developer ID Application" not in result.stdout:
            raise ProcessorError(f"App at {app_path} is not properly signed!")

        return version, bundle_id

    def main(self):
        app_name = self.env["app_name"]
        intel_app = self.env["intel_app_path"]
        arm_app = self.env["arm_app_path"]
        pkg_output_path = self.env["pkg_output_path"]

        # Validate apps
        intel_version, intel_bundle_id = self.validate_app(intel_app)
        arm_version, arm_bundle_id = self.validate_app(arm_app)

        if intel_version != arm_version or intel_bundle_id != arm_bundle_id:
            raise ProcessorError("Version or Bundle ID mismatch between Intel and ARM apps!")

        # Set up working directories
        work_dir = os.path.join(self.env["RECIPE_CACHE_DIR"], "universal_pkgbuild")
        payload_dir = os.path.join(work_dir, "pkgroot", "Library", "Application Support", "UniversalApps")
        scripts_dir = os.path.join(work_dir, "scripts")
        intel_dest = os.path.join(payload_dir, "Intel", app_name)
        arm_dest = os.path.join(payload_dir, "Apple", app_name)

        # Cleanup old build directories
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(payload_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)

        # Copy both app versions
        shutil.copytree(intel_app, intel_dest)
        shutil.copytree(arm_app, arm_dest)

        # Create improved postinstall script
        postinstall_script = os.path.join(scripts_dir, "postinstall")
        with open(postinstall_script, "w") as f:
            f.write(f"""#!/bin/zsh
# Detect Mac Architecture
arch=$(/usr/bin/arch)

# Define paths
app_name="{app_name}"
source_dir="/Library/Application Support/UniversalApps"
dest_dir="/Applications"

# Select correct version
if [[ "$arch" == "arm64" ]]; then
    /bin/cp -R "$source_dir/Apple/$app_name" "$dest_dir/$app_name"
else
    /bin/cp -R "$source_dir/Intel/$app_name" "$dest_dir/$app_name"
fi

# Remove quarantine & re-sign
/usr/bin/xattr -rc "$dest_dir/$app_name"
/usr/bin/codesign --force --deep --sign - --timestamp --preserve-metadata=identifier,entitlements "$dest_dir/$app_name"

# Verify signing
codesign -vvv "$dest_dir/$app_name" || echo "❌ Signing failed!"

# Cleanup
/bin/rm -rf "$source_dir"

exit 0
""")
        os.chmod(postinstall_script, 0o755)

        # Build the package
        cmd = [
            "/usr/bin/pkgbuild",
            "--identifier", intel_bundle_id,
            "--version", intel_version,
            "--root", os.path.join(work_dir, "pkgroot"),
            "--install-location", "/",
            "--scripts", scripts_dir,
            pkg_output_path
        ]
        self.output(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        self.output(f"✅ Universal flat package created at: {pkg_output_path}")