import test_gql
q = """
query {
  products(first: 1) {
    edges {
      node {
        productType
        productCategory {
          productTaxonomyNode {
            fullName
            name
          }
        }
        category {
          name
        }
      }
    }
  }
}
"""
res = test_gql.requests.post(test_gql.GRAPHQL_URL, json={'query': q}, headers=test_gql.HEADERS)
print(res.json())
