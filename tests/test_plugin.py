from importlib.metadata import distributions
import site
import sys

import pytest

from tox_console_scripts import __version__
from tox_console_scripts.plugin import distr_name


def globally_installed(name):
    paths = site.getsitepackages([sys.base_prefix])
    usp_path = site.getusersitepackages()
    if usp_path:
        paths.append(usp_path)

    return any(
        True
        for d in distributions(path=paths)
        if distr_name(d) and distr_name(d).lower() == name
    )


def test_help(tox_project):
    """
    - run tox --help
    - check if return code is 0
    - check if output contains --console-scripts option
    """
    result = tox_project().run(["--help"])
    assert not result.returncode
    assert " --console-scripts " in result.stdout
    assert not result.stderr


def test_version(tox_project):
    """
    - run tox --version
    - check if return code is 0
    - check if output contains plugin name and its version
    """
    result = tox_project().run(["--version"])
    assert not result.returncode
    expected_version = "tox-console-scripts-" + __version__
    assert expected_version in result.stdout
    assert not result.stderr


@pytest.mark.skipif(
    not globally_installed("pytest"),
    reason="requires globally installed pytest (venv console script)",
)
@pytest.mark.skipif(
    not globally_installed("setuptools"),
    reason="requires globally installed setuptools (venv build backend)",
)
def test_plugin_usage(tox_project):
    """
    - assume there are installed package (pytest) and build backend (setuptools)
      in system/user site packages
    - run tox with --console-scripts
    - check if console script works
    - check if output contains the only related record
    - check the generated script for the marker
    """
    project = tox_project()
    expected_console_script = "pytest"
    env_name = "py"
    project.contents[
        "tox.ini"
    ] = f"""\
        [tox]
        env_list = {env_name}
        [testenv]
        commands = {expected_console_script} --help
        """
    project.create()
    result = project.run(["-v", "--console-scripts"])
    assert not result.returncode
    assert not result.stderr

    # must be only installed for run environments
    assert result.stdout.count("installing console scripts") == 1

    # assume tox default paths
    envbindir = project.location / ".tox" / env_name / "bin"
    expected_script = envbindir / expected_console_script
    assert expected_script.exists()


@pytest.mark.skipif(
    not globally_installed("pytest"),
    reason="requires globally installed pytest (venv console script)",
)
@pytest.mark.skipif(
    not globally_installed("setuptools"),
    reason="requires globally installed setuptools (venv build backend)",
)
def test_no_plugin_usage(tox_project):
    """
    - assume there are installed package (pytest) and build backend (setuptools)
      in system/user site packages
    - run tox without --console-scripts
    - check if output doesn't contain any related record
    - check if console script was not generated
    """
    project = tox_project()
    expected_console_script = "pytest"
    env_name = "py"
    project.contents[
        "tox.ini"
    ] = f"""\
        [tox]
        env_list = {env_name}
        [testenv]
        commands=python -c "print('Hello, hello')"
        """
    project.create()
    result = project.run(["-v"])
    assert not result.returncode
    assert not result.stderr
    assert not result.stdout.count("installing console scripts")

    # assume tox default paths
    envbindir = project.location / ".tox" / env_name / "bin"
    expected_script = envbindir / expected_console_script
    assert not expected_script.exists()


@pytest.mark.skipif(
    not globally_installed("pytest"),
    reason="requires globally installed pytest (venv console script)",
)
def test_plugin_usage_no_systemsite(tox_project):
    """
    - assume there are installed package (pytest) and build backend (setuptools)
      in system/user site packages
    - run tox with --console-scripts
    - check if output doesn't contain any related record
    - check if console script was not generated
    """
    project = tox_project()
    expected_console_script = "pytest"
    env_name = "py"
    project.contents[
        "tox.ini"
    ] = f"""\
        [tox]
        env_list = {env_name}
        [testenv]
        # don't build package (no available build backend)
        package = skip
        # overrides the default that was set by VIRTUALENV_SYSTEM_SITE_PACKAGES
        system_site_packages = False
        commands=python -c "print('Hello, hello')"
        """
    project.create()
    result = project.run(["-v", "--console-scripts"])
    assert not result.returncode
    assert not result.stderr
    assert not result.stdout.count("installing console scripts")

    # assume tox default paths
    envbindir = project.location / ".tox" / env_name / "bin"
    expected_script = envbindir / expected_console_script
    assert not expected_script.exists()
