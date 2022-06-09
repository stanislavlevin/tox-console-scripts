from importlib.metadata import distributions
from pathlib import Path
import site
import sys
import sysconfig


SCRIPT_TEMPLATE = """\
{shebang}

import sys

from {module} import {attr}


if __name__ == "__main__":
    sys.exit({main}())
"""


def build_shebang():
    """
    man 2 execve
    The kernel imposes a maximum length on the text that follows the "#!" char‐
    acters  at  the  start of a script; characters beyond the limit are ignored.
    Before Linux 5.1, the limit is 127 characters.  Since Linux 5.1,  the  limit
    is 255 characters.
    """
    executable = sys.executable
    if " " not in executable and len(executable) <= 127:
        return f"#!{sys.executable}"

    # originally taken from distlib.scripts; how it works:
    # https://github.com/pradyunsg/installer/pull/4#issuecomment-623668717
    return "#!/bin/sh\n'''exec' " + executable + ' "$0" "$@"\n' + "' '''"


def parse_entry_points(distr, group):
    """
    Compat only.
    - module and attr attributes of ep are available since Python 3.9
    - "selectable" entry points were introduced in Python 3.10
    """
    distr_eps = distr.entry_points
    try:
        # since Python3.10
        distr_eps.select
    except AttributeError:
        eps = (ep for ep in distr_eps if ep.group == group)
    else:
        eps = distr_eps.select(group=group)

    for ep in eps:
        try:
            # module is available since Python 3.9
            ep_module = ep.module
        except AttributeError:
            ep_match = ep.pattern.match(ep.value)
            ep_module = ep_match.group("module")

        try:
            # attr is available since Python 3.9
            ep_attr = ep.attr
        except AttributeError:
            ep_attr = ep_match.group("attr")

        yield (ep.name, ep_module, ep_attr)


def generate_entrypoints_scripts(distr):
    scripts_path = Path(sysconfig.get_path("scripts"))

    for ep_group in ("console_scripts", "gui_scripts"):
        for ep_name, ep_module, ep_attr in parse_entry_points(distr, ep_group):
            print(f"Generating script {ep_name} into {scripts_path}")
            scripts_path.mkdir(parents=True, exist_ok=True)
            script_path = scripts_path / ep_name
            script_text = SCRIPT_TEMPLATE.format(
                shebang=build_shebang(),
                module=ep_module,
                attr=ep_attr.split(".", maxsplit=1)[0],
                main=ep_attr,
            )
            script_path.write_text(script_text, encoding="utf-8")
            script_path.chmod(script_path.stat().st_mode | 0o555)


def install_console_scripts():
    """Unconditionally installs console_scripts of all system site packages"""
    systemsitepackages_paths = site.getsitepackages([sys.base_prefix])
    systemsitedistrs = distributions(path=systemsitepackages_paths)

    for distr in systemsitedistrs:
        generate_entrypoints_scripts(distr)


if __name__ == "__main__":
    install_console_scripts()
