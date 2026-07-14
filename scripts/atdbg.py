#!/usr/bin/env python3
"""
Compatibility shim forwarding to debug_bridge CLI break command.
"""
import sys
import subprocess

def main():
    # Translate legacy args: --rom -> --xex, --lab-file -> --lab
    new_args = []
    
    i = 0
    args_list = sys.argv[1:]
    while i < len(args_list):
        arg = args_list[i]
        if arg == "--rom":
            new_args.append("--xex")
        elif arg == "--lab-file":
            new_args.append("--lab")
        else:
            new_args.append(arg)
        i += 1

    cmd = [sys.executable, "-m", "debug_bridge.cli", "break"] + new_args
    
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
