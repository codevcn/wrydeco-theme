import re
with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

api_code = '''
@app.get("/api/product-authors")
def get_product_authors():
    query = """
    query {
      metaobjects(type: "product_author", first: 100) {
        edges {
          node {
            id
            handle
            fields {
              key
              value
            }
          }
        }
      }
    }
    """
    try:
        res = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        authors = []
        if "data" in data and "metaobjects" in data["data"]:
            for edge in data["data"]["metaobjects"]["edges"]:
                node = edge["node"]
                author = {"id": node["id"], "handle": node["handle"]}
                for field in node["fields"]:
                    if field["key"] == "title" or field["key"] == "name":
                        author["name"] = field["value"]
                authors.append(author)
        return JSONResponse(content=authors)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
'''

# Find @app.post("/internal-edit-product")
idx = text.find('@app.post("/internal-edit-product")')
if idx != -1:
    text = text[:idx] + api_code + '\n' + text[idx:]
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Injected /api/product-authors")
else:
    print("Could not find /internal-edit-product")
