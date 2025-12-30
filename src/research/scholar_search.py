"""Academic database search clients for literature review."""
import os
import logging
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from src.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class AcademicPaper:
    """Standardized academic paper representation."""
    title: str
    authors: List[str]
    year: Optional[int]
    abstract: Optional[str]
    citation_count: int
    doi: Optional[str]
    url: str
    source: str  # "semantic_scholar" or "openalex"
    venue: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "citation_count": self.citation_count,
            "doi": self.doi,
            "url": self.url,
            "source": self.source,
            "venue": self.venue,
        }


class SemanticScholarSearch:
    """
    Semantic Scholar API client.

    Free tier: 100 requests/5 minutes without API key.
    With API key: Higher limits.
    Docs: https://api.semanticscholar.org/api-docs/
    """
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        self.headers: Dict[str, str] = {}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def search(
        self,
        query: str,
        max_results: int = 5,
        fields: str = "title,authors,year,abstract,citationCount,externalIds,venue,url",
    ) -> List[AcademicPaper]:
        """
        Search Semantic Scholar for papers.

        Args:
            query: Search query (supports boolean operators)
            max_results: Number of results (max 100 per request)
            fields: Comma-separated field list

        Returns:
            List of AcademicPaper objects
        """
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": fields,
        }

        logger.info(f"Semantic Scholar search: {query}")

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            papers = []
            for item in data.get("data", []):
                # Extract DOI from externalIds
                external_ids = item.get("externalIds", {}) or {}
                doi = external_ids.get("DOI")

                # Build paper URL
                paper_url = item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}"

                # Extract author names
                authors = [a.get("name", "") for a in item.get("authors", [])]

                paper = AcademicPaper(
                    title=item.get("title", ""),
                    authors=authors,
                    year=item.get("year"),
                    abstract=item.get("abstract"),
                    citation_count=item.get("citationCount", 0) or 0,
                    doi=doi,
                    url=paper_url,
                    source="semantic_scholar",
                    venue=item.get("venue"),
                )
                papers.append(paper)

            logger.info(f"Semantic Scholar returned {len(papers)} results")
            return papers

        except requests.exceptions.HTTPError as e:
            logger.error(f"Semantic Scholar HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            raise


class OpenAlexSearch:
    """
    OpenAlex API client.

    Completely free, no API key required.
    Rate limit: 100,000 requests/day, 10 requests/second.
    Docs: https://docs.openalex.org/
    """
    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: Optional[str] = None):
        # OpenAlex uses polite pool with email for higher rate limits
        self.email = email or os.getenv("OPENALEX_EMAIL", "")
        if self.email:
            self.headers = {"User-Agent": f"UFE-ResearchAgent/1.0 (mailto:{self.email})"}
        else:
            self.headers = {"User-Agent": "UFE-ResearchAgent/1.0"}

    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def search(self, query: str, max_results: int = 5) -> List[AcademicPaper]:
        """
        Search OpenAlex for works.

        Args:
            query: Search query
            max_results: Number of results

        Returns:
            List of AcademicPaper objects
        """
        url = f"{self.BASE_URL}/works"
        params: Dict[str, str | int] = {
            "search": query,
            "per_page": min(max_results, 50),
            "sort": "cited_by_count:desc",  # Most cited first
        }
        if self.email:
            params["mailto"] = self.email

        logger.info(f"OpenAlex search: {query}")

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            papers = []
            for item in data.get("results", []):
                # Extract author names
                authors = []
                for authorship in item.get("authorships", []):
                    author_info = authorship.get("author", {})
                    if author_info.get("display_name"):
                        authors.append(author_info["display_name"])

                # Get DOI
                doi_url = item.get("doi") or ""
                doi = doi_url.replace("https://doi.org/", "") if doi_url else None

                # Get best available URL
                paper_url = doi_url or item.get("id", "")

                # Get venue/journal
                primary_location = item.get("primary_location", {}) or {}
                source_info = primary_location.get("source", {}) or {}
                venue = source_info.get("display_name")

                paper = AcademicPaper(
                    title=item.get("title", "") or item.get("display_name", ""),
                    authors=authors[:10],  # Limit authors
                    year=item.get("publication_year"),
                    abstract=self._get_abstract(item),
                    citation_count=item.get("cited_by_count", 0) or 0,
                    doi=doi,
                    url=paper_url or item.get("id", ""),
                    source="openalex",
                    venue=venue,
                )
                papers.append(paper)

            logger.info(f"OpenAlex returned {len(papers)} results")
            return papers

        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenAlex HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            raise

    def _get_abstract(self, item: Dict) -> Optional[str]:
        """Extract abstract from OpenAlex inverted index format."""
        abstract_inverted = item.get("abstract_inverted_index")
        if not abstract_inverted:
            return None

        try:
            # Reconstruct abstract from inverted index
            word_positions: List[tuple] = []
            for word, positions in abstract_inverted.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort(key=lambda x: x[0])
            return " ".join(word for _, word in word_positions)
        except Exception:
            return None


class AcademicSearch:
    """
    Unified academic search interface.
    Combines results from multiple sources.
    """

    def __init__(
        self,
        semantic_scholar_key: Optional[str] = None,
        openalex_email: Optional[str] = None,
    ):
        self.semantic_scholar = SemanticScholarSearch(api_key=semantic_scholar_key)
        self.openalex = OpenAlexSearch(email=openalex_email)

    def search(
        self,
        query: str,
        max_per_source: int = 5,
        sources: Optional[List[str]] = None,
    ) -> List[AcademicPaper]:
        """
        Search multiple academic databases.

        Args:
            query: Search query
            max_per_source: Results per source
            sources: List of sources to use ["semantic_scholar", "openalex"]

        Returns:
            Combined list of AcademicPaper objects, deduplicated by DOI
        """
        sources = sources or ["openalex", "semantic_scholar"]  # OpenAlex first (more reliable)
        all_papers: List[AcademicPaper] = []

        # Search OpenAlex first (free, no API key needed, higher rate limits)
        if "openalex" in sources:
            try:
                papers = self.openalex.search(query, max_results=max_per_source)
                all_papers.extend(papers)
            except Exception as e:
                logger.warning(f"OpenAlex search failed, continuing: {e}")

        # Then try Semantic Scholar (may be rate-limited without API key)
        if "semantic_scholar" in sources:
            try:
                papers = self.semantic_scholar.search(query, max_results=max_per_source)
                all_papers.extend(papers)
            except Exception as e:
                logger.warning(f"Semantic Scholar search failed, continuing: {e}")

        # Deduplicate by DOI
        seen_dois: set = set()
        unique_papers: List[AcademicPaper] = []
        for paper in all_papers:
            if paper.doi:
                if paper.doi not in seen_dois:
                    seen_dois.add(paper.doi)
                    unique_papers.append(paper)
            else:
                # Keep papers without DOI (can't deduplicate)
                unique_papers.append(paper)

        return unique_papers
