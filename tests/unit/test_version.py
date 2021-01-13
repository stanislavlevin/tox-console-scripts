def test_version():
    pkg = __import__("tox_console_scripts", fromlist=["__version__"])
    assert pkg.__version__
