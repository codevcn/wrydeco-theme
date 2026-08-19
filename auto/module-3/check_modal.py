with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
with open('temp_copymodal.txt', 'w', encoding='utf-8') as out:
    start_idx = -1
    for i, line in enumerate(lines):
        if 'id="copyModal"' in line:
            start_idx = i
            break
    if start_idx != -1:
        for i in range(start_idx, start_idx+70):
            out.write(str(i+1) + ': ' + lines[i])
