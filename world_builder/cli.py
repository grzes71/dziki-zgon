import argparse
import sys
from .compiler import compile_world

def main():
    parser = argparse.ArgumentParser(description="World Builder Compiler")
    parser.add_argument("input_dir", help="Path to the input world directory")
    parser.add_argument("output_dir", help="Path to the output ASM directory")
    
    args = parser.parse_args()
    
    success = compile_world(args.input_dir, args.output_dir)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
