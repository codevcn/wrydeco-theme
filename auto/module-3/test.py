
import main
import requests
import pprint

q = """
query {
  products(first: 5, query: "tag:best-sellers-manually") {
    edges {
      node {
        title
        tags
      }
    }
  }
}
"""
res = requests.post(main.GRAPHQL_URL, json={"query": q}, headers=main.HEADERS)
pprint.pprint(res.json())

