import json
import re

transcript_path = r'C:\Users\dell\.gemini\antigravity-cli\brain\46081ac9-8c2e-4dab-afb1-916219012a31\.system_generated\logs\transcript_full.jsonl'
file_content = ''

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('type') == 'TOOL_RESPONSE':
                for tool in data.get('tool_calls', []):
                    if tool.get('name') == 'default_api:view_file':
                        output = tool.get('tool_response', {}).get('output', '')
                        if 'contact-info.html' in output:
                            lines = output.split('\n')
                            in_content = False
                            for l in lines:
                                if l.startswith('The following code has been modified'):
                                    in_content = True
                                    continue
                                if l.startswith('The above content was truncated') or l.startswith('The above content shows the entire'):
                                    in_content = False
                                    continue
                                if in_content:
                                    match = re.match(r'^\d+:\s(.*)$', l)
                                    if match:
                                        file_content += match.group(1) + '\n'
                                    elif l == '^\d+:$':
                                        file_content += '\n'
        except Exception as e:
            pass

with open('tmp/policy/contact-info.html', 'w', encoding='utf-8') as out:
    out.write(file_content)

print(f'Recovered {len(file_content)} bytes.')
