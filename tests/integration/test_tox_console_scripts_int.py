import os
import sys
import subprocess

import pytest


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


@pytest.fixture
def systempackage(initproj):
    """Install custom package into systemsite

    Warning: there is no cleanup! Packages and scripts installed by this
    fixture are keeped.
    """
    if os.geteuid() != 0:
        pytest.skip("Requires root privileges")

    basepython = os.environ.get("CONSOLE_SCRIPTS_BASEPYTHON")
    if basepython is None:
        raise ValueError(
            "Systemwide Python interpreter path(via CONSOLE_SCRIPTS_BASEPYTHON"
            " env variable) is required."
        )

    def systempackage_(name, version, filedefs):
        initproj((name, version), filedefs=filedefs)
        args = [
            basepython,
            "setup.py",
            "install",
            "--root",
            "/",
            "--prefix",
            sys.base_prefix,
            "--force",
        ]
        subprocess.run(args, check=True)

    yield systempackage_


def test_console_scripts_indirect_systemdep(systempackage, initproj, cmd):
    sitepkg = "mysitepackage"
    sitepkg_indirect = "myindirectsitepackage"
    version = "0.1"

    systempackage(
        sitepkg_indirect,
        version,
        filedefs={
            sitepkg_indirect: {
                "__init__.py": """\
                    __version__ = {version}

                    def main():
                        print("Test!")
                """.format(
                    version=version
                ),
            },
            "setup.cfg": """\
                [metadata]
                name = {name}
                description = {name} project
                version = {version}
                license = MIT
                platforms = unix

                [options]
                packages = find:

                [options.packages.find]
                where = .

                [options.entry_points]
                console_scripts =
                    {name}_script={name}:main
            """.format(
                name=sitepkg_indirect, version=version
            ),
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
        },
    )

    systempackage(
        sitepkg,
        version,
        filedefs={
            "setup.cfg": """\
                [metadata]
                name = {name}
                description = {name} project
                version = {version}
                license = MIT
                platforms = unix

                [options]
                packages = find:
                install_requires =
                    {sitepkg_indirect}

                [options.packages.find]
                where = .
            """.format(
                name=sitepkg, sitepkg_indirect=sitepkg_indirect, version=version
            ),
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
        },
    )

    pkg_dir = initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = true
                [testenv]
                deps =
                    {sitepkg}>={version}
                commands={{envbindir}}/{sitepkg_indirect}_script
            """.format(
                sitepkg=sitepkg, sitepkg_indirect=sitepkg_indirect, version=version
            ),
        },
    )

    envbindir = os.path.join(".tox", "python", "bin")
    sitepkgscript_path = os.path.join(pkg_dir, envbindir, f"{sitepkg_indirect}_script")

    envpython_path = os.path.join(pkg_dir, envbindir, "python")
    expected_shebang = f"#!{envpython_path}\n"

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()
    assert f"Installing {sitepkg_indirect}_script script to {envbindir}" in result.out

    assert os.path.isfile(sitepkgscript_path)
    with open(sitepkgscript_path) as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang


def test_console_scripts(systempackage, initproj, cmd):
    sitepkg = "mysitepackage"
    sitepkg_extra = "myextrasitepackage"
    version = "0.1"

    for name in (sitepkg, sitepkg_extra):
        systempackage(
            name,
            version,
            filedefs={
                name: {
                    "__init__.py": """\
                        __version__ = {version}

                        def main():
                            print("Test!")
                    """.format(
                        version=version
                    ),
                },
                "setup.cfg": """\
                    [metadata]
                    name = {name}
                    description = {name} project
                    version = {version}
                    license = MIT
                    platforms = unix

                    [options]
                    packages = find:

                    [options.packages.find]
                    where = .

                    [options.entry_points]
                    console_scripts =
                        {name}_script={name}:main
                """.format(
                    name=name, version=version
                ),
                "setup.py": """\
                    from setuptools import setup
                    if __name__ == "__main__":
                        setup()
                """,
            },
        )

    pkg_dir = initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                deps =
                    {name}>={version}
                commands={{envbindir}}/{name}_script
            """.format(
                name=sitepkg, version=version
            ),
        },
    )

    envbindir = os.path.join(".tox", "python", "bin")
    sitepkgscript_path = os.path.join(pkg_dir, envbindir, f"{sitepkg}_script")
    extrasitepkgscript_path = os.path.join(
        pkg_dir, envbindir, f"{sitepkg_extra}_script"
    )

    envpython_path = os.path.join(pkg_dir, envbindir, "python")
    expected_shebang = f"#!{envpython_path}\n"

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()
    assert f"Installing {sitepkg}_script script to {envbindir}" in result.out
    assert f"Installing {sitepkg_extra}_script script to {envbindir}" not in result.out

    assert os.path.isfile(sitepkgscript_path)
    with open(sitepkgscript_path) as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang

    assert not os.path.isfile(extrasitepkgscript_path)
