
import main
import requests
import pprint

q = """
query {
  collectionByHandle(handle: "best-sellers-manually") {
    title
    productsCount {
      count
    }
    products(first: 5) {
      edges {
        node {
          title
          tags
        }
      }
    }
  }
}
"""
res = requests.post(main.GRAPHQL_URL, json={"query": q}, headers=main.HEADERS)
pprint.pprint(res.json())

