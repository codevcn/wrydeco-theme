import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add priceRangeV2 and productType to all GraphQL queries
code = re.sub(
    r'(\s+descriptionHtml\n\s+createdAt\n)(\s+options {)',
    r'\1            productType\n            priceRangeV2 {\n              minVariantPrice {\n                amount\n              }\n            }\n\2',
    code
)

# 2. Update get_products_by_* signatures and sort logic
code = re.sub(
    r'def (get_products_by_[a-z_]+)\(keyword, reverse=True\):',
    r'def \1(keyword, sort_by="created_desc"):',
    code
)

sort_logic = '''    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
'''
code = re.sub(
    r'    all_matched_edges\.sort\(key=lambda edge: edge\["node"\]\.get\("createdAt", ""\), reverse=reverse\)\n',
    sort_logic,
    code
)

# 3. Update read_root logic
old_read_root = '''        reverse = True if sort_by == "created_desc" else False
        
        if filter_value and filter_type == "metafield_amazon_link":
            data = get_products_by_metafield_amazon_link(filter_value, reverse=reverse)
        elif filter_value and filter_type == "metafield_rich_description":
            data = get_products_by_metafield_rich_description(filter_value, reverse=reverse)
        elif filter_value and filter_type == "description":
            data = get_products_by_description(filter_value, reverse=reverse)
        else:
            if filter_value:
                if filter_type == "tag":
                    filter_query = f"tag:{filter_value}"
                elif filter_type == "title":
                    filter_query = f"title:*{filter_value}*"
                elif filter_type == "id":
                    filter_query = f"id:{filter_value}"
                elif filter_type == "handle":
                    filter_query = f"handle:{filter_value}"
                    
            data = get_products(first=30, after=after, before=before, filter_query=filter_query, sort_key="CREATED_AT", reverse=reverse)'''

new_read_root = '''        reverse = True
        sort_key_graphql = "CREATED_AT"
        if sort_by == "price_asc":
            sort_key_graphql = "PRICE"
            reverse = False
        elif sort_by == "price_desc":
            sort_key_graphql = "PRICE"
            reverse = True
        elif sort_by == "created_asc":
            sort_key_graphql = "CREATED_AT"
            reverse = False
            
        if filter_value and filter_type == "metafield_amazon_link":
            data = get_products_by_metafield_amazon_link(filter_value, sort_by=sort_by)
        elif filter_value and filter_type == "metafield_rich_description":
            data = get_products_by_metafield_rich_description(filter_value, sort_by=sort_by)
        elif filter_value and filter_type == "description":
            data = get_products_by_description(filter_value, sort_by=sort_by)
        else:
            if filter_value:
                if filter_type == "tag":
                    filter_query = f"tag:{filter_value}"
                elif filter_type == "title":
                    filter_query = f"title:*{filter_value}*"
                elif filter_type == "id":
                    filter_query = f"id:{filter_value}"
                elif filter_type == "handle":
                    filter_query = f"handle:{filter_value}"
                elif filter_type == "product_type":
                    filter_query = f"product_type:'{filter_value}'"
                    
            data = get_products(first=30, after=after, before=before, filter_query=filter_query, sort_key=sort_key_graphql, reverse=reverse)'''

code = code.replace(old_read_root, new_read_root)

# 4. Extract price and productType for template
old_append = '''            products.append({
                "id": node["id"].split("/")[-1],
                "handle": node["handle"],
                "title": node["title"],
                "description": node.get("descriptionHtml", ""),
                "createdAt": node.get("createdAt", ""),
                "options": options,
                "collections": collections,
                "media": media_urls
            })'''

new_append = '''            price = 0
            price_data = node.get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                price = float(price_data["minVariantPrice"].get("amount", 0))
                
            products.append({
                "id": node["id"].split("/")[-1],
                "handle": node["handle"],
                "title": node["title"],
                "productType": node.get("productType", ""),
                "price": price,
                "description": node.get("descriptionHtml", ""),
                "createdAt": node.get("createdAt", ""),
                "options": options,
                "collections": collections,
                "media": media_urls
            })'''

code = code.replace(old_append, new_append)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Updated main.py')
