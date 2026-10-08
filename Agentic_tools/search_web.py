import serpapi
import os

api_key = os.environ["SERP_API"]

def search_web(query: str, limit: int) -> str:
    client = serpapi.Client(api_key=api_key)

    try:
        results = client.search({
            "engine": "google",
            "q": query,
            "hl": "en",
        })
    except serpapi.HTTPError as e:
        return f"Search API error ({e.status_code}): {e.error}"
    except serpapi.TimeoutError as e:
        return f"Search timed out: {e}"

    if "error" in results:
        return f"Search API returned an error: {results['error']}"

    organic_results = results.get("organic_results", [])[:len(limit)]
    if not organic_results:
        return "No results found."

    return "\n".join(
        f"{r.get('title')}: {r.get('link')}" for r in organic_results
    )