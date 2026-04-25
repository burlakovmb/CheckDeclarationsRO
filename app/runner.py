import subprocess
import tempfile
import os
from parser import parse_duk_err_txt

DUK_PATH = os.getenv("DUK_PATH", "/app/duk/dist/DUKIntegrator.jar")

def run_validation(declaration_type: str, xml: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.xml")

        with open(input_path, "w", encoding="utf-8") as f:
            f.write(xml)

        cmd = [
            "java",
            "-jar",
            DUK_PATH,
            "-v",
            declaration_type,
            input_path
        ]

        result = subprocess.run(
            cmd,
            cwd=tmpdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )

        err_file = input_path + ".err.txt"

        if os.path.exists(err_file):
            with open(err_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()

            if content.lower() == "ok":
                return {
                    "status": "ok",
                    "errors": [],
                    "warnings": []
                }

            errors, warnings = parse_duk_err_txt(content)
            return {
                "status": "error" if errors else "ok",
                "errors": errors,
                "warnings": warnings
            }

        return {
            "status": "error",
            "errors": [{
                "code": "EXECUTION_ERROR",
                "message": result.stderr.decode() or result.stdout.decode()
            }],
            "warnings": []
        }