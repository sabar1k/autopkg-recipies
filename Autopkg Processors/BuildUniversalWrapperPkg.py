from autopkglib import Processor, ProcessorError
import os
import subprocess
import shutil

__all__ = ["BuildUniversalWrapperPkg"]

class BuildUniversalWrapperPkg(Processor):
    """
    Wraps two architecture-specific .pkg installers into one universal installer package.
    Uses a postinstall script to detect architecture and install the appropriate one.
    """

    input_variables = {
        "intel_pkg_path": {
            "required": True,
            "description": "Path to the Intel .pkg."
        },
        "arm_pkg_path": {
            "required": True,
            "description": "Path to the ARM .pkg."
        },
        "output_universal_pkg_path": {
            "required": True,
            "description": "Path to the final universal .pkg to be created."
        }
    }

    output_variables = {
        "universal_pkg_path": {
            "description": "Path to the created universal .pkg."
        }
    }

    def main(self):
        intel_pkg = self.env["intel_pkg_path"]
        arm_pkg = self.env["arm_pkg_path"]
        output_pkg = self.env["output_universal_pkg_path"]

        # Set up staging dirs
        work_dir = os.path.join(self.env["RECIPE_CACHE_DIR"], "universal_wrapper")
        pkgroot = os.path.join(work_dir, "pkgroot")
        scripts_dir = os.path.join(work_dir, "scripts")

        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(pkgroot, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)

        # Copy both .pkg files into pkgroot
        shutil.copy(intel_pkg, os.path.join(pkgroot, "Miro-Intel.pkg"))
        shutil.copy(arm_pkg, os.path.join(pkgroot, "Miro-ARM.pkg"))

        # Create postinstall script
        postinstall_path = os.path.join(scripts_dir, "postinstall")
        with open(postinstall_path, "w") as f:
            f.write("""#!/bin/zsh
arch=$(/usr/bin/uname -m)
echo "Detected architecture: $arch" >> /var/log/install_MiroUniversal.log

if [[ "$arch" == "arm64" ]]; then
    echo "Installing ARM package..." >> /var/log/install_MiroUniversal.log
    /usr/sbin/installer -pkg "/Library/Application Support/UniversalAppPackages/Miro-ARM.pkg" -target /
else
    echo "Installing Intel package..." >> /var/log/install_MiroUniversal.log
    /usr/sbin/installer -pkg "/Library/Application Support/UniversalAppPackages/Miro-Intel.pkg" -target /
fi
exit 0
""")
        os.chmod(postinstall_path, 0o755)

        # Build the universal wrapper .pkg
        cmd = [
            "/usr/bin/pkgbuild",
            "--identifier", "com.miro.universal",
            "--version", "1.0",
            "--scripts", scripts_dir,
            "--root", pkgroot,
            "--install-location", "/Library/Application Support/UniversalAppPackages",
            output_pkg
        ]

        self.output(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        self.env["universal_pkg_path"] = output_pkg
        self.output(f"✅ Universal wrapper package created at: {output_pkg}")