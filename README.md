# tox-console-scripts plugin ![CI](https://github.com/stanislavlevin/tox-console-scripts/workflows/CI/badge.svg)

It's possible to have access to system or user site packages within Python
virtual environment. But there is no way to run console scripts in the
context of such environments.

With the help of this plugin the console scripts of all of the system and user
site packages are automatically generated for tox' test virtual environments
having access to globally installed packages.

This is mostly used for testing purposes in ALTLinux during RPM build of Python
packages to run integration tests against repository packages.

Usage
-----

```
tox --console-scripts
```

Note: this requires virtual environments having access to globally installed
packages (see for details: [sitepackages](https://tox.wiki/en/latest/config.html#sitepackages))

License
-------

Distributed under the terms of the **MIT** license, `tox-console-scripts` is
free and open source software.
