from autopkglib import Processor, ProcessorError
import os
import subprocess
import shutil

__all__ = ["BuildArchSpecificPkg"]

class BuildArchSpecificPkg(Processor):
    """
    Builds a flat .pkg installer from an app bundle for a specific architecture.
    The resulting package installs the .app into /Applications.
    """

    input_variables = {
        "app_path": {
            "required": True,
            "description": "Path to the .app bundle to be packaged."
        },
        "architecture": {
            "required": True,
            "description": "Architecture this .pkg is built for (e.g., x86_64 or arm64)."
        },
        "output_pkg_path": {
            "required": True,
            "description": "Path to the final .pkg file to be created."
        }
    }

    output_variables = {
        "built_pkg_path": {
            "description": "Path to the created .pkg file."
        }
    }

    def main(self):
        app_path = self.env["app_path"]
        arch = self.env["architecture"]
        output_pkg = self.env["output_pkg_path"]

        if not os.path.exists(app_path):
            raise ProcessorError(f"App path does not exist: {app_path}")

        app_name = os.path.basename(app_path)
        version_plist = os.path.join(app_path, "Contents", "Info.plist")

        if not os.path.exists(version_plist):
            raise ProcessorError("Missing Info.plist to extract version info")

        # Create staging directory
        staging_root = os.path.join(self.env["RECIPE_CACHE_DIR"], f"pkgroot-{arch}")
        app_dest = os.path.join(staging_root, "Applications", app_name)

        if os.path.exists(staging_root):
            shutil.rmtree(staging_root)
        os.makedirs(os.path.dirname(app_dest), exist_ok=True)

        # Copy app to staging
        self.output(f"Copying {app_path} to {app_dest}...")
        subprocess.run(["rsync", "-aE", app_path + "/", app_dest], check=True)

        # Build package
        pkgbuild_cmd = [
            "/usr/bin/pkgbuild",
            "--root", staging_root,
            "--install-location", "/",
            "--identifier", f"com.miro.{arch}",
            "--version", "1.0",
            output_pkg
        ]

        self.output(f"Building {arch} .pkg: {' '.join(pkgbuild_cmd)}")
        subprocess.run(pkgbuild_cmd, check=True)

        self.env["built_pkg_path"] = output_pkg
        self.output(f"✅ Built {arch} pkg at: {output_pkg}")
