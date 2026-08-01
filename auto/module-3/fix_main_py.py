import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

fixed_content = re.sub(
    r'templates\.TemplateResponse\(\s*("[^"]+"|' + r"'[^']+'),\s*(\{)",
    r'templates.TemplateResponse(request=request, name=\1, context=\2',
    content
)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(fixed_content)
    
print("Fixed main.py!")
