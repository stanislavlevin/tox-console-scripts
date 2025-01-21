from importlib.metadata import distributions
import logging
import site
import sys

from pyproject_installer.lib.normalization import pep503_normalized_name
from pyproject_installer.lib.scripts import generate_entrypoints_scripts

from tox.plugin import impl


logger = logging.getLogger(__name__)


def distr_name(distr):
    """`name` added in importlib.metadata 3.3.0 and Python 3.10"""
    try:
        return distr.name
    except AttributeError:
        return distr.metadata["Name"]


@impl
def tox_add_option(parser):
    parser.add_argument(
        "--console-scripts",
        action="store_true",
        help=(
            "create console_scripts of system and user site packages for "
            "virtual envs having access to globally installed packages"
        ),
    )


@impl
def tox_on_install(tox_env, arguments, section, of_type):
    if not all(
        (
            tox_env.options.console_scripts,
            tox_env.conf["sitepackages"],
            section == "PythonRun",
            of_type == "deps",
        )
    ):
        return

    logger.info("installing console scripts")
    install_console_scripts(
        tox_env.conf["env_python"], tox_env.conf["env_bin_dir"]
    )


def install_console_scripts(env_python, env_bin_dir):
    """
    Install console_scripts of system and user site packages

    All python scripts should point to virtual env's Python interpreter to
    be run in correct environment.

    According to
    https://peps.python.org/pep-0405/#isolation-from-system-site-packages:
    PEP 370 user-level site-packages are considered part of the system
    site-packages for venv purposes: they are not available from an
    isolated venv, but are available from an
    include-system-site-packages = true venv.

    1) install console scripts of packages:
    system site packages - user site packages
    2) install console scripts of packages:
    user site packages
    """
    ssp_paths = site.getsitepackages([sys.base_prefix])
    ssds = {
        pep503_normalized_name(distr_name(x)): x
        for x in distributions(path=ssp_paths)
    }

    # user site packages can be either a string or None
    usp_path = site.getusersitepackages()
    usp_paths = [] if usp_path is None else [usp_path]
    usds = {
        pep503_normalized_name(distr_name(x)): x
        for x in distributions(path=usp_paths)
    }

    logger.info("generating console scripts of system packages")
    for name in ssds.keys() - usds.keys():
        generate_entrypoints_scripts(
            ssds[name],
            python=str(env_python),
            scriptsdir=env_bin_dir,
            destdir="/",
        )

    logger.info("generating console scripts of user packages")
    for distr in usds.values():
        generate_entrypoints_scripts(
            distr,
            python=str(env_python),
            scriptsdir=env_bin_dir,
            destdir="/",
        )
