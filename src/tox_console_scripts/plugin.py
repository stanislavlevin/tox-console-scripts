import os

from tox import exception, reporter
import pluggy


hookimpl = pluggy.HookimplMarker("tox")

_HELPER_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "helper")
CONSOLE_SCRIPTS = os.path.join(_HELPER_DIR, "console_scripts.py")


@hookimpl
def tox_addoption(parser):
    parser.add_argument(
        "--console-scripts",
        action="store_true",
        help="create console_scripts of system site packages within env(requires "
        "--sitepackages)",
    )

    def console_scripts(testenv_config, value):
        return testenv_config.config.option.console_scripts or value

    parser.add_testenv_attribute(
        name="console_scripts",
        type="bool",
        default=False,
        postprocess=console_scripts,
        help="Set to ``True`` if you want to create console_scripts of system site "
        "packages within env(requires --sitepackages)",
    )


@hookimpl
def tox_configure(config):
    for _, envconfig in config.envconfigs.items():
        if envconfig.console_scripts and not envconfig.sitepackages:
            raise exception.ConfigError(
                "console_scripts option requires enabled sitepackages"
            )


@hookimpl(hookwrapper=True, tryfirst=True)
def tox_testenv_install_deps(venv, action):
    # execute non-wrapper plugins
    yield
    if not venv.envconfig.console_scripts:
        # nothing to do
        return

    envbindir = venv.envconfig.get_envbindir()
    args = [
        venv.envconfig.get_envpython(),
        CONSOLE_SCRIPTS,
        "--bindir",
        envbindir,
    ]

    deps = venv.get_resolved_dependencies()
    args.extend(deps)

    venv._pcall(
        args,
        cwd=venv.envconfig.config.toxinidir,
        action=action,
        redirect=reporter.verbosity() < reporter.Verbosity.DEBUG,
    )
