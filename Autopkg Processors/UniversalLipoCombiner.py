from autopkglib import Processor, ProcessorError
import os
import shutil
import subprocess

__all__ = ["UniversalLipoCombiner"]

class UniversalLipoCombiner(Processor):
    description = "Creates a universal macOS .app by combining Intel and ARM app binaries."
    input_variables = {
        "intel_app_path": {
            "required": True,
            "description": "Path to x86_64 app bundle"
        },
        "arm_app_path": {
            "required": True,
            "description": "Path to arm64 app bundle"
        },
        "output_app_path": {
            "required": True,
            "description": "Destination for the universal .app"
        },
        "binary_relative_path": {
            "required": False,
            "description": "Relative path from .app root to main executable (default: Contents/MacOS/<AppName>)"
        }
    }
    output_variables = {}

    def main(self):
        intel_app = self.env["intel_app_path"]
        arm_app = self.env["arm_app_path"]
        output_app = self.env["output_app_path"]
        app_name = os.path.basename(intel_app).replace('.app', '')

        # Default binary path if not provided
        rel_bin_path = self.env.get("binary_relative_path", f"Contents/MacOS/{app_name}")
        intel_bin = os.path.join(intel_app, rel_bin_path)
        arm_bin = os.path.join(arm_app, rel_bin_path)
        output_bin = os.path.join(output_app, rel_bin_path)

        if not os.path.exists(intel_bin):
            raise ProcessorError(f"Intel binary not found at: {intel_bin}")
        if not os.path.exists(arm_bin):
            raise ProcessorError(f"ARM binary not found at: {arm_bin}")

        # Copy the Intel app as base
        if os.path.exists(output_app):
            shutil.rmtree(output_app)
        shutil.copytree(intel_app, output_app)

        # Create universal binary
        self.output(f"Combining binaries: {intel_bin} and {arm_bin}")
        subprocess.run(["lipo", "-create", intel_bin, arm_bin, "-output", output_bin], check=True)

        # Optional: verify
        result = subprocess.check_output(["lipo", "-archs", output_bin]).decode().strip()
        self.output(f"✅ Universal binary created at {output_bin} with architectures: {result}")