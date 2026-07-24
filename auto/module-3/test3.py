
import main
import requests
import pprint

q = """
query {
  collectionByHandle(handle: "best-sellers-manually") {
    products(first: 25) {
      edges {
        node {
          title
        }
      }
    }
  }
}
"""
res = requests.post(main.GRAPHQL_URL, json={"query": q}, headers=main.HEADERS)
pprint.pprint(res.json())

