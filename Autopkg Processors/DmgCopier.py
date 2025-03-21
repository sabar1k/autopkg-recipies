from autopkglib import Processor, ProcessorError
import shutil
import os

__all__ = ["DmgCopier"]

class DmgCopier(Processor):
    description = "Copies a file or folder from a mounted DMG to a destination path."

    input_variables = {
        "source_path": {
            "required": True,
            "description": "The path to the file or folder to copy (e.g. /Volumes/App/AppName.app)."
        },
        "destination_path": {
            "required": True,
            "description": "The full path where the file/folder should be copied to."
        }
    }

    output_variables = {
    }

    def main(self):
        source = self.env["source_path"]
        dest = self.env["destination_path"]

        if not os.path.exists(source):
            raise ProcessorError(f"Source path does not exist: {source}")

        self.output(f"Copying from {source} to {dest}...")

        if os.path.isdir(source):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)

        self.output("✅ Copy completed.")