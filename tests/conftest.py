from pathlib import Path
import os
import shutil
import subprocess
import sys
import textwrap

import pytest


@pytest.fixture
def tmp_dir(tmp_path):
    yield tmp_path
    shutil.rmtree(tmp_path)


class ToxProject:
    """Project that uses tox"""

    def __init__(self, location, name="my_tox_project"):
        self.name = name
        self.location = location
        self.location.mkdir()

        self.contents = {
            "pyproject.toml": f"""\
                [project]
                name = "{name}"
                version = "1.0"
            """,
            f"{name}/__init__.py": f"""\
                def main():
                    print(f"Hello from {name}")
                """,
        }

    def create(self):
        for file, content in self.contents.items():
            if Path(file).is_absolute():
                raise RuntimeError(
                    f"Files paths in contents should be relative, given: {file}"
                )
            target = self.location / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(textwrap.dedent(content), encoding="utf-8")

    def run(self, args):
        tox_args = [sys.executable, "-m", "tox"]
        tox_args.extend(args)
        env = os.environ.copy()
        # make tox environment isolated
        env.update(
            {
                "PIP_NO_BUILD_ISOLATION": "NO",
                "PIP_NO_INDEX": "YES",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "VIRTUALENV_SYSTEM_SITE_PACKAGES": "1",
            }
        )

        result = subprocess.run(
            tox_args,
            capture_output=True,
            cwd=self.location,
            env=env,
            encoding="utf-8",
        )
        return result


@pytest.fixture
def tox_project(tmp_dir, monkeypatch):
    """Creates tox project"""

    def _make_tox_project(name="project"):
        location = tmp_dir / f"{name}_dir"
        project = ToxProject(location, name=name)
        monkeypatch.chdir(project.location)
        return project

    return _make_tox_project
