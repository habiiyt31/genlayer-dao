import os

_PACKAGE_PATH = os.path.dirname(__file__)

def get_package_path():
    return _PACKAGE_PATH

def list_contracts():
    return ["proposal", "grant", "bounty", "veto"]
