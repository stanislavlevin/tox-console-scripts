# tox-console-scripts plugin ![CI](https://github.com/stanislavlevin/tox-console-scripts/workflows/CI/badge.svg)

It's possible to use system site packages within Python virtual environment,
but there is no way to install console or gui scripts into such environment.

With the help of this plugin the corresponding scripts will be automatically
generated for all of system site packages.

This is mostly used for testing purposes in ALTLinux during RPM build of Python
packages to run integration tests against the repository packages.

Usage
-----

The two possible options may be provided with:

1) `tox.ini` configuration file
```
[testenv]
console_scripts = True
```

2) command line option
```
tox --console-scripts
```

Note: both require `sitepackages`.

License
-------

Distributed under the terms of the **MIT** license, `tox-console-scripts` is
free and open source software.
