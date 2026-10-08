from langchain.tools import tool
from second.Agentic_tools.search_web import search_web

@tool
def web_search(query: str, limit: int = 3) -> str:
    """Search the web and return the top search results.

    Args:
        query: The search query.
        limit: Maximum number of search results to return.
    """
    return search_web(query, limit)
