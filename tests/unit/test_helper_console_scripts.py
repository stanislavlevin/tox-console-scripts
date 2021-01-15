import os
import re
import site
import subprocess
import sys

from pkg_resources import Requirement
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
    def _find_deps(self, req, dists):
        dist = self.by_key[req.project_name]
        if dist in dists:
            return

        dists.append(dist)
        for req_ in dist.requires():
            self._find_deps(req_, dists)

    def resolve(self, reqs):
        dists = []
        for req in reqs:
            self._find_deps(req, dists)

        return dists

    def __init__(self):
        self.by_key = {
            # systemsite package
            "mysitepackage": MockEggInfoDistribution(
                project_name="mysitepackage",
                version="0.1",
                requires=[],
                location=site.getsitepackages([sys.base_prefix])[0],
            ),
            # extra systemsite package must not produce console_script
            "myextrasitepackage": MockEggInfoDistribution(
                project_name="myextrasitepackage",
                version="0.1",
                requires=[],
                location=site.getsitepackages([sys.base_prefix])[0],
            ),
            # package within virtual environment to cover non-systemsite deps
            "mypackage": MockEggInfoDistribution(
                project_name="mypackage",
                version="0.1",
                requires=[],
                location="nonsystemsitelocation",
            ),
            #
            # systemsite package which will be direct requirement of another
            # systemsite package and indirect requirement of installed into
            # virtual environment package
            #
            "myindirectrsitepackage": MockEggInfoDistribution(
                project_name="myindirectrsitepackage",
                version="0.1",
                requires=[],
                location=site.getsitepackages([sys.base_prefix])[0],
            ),
            # systemsite package which requires another one
            "mydirectsitepackage": MockEggInfoDistribution(
                project_name="mydirectsitepackage",
                version="0.1",
                requires=[Requirement.parse("myindirectrsitepackage==0.1")],
                location=site.getsitepackages([sys.base_prefix])[0],
                console_scripts=False,
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
        ["mysitepackage>=0.1", "mypackage==0.1"],
    ),
)
def test_helper_mocked(mocker, deps, capsys):
    mocker.patch(
        "tox_console_scripts.helper.console_scripts.WorkingSet", MockWorkingSet
    )
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


def test_helper_indirect_systemdep(mocker, capsys):
    mocker.patch(
        "tox_console_scripts.helper.console_scripts.WorkingSet", MockWorkingSet
    )
    mopen = mocker.patch("builtins.open", mocker.mock_open())
    console_scripts.main("notexistedpath", deps=["mydirectsitepackage==0.1"])
    mopen.assert_called_once_with(
        os.path.join("notexistedpath", "myindirectrsitepackage"), "w"
    )

    mopen().write.assert_called_once()
    # check at least shebang
    write_args, _ = mopen().write.call_args
    assert len(write_args) == 1
    assert re.match(f"^#!{sys.executable}\n", write_args[0])

    captured = capsys.readouterr()
    expected_msg = "Installing myindirectrsitepackage script to notexistedpath\n"
    assert captured.out == expected_msg
