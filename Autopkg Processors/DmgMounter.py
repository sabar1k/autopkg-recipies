from autopkglib import Processor, ProcessorError
import subprocess
import plistlib

__all__ = ["DmgMounter"]

class DmgMounter(Processor):
    """Mounts a DMG file and returns the mount point as a variable."""

    description = "Mounts a DMG file and sets a mount path as an output variable."
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to the DMG file to be mounted."
        },
        "mount_point_output_variable": {
            "required": True,
            "description": "Name of the variable to store the mount point."
        }
    }
    output_variables = {
        # This is dynamic based on the input
    }

    def main(self):
        dmg_path = self.env["dmg_path"]
        output_var = self.env["mount_point_output_variable"]

        self.output(f"Mounting {dmg_path}...")

        try:
            result = subprocess.run(
                ["/usr/bin/hdiutil", "attach", "-nobrowse", "-plist", dmg_path],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            plist = plistlib.loads(result.stdout)

            mount_point = None
            for entity in plist.get("system-entities", []):
                if "mount-point" in entity:
                    mount_point = entity["mount-point"]
                    break

            if not mount_point:
                raise ProcessorError("Unable to determine mount point from hdiutil output.")

            self.env[output_var] = mount_point
            self.output(f"Mounted {dmg_path} at: {mount_point}")
        except subprocess.CalledProcessError as e:
            raise ProcessorError(f"Failed to mount DMG: {e.stderr.decode().strip()}")