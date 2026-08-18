with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

settings_route = '''@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request=request, name="settings.html", context={"request": request})'''

blogs_route = '''@app.get("/blogs", response_class=HTMLResponse)
async def blogs_page(request: Request):
    return templates.TemplateResponse(request=request, name="blogs.html", context={"request": request})

'''

if blogs_route not in content:
    new_content = content.replace(settings_route, blogs_route + settings_route)
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Added blogs route')
else:
    print('Blogs route already exists')
