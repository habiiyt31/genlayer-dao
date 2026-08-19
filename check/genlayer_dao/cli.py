import os
import sys
import shutil
import genlayer_dao

CONTRACTS = {
    "proposal": "dao_proposal.py",
    "grant":    "dao_grant.py",
    "bounty":   "dao_bounty.py",
    "veto":     "dao_veto.py",
}


def copy_file(src, dst):
    shutil.copy(src, dst)
    print(f"  dao: {os.path.basename(dst)}")


def main():
    args = sys.argv[1:]

    package_path = genlayer_dao.get_package_path()
    target_dir = os.path.abspath("contracts")
    os.makedirs(target_dir, exist_ok=True)

    if args and args[0] == "list":
        print("Available contracts:")
        for k, v in CONTRACTS.items():
            print(f"  {k:<12} -> {v}")
        return

    if len(args) == 0 or args[0] == "init":
        selected = None if len(args) <= 1 else args[1]
    else:
        selected = args[0]

    if selected:
        selected = selected.lower()
        if selected not in CONTRACTS:
            print(f"Unknown contract: '{selected}'")
            print(f"Available: {', '.join(CONTRACTS.keys())}")
            sys.exit(1)

        file = CONTRACTS[selected]
        src = os.path.join(package_path, file)
        dst = os.path.join(target_dir, file)
        copy_file(src, dst)
        print(f"\n  {selected} ready in contracts/")
        return

    print("Copying all DAO contracts to contracts/ ...\n")
    for file in CONTRACTS.values():
        src = os.path.join(package_path, file)
        dst = os.path.join(target_dir, file)
        copy_file(src, dst)

    print("\n  All 4 contracts ready!")
    print("\n  contracts/")
    for f in CONTRACTS.values():
        print(f"    {f}")
