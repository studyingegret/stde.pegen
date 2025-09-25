#!/usr/bin/env python
"""
Utility for generating grammar parsers with backup functionality
"""
import argparse
import shutil
import subprocess
import sys
import os
import colorama

# Path configurations
LEGACY_METAGRAMMAR = "src/stde/pegen/legacy/metagrammar.gram"
LEGACY_OUTPUT = "src/stde/pegen/legacy/grammar_parser.py"
V2_METAGRAMMAR = "src/stde/pegen/v2/metagrammar.gram"
V2_OUTPUT = "src/stde/pegen/v2/grammar_parser.py"

RED = colorama.Fore.LIGHTRED_EX
GREEN = colorama.Fore.LIGHTGREEN_EX
WHITE = colorama.Fore.LIGHTWHITE_EX
MAGENTA = colorama.Fore.MAGENTA
BOLD = colorama.Style.BRIGHT
NORMAL = colorama.Style.NORMAL
RESET = colorama.Fore.RESET

p = argparse.ArgumentParser(
    description="Generate grammar parser with backup functionality")
p.add_argument("version", choices=["legacy", "v2"],
               help="Parser version to generate")
p.add_argument("-v", "--verbose", action="count", default=0,
               help="Verbosity level (use -v, -vv, etc.)")
p.add_argument("-g", "--generations", type=int, default=2,
               help="Number of generations to run (default: 2, see CONTRIBUTING.md for why)")
p.add_argument("args", nargs="*", # NOT argparse.REMAINDER! It's no good
               help="Arguments to pass to generator (precede with '--')")


def backup_file(file_path):
    """Create backup of file if it exists"""
    backup_path = f"{file_path}.bak" #XXX:...
    shutil.copy2(file_path, backup_path)
    print(f"Backed up {file_path} -> {backup_path}")
    return backup_path


def restore_backup(original_path, backup_path):
    """Restore file from backup"""
    shutil.copy2(backup_path, original_path)
    print(f"Restored from backup {original_path} <- {backup_path}")


def main(args):
    colorama.just_fix_windows_console()
    if args.version == "legacy":
        metagrammar = LEGACY_METAGRAMMAR
        output = LEGACY_OUTPUT
        version_flag = None
    else:
        metagrammar = V2_METAGRAMMAR
        output = V2_OUTPUT
        version_flag = "-v2"
    if not os.path.exists(metagrammar):
        print(f"Error: Metagrammar file not found at {metagrammar}")
        return 1

    if not os.path.exists(output):
        print(f"Skipping backing up output file {output} as it doesn't exist")
        backup_path = None
    else:
        backup_path = backup_file(output)
    # Generate parser
    cmd = [sys.executable, "-m", "stde.pegen", metagrammar, "-o", output]
    if version_flag:
        cmd.append(version_flag)
    
    #cmd.append("-" + ("q" if not args.verbose else "v" * (args.verbose-1)))
    if args.verbose:
        cmd.append("-" + "v" * args.verbose)
    cmd.extend(args.args)
    #raise
    for i in range(1, args.generations + 1):
        print(f"{WHITE}{BOLD}Generation {i}/{args.generations}: {' '.join(cmd)}{RESET}{NORMAL}")
        result = subprocess.run(cmd)
        if result.returncode:
            print(f"{RED}{BOLD}Error: Generation {i} failed with code {result.returncode}{RESET}{NORMAL}")
            if backup_path:
                restore_backup(output, backup_path)
            return result.returncode
        #XXX: Use first result as backup if backup_path initially None?

    print(f"{GREEN}{BOLD}Generation successful!{RESET}{NORMAL}")
    return 0

if __name__ == "__main__":
    main(p.parse_args())