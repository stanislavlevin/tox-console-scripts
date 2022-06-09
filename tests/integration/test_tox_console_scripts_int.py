from pathlib import Path
import os
import sys

import pytest


def assert_console_script_installed_once(script_name, path, outlines):
    expected = f"Generating script {script_name} into {path}"
    matches = [l for l in outlines if l == expected]
    assert len(matches) == 1, outlines


def assert_shebang(script, expected_shebang):
    with open(script) as f:
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


def test_no_plugin_usage(initproj, cmd):
    """Plugin doesn't break regular tox"""
    initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                commands=python -c "print('test')"
            """,
        },
    )
    result = cmd()
    result.assert_success()


def test_cmd_sitepackages_cmd(initproj, cmd):
    initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                commands=python -c "print('test')"
            """,
        },
    )
    result = cmd("--console-scripts", "--sitepackages")
    result.assert_success()


def test_cmd_sitepackages_config(initproj, cmd):
    initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                sitepackages = True
                commands=python -c "print('test')"
            """,
        },
    )
    result = cmd("--console-scripts")
    result.assert_success()


def test_cmd_nositepackages(initproj, cmd):
    initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                commands=python -c "print('test')"
            """,
        },
    )
    result = cmd("--console-scripts")
    result.assert_fail()
    assert "console_scripts option requires enabled sitepackages" in result.err


def test_config_sitepackages_cmd(initproj, cmd):
    initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                console_scripts = True
                commands=python -c "print('test')"
            """,
        },
    )
    result = cmd("--sitepackages")
    result.assert_success()


def test_config_sitepackages_config(initproj, cmd):
    initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                console_scripts = True
                sitepackages = True
                commands=python -c "print('test')"
            """,
        },
    )
    result = cmd()
    result.assert_success()


def test_config_nositepackages(initproj, cmd):
    initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                console_scripts = True
                commands=python -c "print('test')"
            """,
        },
    )
    result = cmd()
    result.assert_fail()
    assert "console_scripts option requires enabled sitepackages" in result.err


def test_deps_skipsdist(system_distribution, initproj, cmd):
    distr = system_distribution()
    distr.make()

    pkg_dir = initproj(
        "pkg123",
        filedefs={
            "tox.ini": """\
                [tox]
                skipsdist = True
                [testenv]
                deps =
                    foo>=1.0
                commands={envbindir}/foo_script
            """
        },
    )

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=result.outlines
    )
    # result of main function
    assert "Hello, World!" in result.outlines

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_no_deps_skipsdist(system_distribution, initproj, cmd):
    distr = system_distribution()
    distr.make()

    pkg_dir = initproj(
        "pkg123",
        filedefs={
            "tox.ini": """\
                [tox]
                skipsdist = True
                [testenv]
                commands={envbindir}/foo_script
            """
        },
    )

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=result.outlines
    )
    # result of main function
    assert "Hello, World!" in result.outlines

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_install_requires(system_distribution, initproj, cmd):
    distr = system_distribution()
    distr.make()

    pkg_dir = initproj(
        "my_test_pkg",
        filedefs={
            "setup.cfg": """\
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
            """,
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
            "tox.ini": """\
                [tox]
                [testenv]
                commands={envbindir}/foo_script
            """,
        },
    )

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=result.outlines
    )
    # result of main function
    assert "Hello, World!" in result.outlines

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_install_requires_usedevelop(system_distribution, initproj, cmd):
    distr = system_distribution()
    distr.make()

    pkg_dir = initproj(
        "my_test_pkg",
        filedefs={
            "setup.cfg": """\
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
            """,
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
            "tox.ini": """\
                [tox]
                [testenv]
                usedevelop=true
                commands={envbindir}/foo_script
            """,
        },
    )

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=result.outlines
    )
    # result of main function
    assert "Hello, World!" in result.outlines

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)


def test_extra_usedevelop(system_distribution, initproj, cmd):
    distr = system_distribution()
    distr.make()

    pkg_dir = initproj(
        "my_test_pkg",
        filedefs={
            "setup.cfg": """\
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
            """,
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
            "tox.ini": """\
                [tox]
                [testenv]
                extras =
                    tests
                usedevelop=true
                commands={envbindir}/foo_script
            """,
        },
    )

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()

    envbindir = (Path(".tox") / "python" / "bin").resolve()
    assert_console_script_installed_once(
        "foo_script", path=envbindir, outlines=result.outlines
    )
    # result of main function
    assert "Hello, World!" in result.outlines

    expected_shebang = f"#!{envbindir / 'python'}\n"
    assert_shebang(envbindir / "foo_script", expected_shebang)
