#!/usr/bin/env python
"""
Generate grammar parsers with backup functionality

See CONTRIBUTING.md for design details.
"""

import sys, os, argparse, shutil, subprocess, builtins
from typing import TYPE_CHECKING, Any, NamedTuple
from functools import partial

class _Colors(NamedTuple):
    RED: str = ""
    GREEN: str = ""
    WHITE: str = ""
    MAGENTA: str = ""
    BOLD: str = ""
    NORMAL: str = ""
    RESET: str = ""

class Colors(_Colors):
    @classmethod
    def null(cls):
        return cls()
    @property
    def RST(self):
        return self.RESET + self.NORMAL

try:
    import colorama # type:ignore[import-untyped]
    colors = Colors(
        colorama.Fore.LIGHTRED_EX,
        colorama.Fore.LIGHTGREEN_EX,
        colorama.Fore.LIGHTWHITE_EX,
        colorama.Fore.MAGENTA,
        colorama.Style.BRIGHT,
        colorama.Style.NORMAL,
        colorama.Fore.RESET
    )
    just_fix_windows_console = colorama.just_fix_windows_console
    has_colorama = True
except ImportError:
    colors = Colors()
    just_fix_windows_console = lambda: None
    has_colorama = False

# Path configurations
LEGACY_METAGRAMMAR = "src/stde/pegen/legacy/metagrammar.gram"
LEGACY_OUTPUT = "src/stde/pegen/legacy/grammar_parser.py"
LEGACY_BAD_OUTPUT = "src/stde/pegen/legacy/grammar_parser.bad.py"
V2_METAGRAMMAR = "src/stde/pegen/v2/metagrammar.gram"
V2_OUTPUT = "src/stde/pegen/v2/grammar_parser.py"
V2_BAD_OUTPUT = "src/stde/pegen/v2/grammar_parser.bad.py"


p = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    add_help=False)
g = p.add_argument_group("Positional arguments")
g.add_argument("version", choices=["legacy", "v2"],
               help="Parser version to generate")
g = p.add_argument_group("Options")
g.add_argument("-h", "--help", action="help",
               help="Show this help message and exit")
g.add_argument("-v", "--verbose", action="count", default=0,
               help="Verbosity level (use -v, -vv, etc.)")
g.add_argument("-g", "--generations", type=int, default=2,
               help="Number of generations to run (default: 2, see CONTRIBUTING.md for why)")
g.add_argument("--color", choices=["on", "auto", "off"], default="auto",
               help="Whether to use colored output. "
                    "'auto' means only use colored output when both stdout and stderr are tty.")
g = p.add_argument_group("Raw arguments")
g.add_argument("args", nargs="*", # NOT argparse.REMAINDER! It's no good
               help="Arguments passed to the underlying generator "
                    "stde.pegen.__main__. Precede with '--'. "
                    "See `python -m stde.pegen -h`")


def backup_file(file_path):
    """Create backup of file if it exists"""
    backup_path = f"{file_path}.bak" #XXX:...
    shutil.copy2(file_path, backup_path)
    print(f"Backed up {file_path} -> {backup_path}")
    return backup_path



def main(args):
    if TYPE_CHECKING:
        def print(*args: Any, **kwargs: Any) -> None: pass
    else:
        print = partial(builtins.print, flush=True)
    use_color = (args.color == "auto" and sys.stdout.isatty() and sys.stderr.isatty()
                 or args.color == "on")
    if use_color and not has_colorama:
        print("Warning: Color is determined to be enabled but colorama is not available. "
              "No color will be printed.")
    if use_color:
        just_fix_windows_console()
        c = colors
    else:
        c = Colors.null()
    if args.version == "legacy":
        metagrammar = LEGACY_METAGRAMMAR
        output = LEGACY_OUTPUT
        bad_path = LEGACY_BAD_OUTPUT
        version_flag = "--legacy"
    elif args.version == "v2":
        metagrammar = V2_METAGRAMMAR
        output = V2_OUTPUT
        bad_path = V2_BAD_OUTPUT
        version_flag = "--v2"
    else:
        assert False, args.version
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
        print(f"{c.WHITE}{c.BOLD}Generation {i}/{args.generations}: {' '.join(cmd)}{c.RST}")
        result = subprocess.run(cmd)
        if result.returncode:
            print(f"{c.RED}{c.BOLD}Error: Generation {i} failed with code {result.returncode}{c.RST}")
            shutil.copy2(output, bad_path)
            print(f"Broken parser stored in {bad_path}")
            if backup_path:
                shutil.copy2(backup_path, output)
                print(f"Restored from backup {output} <- {backup_path}")
            return result.returncode
        #XXX: Use first result as backup if backup_path initially None?

    print(f"{c.GREEN}{c.BOLD}Generation successful!{c.RST}")
    return 0

if __name__ == "__main__":
    sys.exit(main(p.parse_args())) #type:ignore[no-untyped-call] # TODO: Fix later