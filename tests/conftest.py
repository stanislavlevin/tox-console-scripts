from pathlib import Path
import os
import shutil
import site
import sys
import textwrap

import pytest


pytest_plugins = "tox._pytestplugin"


@pytest.fixture
def tmp_dir(tmp_path):
    yield tmp_path
    shutil.rmtree(tmp_path)


class PathDistribution:
    def __init__(self, location, name="foo", version="1.0", contents=None):
        """
        Contents should be relative to location
        """
        self.name = name
        self.version = version

        self.location = location
        # may exist if location points to system sitepackages for example
        self.location.mkdir(exist_ok=True)

        self.dist_info = f"{name}-{version}.dist-info"
        # but there should be no existent dist-info (avoid overwrite)
        if (self.location / self.dist_info).exists():
            raise RuntimeError(
                f"Duplicated distribution at {self.location}: {self.dist_info}"
            )

        self.contents = {}
        if contents is None:
            self.contents = {
                Path(name)
                / "__init__.py": """\
                    def main():
                        print("Hello, World!")
                    """,
                Path(self.dist_info)
                / "METADATA": f"""\
                    Metadata-Version: 2.1
                    Name: {name}
                    Version: {version}
                    """,
            }
        else:
            self.contents = dict(contents)

    def make(self):
        for file, content in self.contents.items():
            if Path(file).is_absolute():
                raise RuntimeError(
                    f"Files paths in contents should be relative, given: {file}"
                )
            target = self.location / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(textwrap.dedent(content), encoding="utf-8")

    def add_console_scripts(self, eps):
        eps_text = "[console_scripts]\n"
        for ep_name, ep_module, ep_attr in eps:
            eps_text += f"{ep_name} = {ep_module}:{ep_attr}\n"

        self.contents[Path(self.dist_info) / "entry_points.txt"] = eps_text


@pytest.fixture
def path_distribution(tmp_dir):
    def _make_distribution(name="foo", version="1.0", contents=None):
        return PathDistribution(
            tmp_dir / name,
            name=name,
            version=version,
            contents=contents,
        )

    return _make_distribution


@pytest.fixture
def system_distribution():
    """Generates distribution in system site packages"""
    if os.geteuid() != 0:
        pytest.skip("Requires root privileges")

    # one of the paths is enough
    systemsite_path = Path(sorted(site.getsitepackages([sys.base_prefix]))[0])
    location = None
    dist_info = None

    def _make_distribution(name="foo", version="1.0", contents=None):
        nonlocal location
        nonlocal dist_info

        distr = PathDistribution(
            systemsite_path,
            name=name,
            version=version,
            contents=contents,
        )
        distr.add_console_scripts(((f"{name}_script", name, "main"),))

        location = distr.location / distr.name
        dist_info = distr.location / distr.dist_info
        return distr

    yield _make_distribution

    shutil.rmtree(location, ignore_errors=True)
    shutil.rmtree(dist_info, ignore_errors=True)
