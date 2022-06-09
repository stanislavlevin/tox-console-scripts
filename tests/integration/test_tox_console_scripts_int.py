import os
import sys
import subprocess

import pytest


def assert_console_script_installed_once(script_name, path, outlines):
    expected = f"Generating script {script_name} into {path}"
    matches = [l for l in outlines if l == expected]
    assert len(matches) == 1, outlines


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


@pytest.fixture
def systemsitepackage(systempackage):
    """Install typical system site package, which has console_scripts

    Warning: there is no cleanup! Packages and scripts installed by this
    fixture are keeped.
    """

    def systemsitepackage_(name, version, install_requires="", console_scripts=True):
        console_scripts_content = ""
        if console_scripts:
            console_scripts_content = f"{name}_script={name}:main"

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
                    install_requires =
                        {install_requires}

                    [options.packages.find]
                    where = .

                    [options.entry_points]
                    console_scripts =
                        {console_scripts_content}
                """.format(
                    name=name,
                    version=version,
                    install_requires=install_requires,
                    console_scripts_content=console_scripts_content,
                ),
                "setup.py": """\
                    from setuptools import setup
                    if __name__ == "__main__":
                        setup()
                """,
            },
        )

    yield systemsitepackage_


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


def test_deps_skipsdist(systemsitepackage, initproj, cmd):
    sitepkg = "mysitepackage"
    version = "0.1"

    systemsitepackage(sitepkg, version)

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

    envpython_path = os.path.join(pkg_dir, envbindir, "python")
    expected_shebang = f"#!{envpython_path}\n"

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()
    assert_console_script_installed_once(
        f"{sitepkg}_script", path=envbindir, outlines=result.outlines
    )

    assert os.path.isfile(sitepkgscript_path)
    with open(sitepkgscript_path) as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang


def test_no_deps_skipsdist(systemsitepackage, initproj, cmd):
    sitepkg = "mysitepackage"
    version = "0.1"

    systemsitepackage(sitepkg, version)

    pkg_dir = initproj(
        "pkg123",
        filedefs={
            "tox.ini": """
                [tox]
                skipsdist = True
                [testenv]
                commands={{envbindir}}/{name}_script
            """.format(
                name=sitepkg, version=version
            ),
        },
    )

    envbindir = os.path.join(".tox", "python", "bin")
    sitepkgscript_path = os.path.join(pkg_dir, envbindir, f"{sitepkg}_script")

    envpython_path = os.path.join(pkg_dir, envbindir, "python")
    expected_shebang = f"#!{envpython_path}\n"

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()
    assert_console_script_installed_once(
        f"{sitepkg}_script", path=envbindir, outlines=result.outlines
    )

    assert os.path.isfile(sitepkgscript_path)
    with open(sitepkgscript_path) as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang


def test_install_requires(systemsitepackage, initproj, cmd):
    sitepkg = "mysitepackage"
    pkg = "my-test-pkg"
    version = "0.1"

    systemsitepackage(sitepkg, version)

    pkg_dir = initproj(
        pkg,
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
                    {sitepkg}

                [options.packages.find]
                where = .
            """.format(
                name=pkg, sitepkg=sitepkg, version=version
            ),
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
            "tox.ini": """
                [tox]
                [testenv]
                commands={{envbindir}}/{sitepkg}_script
            """.format(
                sitepkg=sitepkg
            ),
        },
    )

    envbindir = os.path.join(".tox", "python", "bin")
    sitepkgscript_path = os.path.join(pkg_dir, envbindir, f"{sitepkg}_script")

    envpython_path = os.path.join(pkg_dir, envbindir, "python")
    expected_shebang = f"#!{envpython_path}\n"

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()
    assert_console_script_installed_once(
        f"{sitepkg}_script", path=envbindir, outlines=result.outlines
    )

    assert os.path.isfile(sitepkgscript_path)
    with open(sitepkgscript_path) as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang


def test_install_requires_usedevelop(systemsitepackage, initproj, cmd):
    sitepkg = "mysitepackage"
    pkg = "my-test-pkg"
    version = "0.1"

    systemsitepackage(sitepkg, version)

    pkg_dir = initproj(
        pkg,
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
                    {sitepkg}

                [options.packages.find]
                where = .
            """.format(
                name=pkg, sitepkg=sitepkg, version=version
            ),
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
            "tox.ini": """
                [tox]
                [testenv]
                usedevelop=true
                commands={{envbindir}}/{sitepkg}_script
            """.format(
                sitepkg=sitepkg
            ),
        },
    )

    envbindir = os.path.join(".tox", "python", "bin")
    sitepkgscript_path = os.path.join(pkg_dir, envbindir, f"{sitepkg}_script")

    envpython_path = os.path.join(pkg_dir, envbindir, "python")
    expected_shebang = f"#!{envpython_path}\n"

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()
    assert_console_script_installed_once(
        f"{sitepkg}_script", path=envbindir, outlines=result.outlines
    )

    assert os.path.isfile(sitepkgscript_path)
    with open(sitepkgscript_path) as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang


def test_extra_usedevelop(systemsitepackage, initproj, cmd):
    sitepkg = "mysitepackage"
    pkg = "my-test-pkg"
    version = "0.1"

    systemsitepackage(sitepkg, version)

    pkg_dir = initproj(
        pkg,
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

                [options.packages.find]
                where = .

                [options.extras_require]
                tests =
                    {sitepkg}
            """.format(
                name=pkg, sitepkg=sitepkg, version=version
            ),
            "setup.py": """\
                from setuptools import setup
                if __name__ == "__main__":
                    setup()
            """,
            "tox.ini": """
                [tox]
                [testenv]
                extras =
                    tests
                usedevelop=true
                commands={{envbindir}}/{sitepkg}_script
            """.format(
                sitepkg=sitepkg
            ),
        },
    )

    envbindir = os.path.join(".tox", "python", "bin")
    sitepkgscript_path = os.path.join(pkg_dir, envbindir, f"{sitepkg}_script")

    envpython_path = os.path.join(pkg_dir, envbindir, "python")
    expected_shebang = f"#!{envpython_path}\n"

    result = cmd("--console-scripts", "--sitepackages", "-vv")
    result.assert_success()
    assert_console_script_installed_once(
        f"{sitepkg}_script", path=envbindir, outlines=result.outlines
    )

    assert os.path.isfile(sitepkgscript_path)
    with open(sitepkgscript_path) as f:
        actual_shebang = f.readline()

    assert actual_shebang == expected_shebang
