import os
import re
import site
import subprocess
import sys

import pytest

import tox_console_scripts.helper.console_scripts as console_scripts


class MockEggInfoDistribution:
    def __init__(self, project_name, version, requires, location, console_scripts=True):
        self.project_name = project_name
        self.version = version
        self._location = location
        self._requires = requires
        self.console_scripts = console_scripts

    def as_requirement(self):
        return f"{self.project_name}=={self.version}"

    def get_entry_map(self, group=None):
        if not self.console_scripts:
            return dict()

        if group == "console_scripts":
            return dict({self.project_name: None})

        return dict()

    @property
    def location(self):
        return self._location

    def requires(self):
        return self._requires


class MockWorkingSet:
    def __init__(self):
        self._by_key = None
        self._entry_keys = None

    @property
    def by_key(self):
        if self._by_key is None:
            self._by_key = {
                # systemsite package
                "mysitepackage": MockEggInfoDistribution(
                    project_name="mysitepackage",
                    version="0.1",
                    requires=[],
                    location=site.getsitepackages([sys.base_prefix])[0],
                ),
                # systemsite package which hasn't console_scripts
                "mysitepackage_without_consolescripts": MockEggInfoDistribution(
                    project_name="mysitepackage_without_consolescripts",
                    version="0.1",
                    requires=[],
                    location=site.getsitepackages([sys.base_prefix])[0],
                    console_scripts=False,
                ),
            }
        return self._by_key

    @property
    def entry_keys(self):
        if self._entry_keys is None:
            self._entry_keys = {}
            for key in self.by_key:
                dist = self.by_key[key]
                if self._entry_keys.get(dist.location) is None:
                    self._entry_keys[dist.location] = []
                self._entry_keys[dist.location].append(dist.project_name)

        return self._entry_keys


def test_install_console_scripts():
    """Generating of nothing must not fail"""
    args = [
        sys.executable,
        "-m",
        "tox_console_scripts.helper.console_scripts",
    ]
    proc = subprocess.run(args)
    assert proc.returncode == 0


def test_helper_mocked_install(mocker, capsys):
    mocker.patch(
        "tox_console_scripts.helper.console_scripts.WorkingSet", MockWorkingSet
    )
    mocker.patch(
        "tox_console_scripts.helper.console_scripts.sysconfig.get_path",
        return_value="notexistedpath",
    )
    mopen = mocker.patch(
        "tox_console_scripts.helper.console_scripts.open", mocker.mock_open()
    )
    console_scripts.install_console_scripts()
    mopen.assert_called_once_with(os.path.join("notexistedpath", "mysitepackage"), "w")

    mopen().write.assert_called_once()
    # check at least shebang
    write_args, _ = mopen().write.call_args
    assert len(write_args) == 1
    assert re.match(f"^#!{sys.executable}\n", write_args[0])

    captured = capsys.readouterr()
    capt_out_lines = captured.out.splitlines()
    expected_msgs = [
        "Installing mysitepackage script to notexistedpath",
    ]
    assert capt_out_lines == expected_msgs
