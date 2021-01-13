import os
import re
import site
import subprocess
import sys

import pytest

import tox_console_scripts.helper.console_scripts as console_scripts


class MockEggInfoDistribution:
    def __init__(self, project_name, version, location=None):
        self.project_name = project_name
        self.version = version
        self._location = location

    def as_requirement(self):
        return f"{self.project_name}=={self.version}"

    def get_entry_map(self, group=None):
        if group == "console_scripts":
            return dict({self.project_name: None})

        return dict()

    @property
    def location(self):
        return self._location


class MockWorkingSet:
    def __init__(self):
        self.by_key = {
            # systemsite package
            "mysitepackage": MockEggInfoDistribution(
                project_name="mysitepackage",
                version="0.1",
                location=site.getsitepackages([sys.base_prefix])[0],
            ),
            # extra systemsite package must not produce console_script
            "myextrasitepackage": MockEggInfoDistribution(
                project_name="myextrasitepackage",
                version="0.1",
                location=site.getsitepackages([sys.base_prefix])[0],
            ),
            # package within virtual environment to cover non-systemsite deps
            "mypackage": MockEggInfoDistribution(
                project_name="mypackage",
                version="0.1",
                location="nonsystemsitelocation",
            ),
        }


def test_helper(tmpdir):
    """Generating of nothing must not fail"""
    bindir = tmpdir.mkdir("tox").join("bin")
    bindir.ensure(dir=1)
    args = [
        sys.executable,
        "-m",
        "tox_console_scripts.helper.console_scripts",
        "--bindir",
        str(bindir),
    ]
    proc = subprocess.run(args)
    assert proc.returncode == 0


def test_helper_less_args():
    """--bindir option is required"""
    args = [
        sys.executable,
        "-m",
        "tox_console_scripts.helper.console_scripts",
    ]
    proc = subprocess.run(args, capture_output=True)
    assert proc.returncode != 0
    expected_msg = "error: the following arguments are required: --bindir\n"
    assert expected_msg in proc.stderr.decode()


@pytest.mark.parametrize(
    "deps",
    (
        ["mysitepackage"],
        ["mysitepackage", "mypackage"],
    ),
)
def test_helper_mocked(mocker, deps, capsys):
    mocker.patch("pkg_resources.WorkingSet", MockWorkingSet)
    mopen = mocker.patch("builtins.open", mocker.mock_open())
    console_scripts.main("notexistedpath", deps=deps)
    mopen.assert_called_once_with(os.path.join("notexistedpath", "mysitepackage"), "w")

    mopen().write.assert_called_once()
    # check at least shebang
    write_args, _ = mopen().write.call_args
    assert len(write_args) == 1
    assert re.match(f"^#!{sys.executable}\n", write_args[0])

    captured = capsys.readouterr()
    expected_msg = "Installing mysitepackage script to notexistedpath\n"
    assert captured.out == expected_msg
