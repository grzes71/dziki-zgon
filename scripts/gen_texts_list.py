import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python gen_texts_list.py <output_file> [input_files...]")
        sys.exit(1)
        
    output_file = sys.argv[1]
    input_files = sys.argv[2:]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("; Plik wygenerowany automatycznie\n")
        for in_file in input_files:
            # Upewnij się, że używamy slashy forward dla MADS
            normalized_path = in_file.replace('\\', '/')
            f.write(f'    icl "{normalized_path}"\n')

if __name__ == "__main__":
    main()
