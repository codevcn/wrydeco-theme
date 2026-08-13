import sys
import requests

with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
# keep up to line 2797
new_lines = lines[:2797]
append_text = """        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})

@app.post("/internal-edit-product")
async def internal_edit_product(request: Request):
    try:
        import json
        form = await request.form()
        product_id = form.get("product_id")
        target_field = form.get("target_field")
        new_value = form.get("new_value")

        if not product_id or not target_field or not new_value:
            return HTMLResponse(content=json.dumps({"success": False, "message": "Thiếu dữ liệu"}), media_type="application/json")

        if target_field == "productTitle":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  title
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "title": new_value
                }
            }
        elif target_field == "productType":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  productType
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "productType": new_value
                }
            }
        else:
            return HTMLResponse(content=json.dumps({"success": False, "message": f"Trường '{target_field}' chưa được hỗ trợ cập nhật"}), media_type="application/json")

        res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        if "errors" in data:
            return HTMLResponse(content=json.dumps({"success": False, "message": f"GraphQL Error: {data['errors'][0]['message']}"}), media_type="application/json")
        
        user_errs = data.get("data", {}).get("productUpdate", {}).get("userErrors", [])
        if user_errs:
            return HTMLResponse(content=json.dumps({"success": False, "message": f"Lỗi từ Shopify: {user_errs[0]['message']}"}), media_type="application/json")
            
        return HTMLResponse(content=json.dumps({"success": True, "message": "Thành công"}), media_type="application/json")
            
    except Exception as e:
        import json
        return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}), media_type="application/json")
"""
with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    f.write(append_text)
print('Fixed main.py')
