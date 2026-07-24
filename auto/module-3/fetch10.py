import main
data = main.get_products(first=10)
for i, edge in enumerate(data['products']['edges']):
    node = edge['node']
    print(f"{i+1}. {node['title']} - {node['createdAt']}")
