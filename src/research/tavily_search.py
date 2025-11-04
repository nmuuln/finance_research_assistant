import os, requests

class WebSearch:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")

    def search(self, query: str, max_results: int = 6):
        """
        Returns [{'title','url','snippet'}] using Tavily's public API.
        """
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
        }
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": (r.get("content") or "")[:400],
            }
            for r in results
        ]
