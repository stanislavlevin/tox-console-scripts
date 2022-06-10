from pathlib import Path

import pytest


def assert_console_script_installed_once(script_name, path, outlines):
    expected = f"Generating script {script_name} into {path}"
    matches = [l for l in outlines if l == expected]
    assert len(matches) == 1, outlines


def assert_shebang(script, expected_shebang):
    with open(script, encoding="utf-8") as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    monkeypatch.setenv("PIP_NO_BUILD_ISOLATION", "NO")
    monkeypatch.setenv("PIP_NO_INDEX", "YES")
    monkeypatch.setenv("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    monkeypatch.setenv(
        "TOX_TESTENV_PASSENV",
        "PIP_NO_BUILD_ISOLATION PIP_NO_INDEX PIP_DISABLE_PIP_VERSION_CHECK",
    )


def test_no_plugin_usage(tox_project, tox):
    """Plugin doesn't break regular tox"""
    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        commands=python -c "print('Hello, hello')"
        """
    project.make()
    result = tox("-vv", cwd=project.location)
    assert result.returncode == 0
    assert b"Hello, hello" in result.stdout
    assert result.stderr == b""


def test_cmd_sitepackages_cmd(tox_project, tox):
    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        commands=python -c "print('Hello, hello')"
        """
    project.make()
    result = tox("--console-scripts", "--sitepackages", cwd=project.location)
    assert result.returncode == 0
    assert b"Hello, hello" in result.stdout
    assert result.stderr == b""


def test_cmd_sitepackages_config(tox_project, tox):
    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        sitepackages = True
        commands=python -c "print('Hello, hello')"
        """
    project.make()
    result = tox("--console-scripts", cwd=project.location)
    assert result.returncode == 0
    assert b"Hello, hello" in result.stdout
    assert result.stderr == b""


def test_cmd_nositepackages(tox_project, tox):
    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        commands=python -c "print('Hello, hello')"
        """
    project.make()
    result = tox("--console-scripts", cwd=project.location)
    assert result.returncode != 0
    assert b"console_scripts option requires enabled sitepackages" in result.stderr


def test_config_sitepackages_cmd(tox_project, tox):
    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        console_scripts = True
        commands=python -c "print('Hello, hello')"
        """
    project.make()
    result = tox("--sitepackages", cwd=project.location)
    assert result.returncode == 0
    assert b"Hello, hello" in result.stdout
    assert result.stderr == b""


def test_config_sitepackages_config(tox_project, tox):
    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        console_scripts = True
        sitepackages = True
        commands=python -c "print('Hello, hello')"
        """
    project.make()
    result = tox(cwd=project.location)
    assert result.returncode == 0
    assert b"Hello, hello" in result.stdout
    assert result.stderr == b""


def test_config_nositepackages(tox_project, tox):
    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        console_scripts = True
        commands=python -c "print('Hello, hello')"
        """
    project.make()
    result = tox(cwd=project.location)
    assert result.returncode != 0
    assert b"console_scripts option requires enabled sitepackages" in result.stderr


def test_deps_skipsdist(system_distribution, tox_project, tox):
    distr = system_distribution()
    distr.make()

    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        deps =
            foo>=1.0
        commands={envbindir}/foo_script
        """
    project.make()
    result = tox("--console-scripts", "--sitepackages", "-vv", cwd=project.location)
    assert result.returncode == 0
    assert result.stderr == b""
    stdout_lines = result.stdout.decode("utf-8").splitlines()
    # result of main function
    assert "Hello, World!" in stdout_lines

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=stdout_lines
    )

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_no_deps_skipsdist(system_distribution, tox_project, tox):
    distr = system_distribution()
    distr.make()

    project = tox_project()
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        skipsdist = True
        [testenv]
        commands={envbindir}/foo_script
        """
    project.make()
    result = tox("--console-scripts", "--sitepackages", "-vv", cwd=project.location)
    assert result.returncode == 0
    assert result.stderr == b""
    stdout_lines = result.stdout.decode("utf-8").splitlines()
    # result of main function
    assert "Hello, World!" in stdout_lines

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=stdout_lines
    )

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_install_requires(system_distribution, tox_project, tox):
    distr = system_distribution()
    distr.make()

    project = tox_project()
    project.contents[
        "setup.cfg"
    ] = """\
        [metadata]
        name = my_test_pkg
        description = my_test_pkg project
        version = 1.0
        license = MIT
        platforms = unix

        [options]
        packages = find:
        install_requires =
            foo

        [options.packages.find]
        where = .
        """
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        [testenv]
        commands={envbindir}/foo_script
        """
    project.make()
    result = tox("--console-scripts", "--sitepackages", "-vv", cwd=project.location)
    assert result.returncode == 0
    assert result.stderr == b""
    stdout_lines = result.stdout.decode("utf-8").splitlines()
    # result of main function
    assert "Hello, World!" in stdout_lines

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=stdout_lines
    )

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_install_requires_usedevelop(system_distribution, tox_project, tox):
    distr = system_distribution()
    distr.make()

    project = tox_project()
    project.contents[
        "setup.cfg"
    ] = """\
        [metadata]
        name = my_test_pkg
        description = my_test_pkg project
        version = 1.0.0
        license = MIT
        platforms = unix

        [options]
        packages = find:
        install_requires =
            foo

        [options.packages.find]
        where = .
        """
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        [testenv]
        usedevelop=true
        commands={envbindir}/foo_script
        """
    project.make()
    result = tox("--console-scripts", "--sitepackages", "-vv", cwd=project.location)
    assert result.returncode == 0
    assert result.stderr == b""
    stdout_lines = result.stdout.decode("utf-8").splitlines()
    # result of main function
    assert "Hello, World!" in stdout_lines

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=stdout_lines
    )

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_extra_usedevelop(system_distribution, tox_project, tox):
    distr = system_distribution()
    distr.make()

    project = tox_project()
    project.contents[
        "setup.cfg"
    ] = """\
        [metadata]
        name = my_test_pkg
        description = my_test_pkg project
        version = 1.0
        license = MIT
        platforms = unix

        [options]
        packages = find:

        [options.packages.find]
        where = .

        [options.extras_require]
        tests =
            foo
        """
    project.contents[
        "tox.ini"
    ] = """\
        [tox]
        [testenv]
        extras =
            tests
        usedevelop=true
        commands={envbindir}/foo_script
        """
    project.make()
    result = tox("--console-scripts", "--sitepackages", "-vv", cwd=project.location)
    assert result.returncode == 0
    assert result.stderr == b""
    stdout_lines = result.stdout.decode("utf-8").splitlines()
    # result of main function
    assert "Hello, World!" in stdout_lines

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=stdout_lines
    )

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)
