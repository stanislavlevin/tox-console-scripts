from importlib.metadata import distributions
import os
import re
import site
import subprocess
import sys
import textwrap

import pytest

import tox_console_scripts.helper.console_scripts as console_scripts


@pytest.fixture
def sub_execs(tmp_dir, request):
    """
    Makes named executable(link to sys.executable)
    """
    sys_execs = tmp_dir / "sys_execs"
    sys_execs.mkdir()
    sys_exec, expected_shebang = request.param
    sys_exec_path = sys_execs / sys_exec
    sys_exec_path.symlink_to(sys.executable)
    return str(sys_exec_path), expected_shebang.format(sys_execs=sys_execs)


@pytest.fixture
def mock_distributions(mocker):
    return mocker.patch.object(console_scripts, "distributions")


@pytest.fixture
def mock_scriptsdir(mocker):
    return mocker.patch.object(console_scripts.sysconfig, "get_path")


@pytest.fixture
def bindir(tmp_dir):
    return tmp_dir / "bin"


def test_install_nothing(tmp_dir, bindir, mock_distributions, mock_scriptsdir, capsys):
    """Generating of nothing must not fail"""
    # pointing to path without distributions
    mock_distributions.return_value = distributions(path=[tmp_dir])
    mock_scriptsdir.return_value = str(bindir)
    console_scripts.install_console_scripts()

    # check logging
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    # check content of bindir
    assert not bindir.exists()


@pytest.mark.parametrize(
    "sub_execs",
    (
        ("mypython", "#!{sys_execs}/mypython"),
        (
            f"{'very_' * 24}_long_mypython",
            f"#!/bin/sh\n'''exec' {{sys_execs}}/{'very_' * 24}_long_mypython"
            ' "$0" "$@"\n' + "' '''",
        ),
    ),
    indirect=True,
    ids=["regular_shebang", "long_shebang"],
)
def test_install_console_scripts(
    sub_execs,
    mock_distributions,
    mock_scriptsdir,
    bindir,
    path_distribution,
    mocker,
    capsys,
):
    sys_exec, expected_shebang = sub_execs

    # prepare 2 dists: 1 - with console_scripts and 2 - without it
    ep_name = "execname"
    ep_module = "foo"
    ep_attr = "main"

    distr = path_distribution()
    distr.add_console_scripts(((ep_name, ep_module, ep_attr),))
    distr.make()

    distr_no_ep = path_distribution("bar")
    distr_no_ep.make()

    distrs = [distr.location, distr_no_ep.location]

    mocker.patch.object(console_scripts.sys, "executable", sys_exec)
    mock_distributions.return_value = distributions(path=distrs)
    mock_scriptsdir.return_value = str(bindir)
    console_scripts.install_console_scripts()

    # check logging
    captured = capsys.readouterr()
    expected_msg = f"Generating script {ep_name} into {bindir}\n"
    assert captured.out == expected_msg
    assert captured.err == ""

    # check content of bindir
    assert {f.name for f in bindir.iterdir()} == {ep_name}

    # check content
    script = bindir / ep_name
    expected_content = console_scripts.SCRIPT_TEMPLATE.format(
        shebang=expected_shebang, module=ep_module, attr=ep_attr, main=ep_attr
    )
    assert script.read_text() == expected_content

    # run produced script
    new_env = os.environ.copy()
    new_env["PYTHONPATH"] = (
        str(distr.location) + os.pathsep + new_env.get("PYTHONPATH", "")
    )
    result = subprocess.run([script], capture_output=True, env=new_env)
    assert result.returncode == 0
    assert result.stdout == b"Hello, World!\n"
    assert result.stderr == b""
