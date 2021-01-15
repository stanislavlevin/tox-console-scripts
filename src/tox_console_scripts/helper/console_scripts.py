import argparse
import os
import site
import sys

from pkg_resources import Requirement, WorkingSet
from setuptools.command.easy_install import ScriptWriter


def write_script(script_name, content, envbindir):
    print(f"Installing {script_name} script to {envbindir}")
    target = os.path.join(envbindir, script_name)
    with open(target, "w") as dst:
        dst.write(content)
        os.fchmod(dst.fileno(), 0o755)


def main(envbindir, deps):
    if not deps:
        # nothing to do
        return

    wset = WorkingSet()
    # at this point all dependencies must be resolved
    reqs = wset.resolve([Requirement.parse(dep) for dep in deps])
    sitepackagedirs = site.getsitepackages([sys.base_prefix])
    for dist in reqs:
        if dist.location not in sitepackagedirs:
            continue

        for args in ScriptWriter.best().get_args(dist):
            write_script(*args, envbindir=envbindir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bindir",
        required=True,
        help="path where to place the generated console scripts",
    )
    parser.add_argument(
        "deps",
        nargs="*",
        help="dependencies for which the console scripts should be generated",
    )
    options = parser.parse_args()

    main(options.bindir, deps=options.deps)
