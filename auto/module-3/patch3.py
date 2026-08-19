import sys
with open('templates/blogs.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Update select
text = text.replace('<option value="created_at">', '<option value="created_at" {% if date_type == \'created_at\' %}selected{% endif %}>')
text = text.replace('<option value="updated_at">', '<option value="updated_at" {% if date_type == \'updated_at\' %}selected{% endif %}>')
text = text.replace('<option value="published_at">', '<option value="published_at" {% if date_type == \'published_at\' %}selected{% endif %}>')

# Update inputs
text = text.replace('id="filterDateFrom" class=', 'id="filterDateFrom" value="{{ date_from or \'\' }}" class=')
text = text.replace('id="filterDateTo" class=', 'id="filterDateTo" value="{{ date_to or \'\' }}" class=')

# Update hidden state
text = text.replace('id="advancedFilters" class="hidden ', 'id="advancedFilters" class="{% if date_from or date_to %}{% else %}hidden{% endif %} ')

# Update toggle button active state
text = text.replace('id="toggleFilterBtn" class="inline-flex', 'id="toggleFilterBtn" class="{% if date_from or date_to %}bg-indigo-50 border-indigo-300 text-indigo-700{% endif %} inline-flex')

with open('templates/blogs.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patched UI persistence")
