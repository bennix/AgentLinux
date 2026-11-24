"""Create office files with the packaged CLI-Anything harness."""
import subprocess
import tempfile
from pathlib import Path


def create_file(kind, text):
    formats = {"writer": "odt", "calc": "ods", "impress": "odp"}
    if kind not in formats or not isinstance(text, str) or not 0 < len(text) <= 16000 or "\0" in text:
        raise ValueError("Choose an office format and supply 1–16000 characters.")
    directory = Path.home() / "Documents"
    directory.mkdir(exist_ok=True)
    commands = {
        "writer": ["writer", "add-paragraph", "--text", text],
        "calc": ["calc", "set-cell", "--", "A1", text],
        "impress": ["impress", "add-slide", "--title", "AgentLinux", "--content", text],
    }
    with tempfile.TemporaryDirectory(dir=directory) as temp:
        project = str(Path(temp) / "project.json")
        output = Path(temp) / ("AgentLinux." + formats[kind])
        cli = ["/usr/local/bin/cli-anything-libreoffice", "--json"]
        for argv in (["document", "new", "--type", kind, "--output", project],
                     ["--project", project, *commands[kind]],
                     ["--project", project, "export", "render", str(output), "--preset", formats[kind]]):
            result = subprocess.run(cli + argv, capture_output=True, text=True, timeout=90)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout)[-1000:])
        # Publish the complete file atomically, preserving existing documents.
        import os
        from uuid import uuid4
        target = directory / f"AgentLinux-{uuid4().hex[:12]}.{formats[kind]}"
        os.link(output, target)
        return target
