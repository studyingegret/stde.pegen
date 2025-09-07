from io import StringIO
import os, re, argparse, sys, rtoml
from subprocess import Popen, run, CompletedProcess
from enum import IntFlag
from pathlib import Path
from typing import TextIO
import colorama

class Action(IntFlag):
    FIRST = 1
    SECOND = 2
    THIRD = 4

TEMP_FILE = "_run_mypy_temp.toml"
NEW_EXCLUDE = r'build/.*|tests/(v2/)?python_parser/(data|parser_cache)/.*|tests/legacy/demo\.py|src/stde/pegen/v2/parser_old\.py'

description = f"""\
See section "Type checking" in CONTRIBUTING.md for details.

Leaves temp file {TEMP_FILE}.

If type check results seem inconsistent with the code, try `dmypy restart` or `dmypy kill`
"""

p = argparse.ArgumentParser(description=description)
p.set_defaults(action=Action.FIRST | Action.SECOND)
p.add_argument("--first-only", action="store_const", dest="action", const=Action.FIRST,
               help="Run first run only (excluding grammar_parser_v2.py).")
p.add_argument("--second-only", action="store_const", dest="action", const=Action.SECOND,
               help="Run second run only (just grammar_parser_v2.py, filtering likely false-positives).")
p.add_argument("--third-only", action="store_const", dest="action", const=Action.THIRD,
               help="Run third run only (just grammar_parser_v2.py, not filtering likely false-positives).")
p.add_argument("args", nargs=argparse.REMAINDER,
               help='Arguments to pass to dmypy (precede with "--")')

RED = colorama.Fore.LIGHTRED_EX
GREEN = colorama.Fore.LIGHTGREEN_EX
#WHITE = colorama.Fore.LIGHTWHITE_EX
MAGENTA = colorama.Fore.MAGENTA
BOLD = colorama.Style.BRIGHT
NORMAL = colorama.Style.NORMAL
RESET = colorama.Fore.RESET

# Exact code will change if type check flagging strategy for grammar_parser_v2.py changes
def compile_toml():
    #data = rtoml.load("pyproject.toml")["tool"]["mypy"]
    data = rtoml.load(Path(__file__).parent / "pyproject.toml")["tool"]["mypy"]
    # [[tool.mypy.overrides]]
    # module = ["stde.pegen.v2.grammar_parser"]
    for i, item in enumerate(data["overrides"]):
        if item["module"] == ["stde.pegen.v2.grammar_parser"]:
            break
    else:
        assert False, "No section for stde.pegen.v2.grammar_parser matched"
    del data["overrides"][i]["follow_imports"]
    data["exclude"] = NEW_EXCLUDE
    rtoml.dump({"tool": {"mypy": data}}, Path(TEMP_FILE))

def print_header(line):
    print(f"{BOLD}{MAGENTA}{line}{RESET}{NORMAL}")

def main(args):
    if args.action != 0:
        colorama.just_fix_windows_console()
        #RED = colorama.Fore.RED
        if args.action & Action.FIRST:
            # Note: Use mypy daemon for Action.FIRST only
            print_header(f"== First run: excluding grammar_parser_v2.py")
            run(["dmypy", "start"], stdout=sys.stdout, stderr=sys.stderr)
            # Crash is likely for first run. Not very likely for other runs. (??)
            if run_a(args):
                print_header(f"== Retry: First run: excluding grammar_parser_v2.py")
                if run_a(args):
                    sys.exit(f"{RED}{BOLD}Daemon crashed twice{RESET}{NORMAL}")
        if args.action & (Action.SECOND | Action.THIRD):
            pass
            # Needed for unknown reasons, might be dmypy bug
            # ??
            #run(["dmypy", "restart"], stdout=sys.stdout, stderr=sys.stderr)
            #run(["dmypy", "kill"], stdout=sys.stdout, stderr=sys.stderr)
            #run(["dmypy", "start"] + args.args, stdout=sys.stdout, stderr=sys.stderr)
        if args.action & Action.SECOND:
            print_header(f"== Second run: just grammar_parser_v2.py, filtering likely false-positives")
            compile_toml()
            r, w = os.pipe()
            with os.fdopen(r, "r") as rf:
                with os.fdopen(w, "w") as wf:
                    Popen(["mypy", "-m", "stde.pegen.v2.grammar_parser", f"--config-file={TEMP_FILE}"] + args.args,
                          stdout=wf, stderr=sys.stderr, env={"MYPY_FORCE_COLOR": "1"})
                nerrors = 0
                nfilterederrors = 0
                nfilteredwarnings = 0
                nfilterednotes = 0
                nfilteredothers = 0
                no_success = True
                for line in rf:
                    if "FAILURE" not in line and "NO_MATCH" not in line and not re.search(r"Found \d+ error", line):
                        sys.stdout.write(line)
                        if "error:" in line:
                            nerrors += 1
                    else:
                        if "error:" in line:
                            nfilterederrors += 1
                        elif "warning:" in line:
                            nfilteredwarnings += 1
                        elif "note:" in line:
                            nfilterednotes += 1
                        elif not re.search(r"Found \d+ error", line): # Abandon this line anyway
                            nfilteredothers += 1
                        if "Success:" in line:
                            no_success = False
                print(f"{BOLD}Filtered {nfilterederrors} {"error" if nfilterederrors == 1 else "errors"}, "
                      f"{nfilteredwarnings} {"warning" if nfilteredwarnings == 1 else "warnings"}, "
                      f"{nfilterednotes} {"note" if nfilterednotes == 1 else "notes"}, "
                      f"{nfilteredothers} other lines{NORMAL}")
                if nerrors:
                    print(f"{RED}{BOLD}Unfiltered {nerrors} "
                          f"{"error" if nerrors == 1 else "errors"}{RESET}{NORMAL}")
                else:
                    if no_success:
                        print(f"{GREEN}{BOLD}Success{RESET}{NORMAL}")
            #CompletedProcess(proc.args, proc.returncode, None, None).check_returncode()
        if args.action & Action.THIRD:
            print_header(f"== Third run: just grammar_parser_v2.py, not filtering likely false-positives")
            run(["mypy", "-m", "stde.pegen.v2.grammar_parser"] + args.args,
                stdout=sys.stdout, stderr=sys.stderr)
        if args.action & Action.SECOND:
            print_header("Use --third-only to run mypy on grammar_parser_v2.py without filtering")
            print_header("(but be prepared to manually handle false-positives)")

def run_a(args):
    r, w = os.pipe()
    crashed = False
    with os.fdopen(r, "r") as rf:
        with os.fdopen(w, "w") as wf:
            proc = Popen(["dmypy", "run", "--"] + args.args,
                         stdout=sys.stdout, stderr=wf, env={"MYPY_FORCE_COLOR": "1"})
        for line in rf:
            if "Daemon crashed" in line:
                crashed = True
            sys.stderr.write(line)
    if crashed:
        print(f"{RED}{BOLD}Daemon crashed{RESET}{NORMAL}")
    return crashed

if __name__ == "__main__":
    sys.exit(main(p.parse_args()))