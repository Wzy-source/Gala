from solc_select.solc_select import switch_global_version, install_artifacts, installed_versions, get_available_versions


class SolcSwitcher:
    def __init__(self):
        pass

    @staticmethod
    def switch(version):
        # some old versions of solc, e.g., 0.3.2 are not available.
        if version not in get_available_versions().keys():
            print(f"Solc version: `{version}` unavailable.")
        # install target solc version if it does not exist in the local environment
        if version not in installed_versions():
            install_artifacts(version)
        # switch to the compiler of target version
        switch_global_version(version, True)
