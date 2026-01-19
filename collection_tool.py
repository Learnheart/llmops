"""
Code Collection Tool - Generate documentation with code content collection
"""
import os
import argparse
import fnmatch
from datetime import datetime
from typing import List, Dict
from pathlib import Path

class CodeCollector:
    """Collect and document code files"""
    
    def parse_gitignore(self, path: str) -> List[str]:
        """Parse .gitignore patterns"""
        patterns = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        return patterns

    def should_exclude(self, path: str, folder_patterns: List[str], 
                      file_patterns: List[str], gitignore_patterns: List[str]) -> bool:
        """Check if path should be excluded using proper gitignore pattern matching"""
        path_obj = Path(path)
        path_str = str(path_obj)
        name = path_obj.name

        # Check for dots in directory names
        if path_obj.is_dir() and '.' in name:
            return True

        # Check folder patterns
        for pattern in folder_patterns:
            if Path(pattern) in path_obj.parents or pattern == name:
                return True

        # Check file patterns
        for pattern in file_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True

        # Check gitignore patterns
        for pattern in gitignore_patterns:
            if pattern.startswith('/'):
                if fnmatch.fnmatch(path_str, pattern[1:] + '*'):
                    return True
            elif pattern.endswith('/'):
                if any(p.name == pattern[:-1] for p in path_obj.parents):
                    return True
            else:
                if fnmatch.fnmatch(name, pattern) or any(fnmatch.fnmatch(p.name, pattern) for p in path_obj.parents):
                    return True

        return False

    def collect_files(self, directories: List[str], folder_exclude: List[str],
                     file_exclude: List[str], gitignore_patterns: List[str],
                     allowed_extensions: List[str]) -> Dict[str, List[Path]]:
        """Collect files from directories applying exclusion patterns and extension filters"""
        files = {}
        for directory in directories:
            files[directory] = []
            base_dir = os.getcwd() if directory == '.' else directory

            for root, _, filenames in os.walk(base_dir):
                if '.' in os.path.basename(root):
                    continue

                if self.should_exclude(root, folder_exclude, [], gitignore_patterns):
                    continue

                for f in filenames:
                    file_path = Path(root) / f
                    if not any(str(file_path).endswith(ext) for ext in allowed_extensions):
                        continue

                    if not self.should_exclude(str(file_path), folder_exclude, 
                                            file_exclude, gitignore_patterns):
                        try:
                            rel_path = file_path.relative_to(base_dir)
                            files[directory].append(rel_path)
                        except ValueError:
                            files[directory].append(file_path)
        return files

    def save_contents(self, files: Dict[str, List[Path]], output: str):
        """Save all file contents to single file"""
        with open(output, 'w', encoding='utf-8') as out:
            out.write(f"# File Contents Collection\nGenerated: {datetime.now()}\n\n")
            
            for directory, paths in files.items():
                out.write(f"\n## Directory: {directory}\n")
                base_dir = os.getcwd() if directory == '.' else directory
                for path in sorted(paths):
                    try:
                        # Construct full path by joining base directory with relative path
                        full_path = os.path.join(base_dir, str(path))
                        with open(full_path, 'r', encoding='utf-8') as f:
                            out.write(f"\n### File: {path}\n```\n")
                            out.write(f.read())
                            out.write("\n```\n")
                            out.write("="*50 + "\n")
                    except Exception as e:
                        out.write(f"Error reading {path}: {e}\n")

    def generate_structure(self, files: Dict[str, List[Path]]) -> str:
        """Generate project structure documentation"""
        structure = f"# Project Structure Documentation\nGenerated: {datetime.now()}\n\n"
        
        for directory, paths in files.items():
            structure += f"\n## {directory}\n"
            for path in sorted(paths):
                structure += f"- {path}\n"
                
        return structure

def main():
    parser = argparse.ArgumentParser(description="Code collection and documentation tool")
    parser.add_argument("-d", "--directories", nargs='+', default=['.'],
                      help="Directories to process")
    parser.add_argument("-o", "--output", default="contents.md",
                      help="Output file for contents")
    parser.add_argument("-s", "--structure", default="structure.md",
                      help="Output file for project structure")
    parser.add_argument("-efo", "--exclude-folder", nargs='+',
                      default=['node_modules', 'venv', '.git', '__pycache__', 'output', '.github', '.husky'],
                      help="Folders to exclude")
    parser.add_argument("-efi", "--exclude-file", nargs='+',
                      default=['.gitignore', 'package-lock.json', '*.pyc', '*.md', 'paste.md', '.gitattributes'],
                      help="Files to exclude")
    parser.add_argument("-ext", "--allowed-extensions", nargs='+',
                      default=['.py', '.js', '.ts', '.json', '.md', '.txt', '.yaml', '.yml', '.hcl', '.R', '.sql'],
                      help="Allowed file extensions")
    args = parser.parse_args()

    collector = CodeCollector()
    
    # Get gitignore patterns
    gitignore_path = os.path.join(os.getcwd(), '.gitignore')
    gitignore_patterns = collector.parse_gitignore(gitignore_path)
    
    # Collect files
    files = collector.collect_files(
        args.directories,
        args.exclude_folder,
        args.exclude_file,
        gitignore_patterns,
        args.allowed_extensions
    )
    
    # Save contents
    collector.save_contents(files, args.output)
    print(f"\nContents saved to {args.output}")
    
    # Generate and save structure
    structure = collector.generate_structure(files)
    with open(args.structure, 'w', encoding='utf-8') as f:
        f.write(structure)
    print(f"Structure documentation saved to {args.structure}")
    
    # Print summary
    print("\nSummary:")
    print(f"- Processed directories: {', '.join(args.directories)}")
    print(f"- Excluded folders: {', '.join(args.exclude_folder)}")
    print(f"- Excluded files: {', '.join(args.exclude_file)}")
    print(f"- Allowed extensions: {', '.join(args.allowed_extensions)}")
    print(f"- Gitignore patterns: {', '.join(gitignore_patterns)}")
    total_files = sum(len(paths) for paths in files.values())
    print(f"- Total files processed: {total_files}")

if __name__ == "__main__":
    main()
    
# python collection_tool.py -d "D:\experiments\repository\ragflow-main\deepdoc" -o "rag_deep_doc_content.md" -s "rag_deepdoc_structure.md"
# python collection_tool.py -d "D:\experiments\repository\ragflow_practice" -o "ragflow_content.md" -s "ragflow_structure.md"
# python collection_tool.py -d "services/guardrails-service" -o "guardrails_content.md" -s "guardrails_structure.md"