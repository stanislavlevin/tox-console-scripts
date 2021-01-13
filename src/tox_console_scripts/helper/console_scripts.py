import argparse
import os
import site
import sys
import pkg_resources

from setuptools.command.easy_install import ScriptWriter


def write_script(script_name, content, envbindir):
    target = os.path.join(envbindir, script_name)
    print(f"Installing {script_name} script to {envbindir}")
    with open(target, "w") as dst:
        dst.write(content)
        os.fchmod(dst.fileno(), 0o755)


def main(envbindir, deps):
    if not deps:
        # nothing to do
        return

    wset = pkg_resources.WorkingSet()
    sitepackagedirs = site.getsitepackages([sys.base_prefix])
    for dep in deps:
        dist = wset.by_key[dep]
        if wset.by_key[dep].location not in sitepackagedirs:
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
