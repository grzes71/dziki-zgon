import os
import re
import argparse

def clean_markdown_content(content, filename):
    # 1. Truncate Wikipedia edit pages / temporary account warnings at the end of the file
    # These sections always start with a header like "## Editing [Page] - Wikipedia" or "## Editing [Page] (section) - Wikipedia"
    edit_header_pattern = re.compile(r'^##\s+Editing\s+.*?\s+-\s+Wikipedia', re.IGNORECASE | re.MULTILINE)
    match = edit_header_pattern.search(content)
    if match:
        content = content[:match.start()]
    
    # 2. Remove Wikipedia/Atariki edit links
    # Examples:
    # [ [edit](url) ]
    # [Edytuj](url)]
    # [edit](url)
    edit_link_pattern = re.compile(
        r'\[?\s*\[(?:edit|Edytuj)\]\([^)]*action=edit[^)]*\)\s*\]?',
        re.IGNORECASE | re.MULTILINE
    )
    content = edit_link_pattern.sub('', content)

    # 3. Remove citation links (e.g. [[3]](https://en.wikipedia.org#cite_note-3) or [1](#cite_note-1))
    citation_link_pattern = re.compile(
        r'\[?\[\d+\]\]?\((?:https?://[a-zA-Z0-9./_-]+)?#cite_note[^)]*\)',
        re.IGNORECASE
    )
    content = citation_link_pattern.sub('', content)

    # 4. Remove atariarchives.org footer/boilerplate disclaimer (specifically found in dere.md)
    atariarchives_disclaimer_pattern = re.compile(
        r'\*This site maintained by Kay Savetz\..*?Do not redistribute, mirror, or copy this online book\.\*',
        re.DOTALL | re.IGNORECASE
    )
    content = atariarchives_disclaimer_pattern.sub('', content)

    # Remove the second part of the atariarchives boilerplate
    atariarchives_about_pattern = re.compile(
        r'##\s*AtariArchives\.org\s*-\s*archiving vintage computer books.*?This site is maintained by Kay Savetz\.\*',
        re.DOTALL | re.IGNORECASE
    )
    content = atariarchives_about_pattern.sub('', content)

    # 5. Clean up site navigation links at the end of files (e.g., in memory-map.md, dere.md)
    # Remove strings like:
    # Return to Table of Contents
    # |
    # Previous Chapter
    # |
    # Next Chapter
    nav_pattern_1 = re.compile(
        r'Return to Table of Contents\s*\|\s*Previous Chapter\s*\|\s*Next Chapter',
        re.IGNORECASE | re.MULTILINE
    )
    content = nav_pattern_1.sub('', content)
    
    nav_pattern_2 = re.compile(
        r'Return to Table of Contents\s*\n\s*\|\s*\n\s*Previous Chapter\s*\n\s*\|\s*\n\s*Next Chapter',
        re.IGNORECASE | re.MULTILINE
    )
    content = nav_pattern_2.sub('', content)

    # 6. Remove "*Generated from: <url>*" footer lines
    generated_from_pattern = re.compile(
        r'^\*Generated from:\s*<https?://[^>]+>\*$',
        re.IGNORECASE | re.MULTILINE
    )
    content = generated_from_pattern.sub('', content)

    # 7. Clean up multiple consecutive empty lines (3 or more newlines -> 2 newlines)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # 8. Strip trailing spaces from each line
    lines = [line.rstrip() for line in content.splitlines()]
    content = '\n'.join(lines) + '\n'
    
    return content

def main():
    parser = argparse.ArgumentParser(description="Oczyszcza dokumenty Markdown z pozostałości po konwersji z HTML.")
    parser.add_argument(
        "directory",
        nargs="?",
        default="docs",
        help="Katalog zawierający pliki dokumentacji do oczyszczenia (domyślnie: 'docs')"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["KONSPEKT.md"],
        help="Lista plików do pominięcia (domyślnie: ['KONSPEKT.md'])"
    )
    parser.add_argument(
        "--ext",
        nargs="*",
        default=[".md"],
        help="Rozszerzenia plików do oczyszczenia (domyślnie: ['.md'])"
    )
    
    args = parser.parse_args()
    
    docs_dir = os.path.abspath(args.directory)
    if not os.path.isdir(docs_dir):
        print(f"Błąd: Katalog '{docs_dir}' nie istnieje.")
        return
        
    exclusions = set(args.exclude)
    extensions = tuple(ext.lower() for ext in args.ext)
    
    print(f"Rozpoczynanie czyszczenia w katalogu: {docs_dir}")
    print(f"Wykluczone pliki: {', '.join(exclusions) if exclusions else 'brak'}")
    print(f"Obsługiwane rozszerzenia: {', '.join(extensions)}")
    print("-" * 50)
    
    files_processed = 0
    for filename in os.listdir(docs_dir):
        filepath = os.path.join(docs_dir, filename)
        
        # Sprawdzenie czy to plik, czy ma odpowiednie rozszerzenie i czy nie jest wykluczony
        if os.path.isfile(filepath) and filename.lower().endswith(extensions) and filename not in exclusions:
            print(f"Przetwarzanie: {filename}...")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                cleaned_content = clean_markdown_content(original_content, filename)
                
                # Zapis z powrotem
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                    
                orig_len = len(original_content)
                clean_len = len(cleaned_content)
                reduction = orig_len - clean_len
                percent = (reduction / orig_len * 100) if orig_len > 0 else 0
                print(f"Zakończono {filename}: rozmiar zmniejszony z {orig_len} do {clean_len} znaków (redukcja: {reduction} znaków / {percent:.1f}%)")
                files_processed += 1
            except Exception as e:
                print(f"Błąd podczas przetwarzania {filename}: {e}")
            
    print("-" * 50)
    print(f"Łącznie oczyszczono plików: {files_processed}")

if __name__ == "__main__":
    main()

