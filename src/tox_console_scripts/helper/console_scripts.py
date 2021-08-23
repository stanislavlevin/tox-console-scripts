import os
import site
import sys
import sysconfig

from pkg_resources import WorkingSet
from setuptools.command.easy_install import ScriptWriter


def write_script(script_name, content, envbindir):
    print(f"Installing {script_name} script to {envbindir}")
    target = os.path.join(envbindir, script_name)
    with open(target, encoding="utf-8", mode="w") as dst:
        dst.write(content)
        os.fchmod(dst.fileno(), 0o755)


def install_console_scripts():
    """Unconditionally installs console_scripts of all system site packages"""
    scripts_dir = sysconfig.get_path("scripts")
    envbindir = os.path.relpath(scripts_dir)

    wset = WorkingSet()
    systemsitepackages_paths = site.getsitepackages([sys.base_prefix])
    systemsitedists = []

    for systemsitepackages_path in systemsitepackages_paths:
        systemsitepackages = wset.entry_keys.get(systemsitepackages_path)
        if systemsitepackages:
            for systemsitepackage in systemsitepackages:
                dist = wset.by_key[systemsitepackage]
                systemsitedists.append(dist)

    for dist in systemsitedists:
        for args in ScriptWriter.best().get_args(dist):
            write_script(*args, envbindir=envbindir)


if __name__ == "__main__":
    install_console_scripts()
