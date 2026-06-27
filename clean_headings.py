import os
import re

sections_dir = r"d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-theme\sections"

# Regex to find heading class blocks: .class-name__heading { ... }
# We want to remove font-size, font-family, letter-spacing
# It can also be inside a media query, so we look for lines inside any block that has __heading.

def clean_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all blocks that define a __heading class
    # We will just do a line-by-line state machine
    lines = content.split('\n')
    new_lines = []
    in_heading_block = False
    
    for line in lines:
        if '__heading' in line and '{' in line:
            in_heading_block = True
        
        if in_heading_block:
            if 'font-size:' in line or 'font-family:' in line or 'letter-spacing:' in line:
                # skip this line
                continue
            if '}' in line:
                in_heading_block = False
        
        new_lines.append(line)

    new_content = '\n'.join(new_lines)
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Cleaned {os.path.basename(filepath)}")

for filename in os.listdir(sections_dir):
    if filename.endswith(".liquid"):
        clean_file(os.path.join(sections_dir, filename))

print("Cleanup complete.")
