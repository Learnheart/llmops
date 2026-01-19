import os
import re

def parse_content(content):
    # Tìm các blocks của file
    file_blocks = re.split(r'={50,}', content)
    
    # Dictionary để lưu thông tin file
    files = {}
    
    for block in file_blocks:
        if not block.strip():
            continue
            
        # Tìm tên file
        file_match = re.search(r'### File: (.+?)\n```(.*?)```', block, re.DOTALL)
        if file_match:
            filename = file_match.group(1).strip()
            content = file_match.group(2).strip()
            files[filename] = content
    
    return files

def create_files(files):
    # Tạo files và thư mục
    for filepath, content in files.items():
        # Tạo thư mục nếu cần
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # Ghi nội dung vào file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Created: {filepath}')

def main():
    # Đọc file input
    with open('contents.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse nội dung
    files = parse_content(content)
    
    # Tạo files
    create_files(files)
    
    print(f'\nCreated {len(files)} files successfully!')

if __name__ == '__main__':
    main()