#!/usr/bin/env python3
import os
import sys

def split_code():
    # Change 'main_program.py' to whatever your file is actually called
    main_file = 'main_program.py'
    
    if not os.path.exists(main_file):
        print(f"Error: {main_file} not found!")
        return False
    
    with open(main_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    print(f"Total lines: {total_lines}")
    
    # Split exactly as you request
    part1_lines = lines[:2400]
    part2_lines = lines[2400:4800]
    part3_lines = lines[4800:7200]
    
    with open('part1.py', 'w', encoding='utf-8') as f:
        f.writelines(part1_lines)
    print(f"Created part1.py with {len(part1_lines)} lines")
    
    if part2_lines:
        with open('part2.py', 'w', encoding='utf-8') as f:
            f.writelines(part2_lines)
        print(f"Created part2.py with {len(part2_lines)} lines")
    
    if part3_lines:
        with open('part3.py', 'w', encoding='utf-8') as f:
            f.writelines(part3_lines)
        print(f"Created part3.py with {len(part3_lines)} lines")
    
    return True

if __name__ == "__main__":
    split_code()