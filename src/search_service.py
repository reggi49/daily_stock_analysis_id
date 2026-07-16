# -*- coding: utf-8 -*-
"""
===================================
Stock Analysis System - Search Service Module
===================================

Responsibilities:
1. Provide a unified news search interface
2. Support Bocha, Tavily, Brave, SerpAPI, SearXNG search engines
3. Multi-key search result caching and formatting
4. Search results caching and formatting
"""

import logging
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Optional, Tuple
from itertools import cycle
from urllib.parse import parse_qsl, unquote, urlparse
import requests
from newspaper import Article, Config
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from data_provider.us_index_mapping import is_us_index_code
from src.config import (
    NEWS_STRATEGY_WINDOWS,
    normalize_news_strategy_profile,
    resolve_news_window_days,
)
from src.services.run_diagnostics import record_provider_run, record_provider_run_started

logger = logging.getLogger(__name__)

# Transient network errors (retryable)
_SEARCH_TRANSIENT_EXCEPTIONS = (
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(_SEARCH_TRANSIENT_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _post_with_retry(url: str, *, headers: Dict[str, str], json: Dict[str, Any], timeout: int) -> requests.Response:
    """POST with retry on transient SSL/network errors."""
    return requests.post(url, headers=headers, json=json, timeout=timeout)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(_SEARCH_TRANSIENT_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_with_retry(
    url: str, *, headers: Dict[str, str], params: Dict[str, Any], timeout: int
) -> requests.Response:
    """GET with retry on transient SSL/network errors."""
    return requests.get(url, headers=headers, params=params, timeout=timeout)


def fetch_url_content(url: str, timeout: int = 5) -> str:
    """
    get URL Web page text content (use newspaper3k)
    """
    try:
        # Second-rate newspaper3k
        config = Config()
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        config.request_timeout = timeout
        config.fetch_images = False  # Don't download pictures
        config.memoize_articles = False # Do not cache

        article = Article(url, config=config, language='zh') # Default Chinese，But it also supports other
        article.download()
        article.parse()

        # Second-rate
        text = article.text.strip()

        # Second-rate，Second-rate
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        return text[:1500]  # Limit return length（Than bs4 slightly more，because newspaper Parse cleaner）
    except Exception as e:
        logger.debug(f"Fetch content failed for {url}: {e}")

    return ""


@dataclass
class SearchResult:
    """Search result data class"""
    title: str
    snippet: str  # summary
    url: str
    source: str  # Source website
    published_date: Optional[str] = None
    relevance_score: Optional[int] = None
    relevance_category: Optional[str] = None
    relevance_reasons: Optional[List[str]] = None
    
    def to_text(self) -> str:
        """Convert to text format"""
        date_str = f" ({self.published_date})" if self.published_date else ""
        relevance_parts: List[str] = []
        if self.relevance_category:
            relevance_parts.append(self.relevance_category)
        if self.relevance_score is not None:
            relevance_parts.append(f"score={self.relevance_score}")
        if self.relevance_reasons:
            relevance_parts.append(f"Basis: {'; '.join(self.relevance_reasons[:3])}")
        relevance_str = f"\nRelevance: {'; '.join(relevance_parts)}" if relevance_parts else ""
        return f"【{self.source}】{self.title}{date_str}\n{self.snippet}{relevance_str}"


@dataclass 
class SearchResponse:
    """search response"""
    query: str
    results: List[SearchResult]
    provider: str  # Search engine used
    success: bool = True
    error_message: Optional[str] = None
    search_time: float = 0.0  # Search time elapsed (seconds)
    
    def to_context(self, max_results: int = 5) -> str:
        """Convert search results to usable AI Analysis context"""
        if not self.success or not self.results:
            return f"Search '{self.query}' returned no results."
        
        lines = [f"[{self.query} Search Results] (Provider: {self.provider})"]
        for i, result in enumerate(self.results[:max_results], 1):
            lines.append(f"\n{i}. {result.to_text()}")
        
        return "\n".join(lines)


class BaseSearchProvider(ABC):
    """Search engine base class"""
    
    def __init__(self, api_keys: List[str], name: str):
        """
        Initialize search engine
        
        Args:
            api_keys: API Key list（Support multiple key load balancing）
            name: Search engine name
        """
        self._api_keys = api_keys
        self._name = name
        self._key_cycle = cycle(api_keys) if api_keys else None
        self._key_usage: Dict[str, int] = {key: 0 for key in api_keys}
        self._key_errors: Dict[str, int] = {key: 0 for key in api_keys}
        self._state_lock = threading.RLock()
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_available(self) -> bool:
        """Check if any are available API Key"""
        return bool(self._api_keys)
    
    def _get_next_key(self) -> Optional[str]:
        """
        Get the next available API Key（load balancing）
        
        Strategy：polling + Skip too many errors key
        """
        with self._state_lock:
            if not self._key_cycle:
                return None
            
            # Second-rate key
            for _ in range(len(self._api_keys)):
                key = next(self._key_cycle)
                # Second-rate key（Second-rate 3 Second-rate）
                if self._key_errors.get(key, 0) < 3:
                    return key
            
            # all key Reset the error count and return the first，Reset the error count and return the first
            logger.warning(f"[{self._name}] all API Key There are error records，Reset error count")
            self._key_errors = {key: 0 for key in self._api_keys}
            return self._api_keys[0] if self._api_keys else None
    
    def _record_success(self, key: str) -> None:
        """Record successful use"""
        with self._state_lock:
            self._key_usage[key] = self._key_usage.get(key, 0) + 1
            # Decrement error count on success
            if key in self._key_errors and self._key_errors[key] > 0:
                self._key_errors[key] -= 1
    
    def _record_error(self, key: str) -> None:
        """Log errors"""
        with self._state_lock:
            self._key_errors[key] = self._key_errors.get(key, 0) + 1
            error_count = self._key_errors[key]
        logger.warning(f"[{self._name}] API Key {key[:8]}... error count: {error_count}")
    
    @abstractmethod
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Perform a search（Subclass implementation）"""
        pass
    
    def _execute_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        days: int = 7,
        api_key: Optional[str] = None,
        **search_kwargs: Any,
    ) -> SearchResponse:
        """Run the shared search flow with an optional preselected API key."""
        api_key = api_key or self._get_next_key()
        if not api_key:
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=f"{self._name} API Key not configured"
            )

        start_time = time.time()
        try:
            response = self._do_search(query, api_key, max_results, days=days, **search_kwargs)
            response.search_time = time.time() - start_time

            if response.success:
                self._record_success(api_key)
                logger.info(f"[{self._name}] search '{query}' success，return {len(response.results)} results，time consuming {response.search_time:.2f}s")
            else:
                self._record_error(api_key)

            return response

        except Exception as e:
            self._record_error(api_key)
            elapsed = time.time() - start_time
            logger.error(f"[{self._name}] search '{query}' fail: {e}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=str(e),
                search_time=elapsed
            )

    def search(self, query: str, max_results: int = 5, days: int = 7) -> SearchResponse:
        """
        Perform a search
        
        Args:
            query: Search keywords
            max_results: Maximum number of results returned
            days: Search the time range of the last few days（default7sky）
            
        Returns:
            SearchResponse object
        """
        return self._execute_search(query, max_results=max_results, days=days)


class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily search engine
    
    Features：
    - Designed for AI/LLM Optimized search API
    - Free version monthly 1000 requests
    - Return structured search results
    
    document：https://docs.tavily.com/
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Tavily")
    
    def _do_search(
        self,
        query: str,
        api_key: str,
        max_results: int,
        days: int = 7,
        topic: Optional[str] = None,
    ) -> SearchResponse:
        """implement Tavily search"""
        try:
            from tavily import TavilyClient
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="tavily-python Not installed，Please run: pip install tavily-python"
            )
        
        try:
            client = TavilyClient(api_key=api_key)
            
            # Perform a search（optimization：useadvanceddepth、Limit the last few days）
            search_kwargs: Dict[str, Any] = {
                "query": query,
                "search_depth": "advanced",  # advanced Get more results
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
                "days": days,  # Search content for the last few days
            }
            if topic is not None:
                search_kwargs["topic"] = topic

            response = client.search(
                **search_kwargs,
            )
            
            # Record raw response to log
            logger.info(f"[Tavily] Search completed，query='{query}', return {len(response.get('results', []))} results")
            logger.debug(f"[Tavily] original response: {response}")
            
            # Parse results
            results = []
            for item in response.get('results', []):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=item.get('content', '')[:500],  # before interception500word
                    url=item.get('url', ''),
                    source=self._extract_domain(item.get('url', '')),
                    published_date=item.get('published_date') or item.get('publishedDate'),
                ))
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            # Check if it is a quota issue
            if 'rate limit' in error_msg.lower() or 'quota' in error_msg.lower():
                error_msg = f"API Quota exhausted: {error_msg}"
            
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )

    def search(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
        topic: Optional[str] = None,
    ) -> SearchResponse:
        """implement Tavily search，from topic。"""
        if topic is None:
            return super().search(query, max_results=max_results, days=days)

        api_key = self._get_next_key()
        if not api_key:
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=f"{self._name} Not configured API Key"
            )

        start_time = time.time()
        try:
            response = self._do_search(query, api_key, max_results, days=days, topic=topic)
            response.search_time = time.time() - start_time

            if response.success:
                self._record_success(api_key)
                logger.info(f"[{self._name}] search '{query}' success，return {len(response.results)} results，time consuming {response.search_time:.2f}s")
            else:
                self._record_error(api_key)

            return response

        except Exception as e:
            self._record_error(api_key)
            elapsed = time.time() - start_time
            logger.error(f"[{self._name}] search '{query}' fail: {e}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=str(e),
                search_time=elapsed
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """from URL Extract domain name as source"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'unknown source'
        except Exception:
            return 'unknown source'


class SerpAPISearchProvider(BaseSearchProvider):
    """
    SerpAPI search engine
    
    Features：
    - support Google、Bing、Baidu and other search engines
    - Free version monthly 100 requests
    - Return real search results
    
    document：https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis
    """

    _ORGANIC_CONTENT_FETCH_LIMIT = 1
    _ORGANIC_CONTENT_FETCH_RANK_LIMIT = 2
    _ORGANIC_CONTENT_FETCH_TIMEOUT = 2
    _ORGANIC_SNIPPET_SUFFICIENT_LENGTH = 140
    _ORGANIC_FETCHED_PREVIEW_LENGTH = 320
    _SKIPPED_CONTENT_FETCH_SUFFIXES = (
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".webp",
        ".zip",
        ".rar",
        ".7z",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
        ".csv",
    )
    _SKIPPED_CONTENT_FETCH_QUERY_KEYS = {
        "attachment",
        "attachment_file",
        "doc",
        "document",
        "download",
        "download_file",
        "file",
        "file_name",
        "filename",
        "file_path",
        "filepath",
        "resource",
        "resource_file",
    }
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "SerpAPI")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """implement SerpAPI search"""
        try:
            from serpapi import GoogleSearch
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="google-search-results Not installed，Please run: pip install google-search-results"
            )
        
        try:
            # Determine time range parameters tbs
            tbs = "qdr:w"  # Default one week
            if days <= 1:
                tbs = "qdr:d"  # past24Hour
            elif days <= 7:
                tbs = "qdr:w"  # past week
            elif days <= 30:
                tbs = "qdr:m"  # past month
            else:
                tbs = "qdr:y"  # past year

            # use Google search (get Knowledge Graph, Answer Box wait)
            params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "google_domain": "google.com.hk", # Use Hong Kong Google，Chinese support is better
                "hl": "zh-cn",  # Chinese interface
                "gl": "cn",     # China region preference
                "tbs": tbs,     # time range limit
                "num": max_results # Number of results requested，Notice：Google APISometimes not strictly followed
            }
            
            search = GoogleSearch(params)
            response = search.get_dict()
            
            # Record raw response to log
            logger.debug(f"[SerpAPI] original response keys: {response.keys()}")
            
            # Parse results
            results = []
            
            # 1. parse Knowledge Graph (Knowledge graph)
            kg = response.get('knowledge_graph', {})
            if kg:
                title = kg.get('title', 'Knowledge graph')
                desc = kg.get('description', '')
                
                # Extract extra attributes
                details = []
                for key in ['type', 'founded', 'headquarters', 'employees', 'ceo']:
                    val = kg.get(key)
                    if val:
                        details.append(f"{key}: {val}")
                        
                snippet = f"{desc}\n" + " | ".join(details) if details else desc
                
                results.append(SearchResult(
                    title=f"[Knowledge graph] {title}",
                    snippet=snippet,
                    url=kg.get('source', {}).get('link', ''),
                    source="Google Knowledge Graph"
                ))
                
            # 2. parse Answer Box (Quote cards/Quote cards)
            ab = response.get('answer_box', {})
            if ab:
                ab_title = ab.get('title', 'Selected answers')
                ab_snippet = ""
                
                # Financial answers
                if ab.get('type') == 'finance_results':
                    stock = ab.get('stock', '')
                    price = ab.get('price', '')
                    currency = ab.get('currency', '')
                    movement = ab.get('price_movement', {})
                    mv_val = movement.get('percentage', 0)
                    mv_dir = movement.get('movement', '')
                    
                    ab_title = f"[Quote cards] {stock}"
                    ab_snippet = f"ups and downs: {price} {currency}\nups and downs: {mv_dir} {mv_val}%"
                    
                    # Extract table data
                    if 'table' in ab:
                        table_data = []
                        for row in ab['table']:
                            if 'name' in row and 'value' in row:
                                table_data.append(f"{row['name']}: {row['value']}")
                        if table_data:
                            ab_snippet += "\n" + "; ".join(table_data)
                            
                # Normal text answer
                elif 'snippet' in ab:
                    ab_snippet = ab.get('snippet', '')
                    list_items = ab.get('list', [])
                    if list_items:
                        ab_snippet += "\n" + "\n".join([f"- {item}" for item in list_items])
                
                elif 'answer' in ab:
                    ab_snippet = ab.get('answer', '')
                    
                if ab_snippet:
                    results.append(SearchResult(
                        title=f"[Selected answers] {ab_title}",
                        snippet=ab_snippet,
                        url=ab.get('link', '') or ab.get('displayed_link', ''),
                        source="Google Answer Box"
                    ))

            # 3. parse Related Questions (Related questions)
            rqs = response.get('related_questions', [])
            for rq in rqs[:3]: # Before picking up3indivual
                question = rq.get('question', '')
                snippet = rq.get('snippet', '')
                link = rq.get('link', '')
                
                if question and snippet:
                     results.append(SearchResult(
                        title=f"[Related questions] {question}",
                        snippet=snippet,
                        url=link,
                        source="Google Related Questions"
                     ))

            # 4. parse Organic Results (organic search results)
            organic_results = response.get('organic_results', [])
            organic_content_fetch_attempts = 0

            for rank, item in enumerate(organic_results[:max_results]):
                link = item.get('link', '')
                rich_extensions = self._extract_rich_snippet_extensions(item)
                snippet = self._build_organic_snippet(item, rich_extensions=rich_extensions)

                if self._should_fetch_organic_content(
                    link=link,
                    snippet=snippet,
                    rank=rank,
                    fetched_count=organic_content_fetch_attempts,
                    has_structured_summary=bool(rich_extensions),
                ):
                    organic_content_fetch_attempts += 1
                    try:
                        fetched_content = fetch_url_content(
                            link,
                            timeout=self._ORGANIC_CONTENT_FETCH_TIMEOUT,
                        )
                        if fetched_content:
                            snippet = self._merge_organic_snippet_with_content(
                                snippet,
                                fetched_content,
                            )
                    except Exception as e:
                        logger.debug(f"[SerpAPI] Fetch content failed: {e}")

                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=snippet[:1000], # Limit total length
                    url=link,
                    source=item.get('source', self._extract_domain(link)),
                    published_date=item.get('date'),
                ))

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """from URL Extract domain name"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '') or 'unknown source'
        except Exception:
            return 'unknown source'

    @classmethod
    def _normalize_organic_text(cls, value: Any) -> str:
        """standardization SerpAPI organic text field。"""
        text = "" if value is None else str(value)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _extract_rich_snippet_extensions(cls, item: Dict[str, Any]) -> List[str]:
        """extract rich_snippet Structured snippets already in，Prioritize reuse API original return。"""
        rich_snippet = item.get("rich_snippet")
        if not isinstance(rich_snippet, dict):
            return []

        extensions: List[str] = []
        seen: set[str] = set()

        for section in ("top", "bottom"):
            section_data = rich_snippet.get(section)
            if not isinstance(section_data, dict):
                continue

            raw_extensions = section_data.get("extensions")
            if isinstance(raw_extensions, (list, tuple, set)):
                for raw_value in raw_extensions:
                    value = cls._normalize_organic_text(raw_value)
                    if not value or value in seen:
                        continue
                    seen.add(value)
                    extensions.append(value)

            for raw_value in cls._flatten_rich_snippet_values(
                section_data.get("detected_extensions")
            ):
                if raw_value in seen:
                    continue
                seen.add(raw_value)
                extensions.append(raw_value)

        return extensions

    @classmethod
    def _flatten_rich_snippet_values(
        cls,
        value: Any,
        *,
        label: Optional[str] = None,
        allow_unlabeled_scalar: bool = False,
    ) -> List[str]:
        """Bundle rich_snippet.detected_extensions Flatten to readable text。"""
        if isinstance(value, dict):
            flattened: List[str] = []
            for key, nested_value in value.items():
                flattened.extend(
                    cls._flatten_rich_snippet_values(
                        nested_value,
                        label=cls._normalize_organic_text(str(key)).replace("_", " "),
                    )
                )
            return flattened

        if isinstance(value, (list, tuple, set)):
            flattened: List[str] = []
            for nested_value in value:
                flattened.extend(
                    cls._flatten_rich_snippet_values(
                        nested_value,
                        label=label,
                        allow_unlabeled_scalar=True,
                    )
                )
            return flattened

        text = cls._normalize_organic_text(value)
        if not text:
            return []

        if label:
            return [f"{label}: {text}"]

        if allow_unlabeled_scalar:
            return [text]

        return []

    @classmethod
    def _build_organic_snippet(
        cls,
        item: Dict[str, Any],
        *,
        rich_extensions: Optional[List[str]] = None,
    ) -> str:
        """Build organic result summary，Try to consume first SerpAPI Information returned。"""
        snippet = cls._normalize_organic_text(item.get("snippet", ""))
        if rich_extensions is None:
            rich_extensions = cls._extract_rich_snippet_extensions(item)

        if rich_extensions:
            rich_text = " | ".join(rich_extensions)
            if rich_text and rich_text not in snippet:
                snippet = f"{snippet}\n{rich_text}".strip() if snippet else rich_text

        return snippet

    @classmethod
    def _matches_skipped_content_fetch_suffix(cls, value: Any) -> bool:
        """Determine whether the link fragment points to an attachment or other non- HTML resource。"""
        normalized_value = cls._normalize_organic_text(value).lower()
        if not normalized_value:
            return False

        decoded_value = unquote(normalized_value)
        if decoded_value.endswith(cls._SKIPPED_CONTENT_FETCH_SUFFIXES):
            return True

        return urlparse(decoded_value).path.lower().endswith(
            cls._SKIPPED_CONTENT_FETCH_SUFFIXES
        )

    @classmethod
    def _matches_skipped_content_fetch_query_param(
        cls, key: Any, value: Any
    ) -> bool:
        """Skip body crawl only for few explicit attachment parameters，Avoid accidental injury to ordinary people HTML page。"""
        normalized_key = cls._normalize_organic_text(key)
        if not normalized_key:
            return False

        snake_key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized_key)
        canonical_key = re.sub(r"[^a-z0-9]+", "_", snake_key.lower()).strip("_")
        if canonical_key not in cls._SKIPPED_CONTENT_FETCH_QUERY_KEYS:
            return False

        return cls._matches_skipped_content_fetch_suffix(value)

    @classmethod
    def _should_fetch_organic_content(
        cls,
        *,
        link: Any,
        snippet: str,
        rank: int,
        fetched_count: int,
        has_structured_summary: bool,
    ) -> bool:
        """Only a very small number of high-ranking results with obviously insufficient abstracts will be supplemented with the main text.。"""
        if fetched_count >= cls._ORGANIC_CONTENT_FETCH_LIMIT:
            return False

        if rank >= cls._ORGANIC_CONTENT_FETCH_RANK_LIMIT:
            return False

        if has_structured_summary:
            return False

        if len(snippet) >= cls._ORGANIC_SNIPPET_SUFFICIENT_LENGTH:
            return False

        if not isinstance(link, str):
            return False

        if not link or not link.startswith(("http://", "https://")):
            return False

        parsed_link = urlparse(link)
        if parsed_link.scheme not in {"http", "https"}:
            return False

        if cls._matches_skipped_content_fetch_suffix(parsed_link.path):
            return False

        for key, value in parse_qsl(parsed_link.query, keep_blank_values=True):
            if cls._matches_skipped_content_fetch_query_param(key, value):
                return False

        return True

    @classmethod
    def _merge_organic_snippet_with_content(cls, snippet: str, content: str) -> str:
        """Enhance with shorter text preview snippet，Avoid elongating the time and return volume of a single search。"""
        normalized = cls._normalize_organic_text(content)
        if not normalized:
            return snippet

        preview = normalized[:cls._ORGANIC_FETCHED_PREVIEW_LENGTH]
        if len(normalized) > cls._ORGANIC_FETCHED_PREVIEW_LENGTH:
            preview = f"{preview}..."

        if snippet:
            return f"{snippet}\n\n【Web page details】\n{preview}"

        return f"【Web page details】\n{preview}"


class BochaSearchProvider(BaseSearchProvider):
    """
    Bocha search engine
    
    Features：
    - Designed forAIOptimized Chinese searchAPI
    - Accurate results、Abstract complete
    - Supports time range filtering andAIsummary
    - compatibleBing Search APIFormat
    
    document：https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Bocha")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Perform a Bocha search"""
        try:
            import requests
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="requests Not installed，Please run: pip install requests"
            )
        
        try:
            # API endpoint
            url = "https://api.bocha.cn/v1/web-search"
            
            # Request header
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Determine time range
            freshness = "oneWeek"
            if days <= 1:
                freshness = "oneDay"
            elif days <= 7:
                freshness = "oneWeek"
            elif days <= 30:
                freshness = "oneMonth"
            else:
                freshness = "oneYear"

            # Request parameters（strictly followAPIdocument）
            payload = {
                "query": query,
                "freshness": freshness,  # dynamic time range
                "summary": True,  # enableAIsummary
                "count": min(max_results, 50)  # maximum50strip
            }
            
            # Perform a search（With instantaneous SSL/Network error retry）
            response = _post_with_retry(url, headers=headers, json=payload, timeout=10)
            
            # examineHTTPstatus code
            if response.status_code != 200:
                # Try to parse the error message
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        error_data = response.json()
                        error_message = error_data.get('message', response.text)
                    else:
                        error_message = response.text
                except Exception:
                    error_message = response.text
                
                # Handle according to error code
                if response.status_code == 403:
                    error_msg = f"Insufficient balance: {error_message}"
                elif response.status_code == 401:
                    error_msg = f"API KEYinvalid: {error_message}"
                elif response.status_code == 400:
                    error_msg = f"Request parameter error: {error_message}"
                elif response.status_code == 429:
                    error_msg = f"Request frequency reaches limit: {error_message}"
                else:
                    error_msg = f"HTTP {response.status_code}: {error_message}"
                
                logger.warning(f"[Bocha] Search failed: {error_msg}")
                
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # Parse response
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"responseJSONParsing failed: {str(e)}"
                logger.error(f"[Bocha] {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # Check responsecode
            if data.get('code') != 200:
                error_msg = data.get('msg') or f"APIReturn error code: {data.get('code')}"
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # Record raw response to log
            logger.info(f"[Bocha] Search completed，query='{query}'")
            logger.debug(f"[Bocha] original response: {data}")
            
            # Parse search results
            results = []
            web_pages = data.get('data', {}).get('webPages', {})
            value_list = web_pages.get('value', [])
            
            for item in value_list[:max_results]:
                # priority usesummary（AIsummary），fallbackarrivesnippet
                snippet = item.get('summary') or item.get('snippet', '')
                
                # Cut summary length
                if snippet:
                    snippet = snippet[:500]
                
                results.append(SearchResult(
                    title=item.get('name', ''),
                    snippet=snippet,
                    url=item.get('url', ''),
                    source=item.get('siteName') or self._extract_domain(item.get('url', '')),
                    published_date=item.get('datePublished'),  # UTC+8Format，No conversion required
                ))
            
            logger.info(f"[Bocha] Parsed successfully {len(results)} results")
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"Network request failed: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"unknown error: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """from URL Extract domain name as source"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'unknown source'
        except Exception:
            return 'unknown source'


class AnspireSearchProvider(BaseSearchProvider):
    """
    Anspire Search search engine
    
    Features：
    - ForAIEcological next-generation real-time intelligent search engine
    - Accurate results、Fast response
    - Good for stock news and market intelligence searches
    
    document: https://open.anspire.cn/document/docs/searchApi/
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Anspire")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7, region_mode: int = 0) -> SearchResponse:
        """implement Anspire search"""
        try:
            import requests
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="requests Not installed，Please run：pip install requests"
            )
        
        try:
            # API endpoint
            url = "https://plugin.anspire.cn/api/ntsearch/search"
            
            # Request header
            headers = {
                'Authorization': f'Bearer {api_key}'
            }

            # Request parameters
            payload = {
                "query": query,
                "top_k": min(max_results,50), 
                "FromTime": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"),
                "ToTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "region_mode": region_mode
            }
            
            # Perform a search
            response = _get_with_retry(url, headers=headers, params=payload, timeout=10)
            
            # examine HTTP status code
            if response.status_code != 200:
                # Try to parse the error message
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        error_data = response.json()
                        error_message = error_data.get('message', response.text)
                    else:
                        error_message = response.text
                except Exception:
                    error_message = response.text
                
                # Handle according to error code
                if response.status_code == 403:
                    error_msg = f"Insufficient balance or insufficient permissions：{error_message}"
                elif response.status_code == 401:
                    error_msg = f"API KEY invalid：{error_message}"
                elif response.status_code == 400:
                    error_msg = f"Request parameter error：{error_message}"
                else:
                    error_msg = f"HTTP {response.status_code}: {error_message}"
                
                logger.warning(f"[Anspire] Search failed：{error_msg}")
                
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # Parse response
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"response JSON Parsing failed：{str(e)}"
                logger.error(f"[Anspire] {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            if 'code' in data and data.get('code') != 200:
                error_msg = data.get('msg') or f"API Return error code：{data.get('code')}"
                logger.warning(f"[Anspire] Search failed：{error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            if 'results' not in data:
                error_msg = "Field results Field"
                logger.error(f"[Anspire] {error_msg}，original response：{data}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # Record raw response to log
            logger.info(f"[Anspire] Search completed，query='{query}'")
            logger.debug(f"[Anspire] original response：{data}")
            
            results = []
            value_list = data.get('results', [])
            
            for item in value_list[:max_results]:
                snippet = item.get('content')
                if snippet and isinstance(snippet, str) and len(snippet) > 500:
                    snippet = snippet[:500] + "..."
                
                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=snippet,
                    url=item.get('url', ''),
                    source=self._extract_domain(item.get('url', '')),
                    published_date=item.get('date', '')
                ))
            
            logger.info(f"[Anspire] Parsed successfully {len(results)} results")
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            logger.error(f"[Anspire] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"Network request failed：{str(e)}"
            logger.error(f"[Anspire] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"unknown error：{str(e)}"
            logger.error(f"[Anspire] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """from URL Extract domain name as source"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'unknown source'
        except Exception:
            return 'unknown source'


class MiniMaxSearchProvider(BaseSearchProvider):
    """
    MiniMax Web Search (Coding Plan API)

    Features:
    - Backed by MiniMax Coding Plan subscription
    - Returns structured organic results with title/link/snippet/date
    - No native time-range parameter; time filtering is done via query
      augmentation and client-side date filtering
    - Circuit-breaker protection: 3 consecutive failures -> 300s cooldown

    API endpoint: POST https://api.minimaxi.com/v1/coding_plan/search
    """

    API_ENDPOINT = "https://api.minimaxi.com/v1/coding_plan/search"

    # Circuit-breaker settings
    _CB_FAILURE_THRESHOLD = 3
    _CB_COOLDOWN_SECONDS = 300  # 5 minutes

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "MiniMax")
        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open_until: float = 0.0

    @property
    def is_available(self) -> bool:
        """Check availability considering circuit breaker state."""
        with self._state_lock:
            if not self._api_keys:
                return False
            if self._consecutive_failures >= self._CB_FAILURE_THRESHOLD:
                if time.time() < self._circuit_open_until:
                    return False
                # Cooldown expired -> half-open, allow one probe
            return True

    def _record_success(self, key: str) -> None:
        with self._state_lock:
            super()._record_success(key)
            # Reset circuit breaker on success
            self._consecutive_failures = 0
            self._circuit_open_until = 0.0

    def _record_error(self, key: str) -> None:
        warning_message = None
        with self._state_lock:
            super()._record_error(key)
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._CB_FAILURE_THRESHOLD:
                self._circuit_open_until = time.time() + self._CB_COOLDOWN_SECONDS
                warning_message = (
                    f"[MiniMax] Circuit breaker OPEN – "
                    f"{self._consecutive_failures} consecutive failures, "
                    f"cooldown {self._CB_COOLDOWN_SECONDS}s"
                )
        if warning_message:
            logger.warning(warning_message)

    # ------------------------------------------------------------------
    # Time-range helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _time_hint(days: int, is_chinese: bool = True) -> str:
        """Build a time-hint string to append to the search query."""
        if is_chinese:
            if days <= 1:
                return "today"
            elif days <= 3:
                return "last three days"
            elif days <= 7:
                return "last week"
            else:
                return "last month"
        else:
            if days <= 1:
                return "today"
            elif days <= 3:
                return "past 3 days"
            elif days <= 7:
                return "past week"
            else:
                return "past month"

    @staticmethod
    def _is_within_days(date_str: Optional[str], days: int) -> bool:
        """Check whether *date_str* falls within the last *days* days.

        Accepts common formats: ``2025-06-01``, ``2025/06/01``,
        ``Jun 1, 2025``, ISO-8601 with timezone, etc.
        Returns True when date_str is None or unparseable (keep the result).
        """
        if not date_str:
            return True
        try:
            from dateutil import parser as dateutil_parser
            dt = dateutil_parser.parse(date_str, fuzzy=True)
            from datetime import timedelta, timezone
            now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
            return (now - dt) <= timedelta(days=days + 1)  # +1 buffer
        except Exception:
            return True  # Keep result when date is unparseable

    # ------------------------------------------------------------------

    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Execute MiniMax web search."""
        try:
            # Detect language hint from query (simple heuristic)
            has_cjk = any('\u4e00' <= ch <= '\u9fff' for ch in query)
            time_hint = self._time_hint(days, is_chinese=has_cjk)
            augmented_query = f"{query} {time_hint}"

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'MM-API-Source': 'Minimax-MCP',
            }
            payload = {"q": augmented_query}

            response = _post_with_retry(
                self.API_ENDPOINT, headers=headers, json=payload, timeout=15
            )

            # HTTP error handling
            if response.status_code != 200:
                error_msg = self._parse_http_error(response)
                logger.warning(f"[MiniMax] Search failed: {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg,
                )

            data = response.json()

            # Check base_resp status
            base_resp = data.get('base_resp', {})
            if base_resp.get('status_code', 0) != 0:
                error_msg = base_resp.get('status_msg', 'Unknown API error')
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg,
                )

            logger.info(f"[MiniMax] Search done, query='{query}'")
            logger.debug(f"[MiniMax] Raw response keys: {list(data.keys())}")

            # Parse organic results
            results: List[SearchResult] = []
            for item in data.get('organic', []):
                date_val = item.get('date')

                # Client-side time filtering
                if not self._is_within_days(date_val, days):
                    continue

                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=(item.get('snippet', '') or '')[:500],
                    url=item.get('link', ''),
                    source=self._extract_domain(item.get('link', '')),
                    published_date=date_val,
                ))

                if len(results) >= max_results:
                    break

            logger.info(f"[MiniMax] Parsed {len(results)} results (after time filter)")

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )

        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            logger.error(f"[MiniMax] {error_msg}")
            return SearchResponse(
                query=query, results=[], provider=self.name,
                success=False, error_message=error_msg,
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e}"
            logger.error(f"[MiniMax] {error_msg}")
            return SearchResponse(
                query=query, results=[], provider=self.name,
                success=False, error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"[MiniMax] {error_msg}")
            return SearchResponse(
                query=query, results=[], provider=self.name,
                success=False, error_message=error_msg,
            )

    @staticmethod
    def _parse_http_error(response) -> str:
        """Parse HTTP error response from MiniMax API."""
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                err = response.json()
                base_resp = err.get('base_resp', {})
                msg = base_resp.get('status_msg') or err.get('message') or str(err)
                return msg
            return response.text[:200]
        except Exception:
            return f"HTTP {response.status_code}: {response.text[:200]}"

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL as source label."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'unknown source'
        except Exception:
            return 'unknown source'


class BraveSearchProvider(BaseSearchProvider):
    """
    Brave Search search engine

    Features：
    - Index exceeds
    - Index exceeds300billion pages
    - Free tier available
    - Support time range filtering

    document：https://brave.com/search/api/
    """

    API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Brave")

    def _do_search(
        self,
        query: str,
        api_key: str,
        max_results: int,
        days: int = 7,
        search_lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> SearchResponse:
        """implement Brave search"""
        try:
            # Request header
            headers = {
                'X-Subscription-Token': api_key,
                'Accept': 'application/json'
            }

            # Determine time range（freshness parameter）
            if days <= 1:
                freshness = "pd"  # Past day (24Hour)
            elif days <= 7:
                freshness = "pw"  # Past week
            elif days <= 30:
                freshness = "pm"  # Past month
            else:
                freshness = "py"  # Past year

            # Request parameters
            params = {
                "q": query,
                "count": min(max_results, 20),  # Brave maximum support20strip
                "freshness": freshness,
                "safesearch": "moderate"
            }
            if search_lang:
                params["search_lang"] = search_lang
            if country:
                params["country"] = country

            # Perform a search（GET ask）
            response = requests.get(
                self.API_ENDPOINT,
                headers=headers,
                params=params,
                timeout=10
            )

            # examineHTTPstatus code
            if response.status_code != 200:
                error_msg = self._parse_error(response)
                logger.warning(f"[Brave] Search failed: {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )

            # Parse response
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"responseJSONParsing failed: {str(e)}"
                logger.error(f"[Brave] {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )

            logger.info(f"[Brave] Search completed，query='{query}'")
            logger.debug(f"[Brave] original response: {data}")

            # Parse search results
            results = []
            web_data = data.get('web', {})
            web_results = web_data.get('results', [])

            for item in web_results[:max_results]:
                # Parse release date（ISO 8601 Format）
                published_date = None
                age = item.get('age') or item.get('page_age')
                if age:
                    try:
                        # Convert ISO Formatted as a simple date string
                        dt = datetime.fromisoformat(age.replace('Z', '+00:00'))
                        published_date = dt.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        published_date = age  # Use original value when parsing fails

                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=item.get('description', '')[:500],  # Intercepted to500character
                    url=item.get('url', ''),
                    source=self._extract_domain(item.get('url', '')),
                    published_date=published_date
                ))

            logger.info(f"[Brave] Parsed successfully {len(results)} results")

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True
            )

        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"Network request failed: {str(e)}"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"unknown error: {str(e)}"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )

    def _parse_error(self, response) -> str:
        """Parse error response"""
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                error_data = response.json()
                # Brave API Returned error format
                if 'message' in error_data:
                    return error_data['message']
                if 'error' in error_data:
                    return error_data['error']
                return str(error_data)
            return response.text[:200]
        except Exception:
            return f"HTTP {response.status_code}: {response.text[:200]}"

    @staticmethod
    def _extract_domain(url: str) -> str:
        """from URL Extract domain name as source"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'unknown source'
        except Exception:
            return 'unknown source'

    def search(
        self,
        query: str,
        max_results: int = 5,
        days: int = 7,
        search_lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> SearchResponse:
        """implement Brave search，Regional and language preferences can be passed in on a per-caller basis。"""
        if search_lang is None and country is None:
            return super().search(query, max_results=max_results, days=days)

        return self._execute_search(
            query,
            max_results=max_results,
            days=days,
            search_lang=search_lang,
            country=country,
        )


class SearXNGSearchProvider(BaseSearchProvider):
    """
    SearXNG search engine (self-hosted, no quota).

    Self-hosted instances are used when explicitly configured.
    Otherwise, the provider can lazily discover public instances from
    searx.space and rotate across them with per-request failover.
    """

    PUBLIC_INSTANCES_URL = "https://searx.space/data/instances.json"
    PUBLIC_INSTANCES_CACHE_TTL_SECONDS = 3600
    PUBLIC_INSTANCES_STALE_REFRESH_BACKOFF_SECONDS = 60
    PUBLIC_INSTANCES_POOL_LIMIT = 20
    PUBLIC_INSTANCES_MAX_ATTEMPTS = 3
    PUBLIC_INSTANCES_TIMEOUT_SECONDS = 5
    SELF_HOSTED_TIMEOUT_SECONDS = 10

    _public_instances_cache: Optional[Tuple[float, List[str]]] = None
    _public_instances_stale_retry_after: float = 0.0
    _public_instances_lock = threading.Lock()

    def __init__(self, base_urls: Optional[List[str]] = None, *, use_public_instances: bool = False):
        normalized_base_urls = [url.rstrip("/") for url in (base_urls or []) if url.strip()]
        super().__init__(normalized_base_urls, "SearXNG")
        self._base_urls = normalized_base_urls
        self._use_public_instances = bool(use_public_instances and not self._base_urls)
        self._cursor = 0
        self._cursor_lock = threading.Lock()

    @property
    def is_available(self) -> bool:
        return bool(self._base_urls) or self._use_public_instances

    @classmethod
    def reset_public_instance_cache(cls) -> None:
        """Reset the shared searx.space cache (used by tests)."""
        with cls._public_instances_lock:
            cls._public_instances_cache = None
            cls._public_instances_stale_retry_after = 0.0

    @staticmethod
    def _parse_http_error(response) -> str:
        """Parse HTTP error details for easier diagnostics."""
        try:
            raw_content_type = response.headers.get("content-type", "")
            content_type = raw_content_type if isinstance(raw_content_type, str) else ""
            if "json" in content_type:
                error_data = response.json()
                if isinstance(error_data, dict):
                    message = error_data.get("error") or error_data.get("message")
                    if message:
                        return str(message)
                return str(error_data)
            raw_text = getattr(response, "text", "")
            body = raw_text.strip() if isinstance(raw_text, str) else ""
            return body[:200] if body else f"HTTP {response.status_code}"
        except Exception:
            raw_text = getattr(response, "text", "")
            body = raw_text if isinstance(raw_text, str) else ""
            return f"HTTP {response.status_code}: {body[:200]}"

    @staticmethod
    def _time_range(days: int) -> str:
        if days <= 1:
            return "day"
        if days <= 7:
            return "week"
        if days <= 30:
            return "month"
        return "year"

    @classmethod
    def _search_latency_seconds(cls, instance_data: Dict[str, Any]) -> float:
        timing = (instance_data.get("timing") or {}).get("search") or {}
        all_timing = timing.get("all")
        if isinstance(all_timing, dict):
            for key in ("mean", "median"):
                value = all_timing.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        return float("inf")

    @classmethod
    def _extract_public_instances(cls, payload: Any) -> List[str]:
        if not isinstance(payload, dict):
            return []

        instances = payload.get("instances")
        if not isinstance(instances, dict):
            return []

        ranked: List[Tuple[float, float, str]] = []
        for raw_url, item in instances.items():
            if not isinstance(raw_url, str) or not isinstance(item, dict):
                continue
            if item.get("network_type") != "normal":
                continue
            http_status = (item.get("http") or {}).get("status_code")
            if http_status != 200:
                continue
            timing = (item.get("timing") or {}).get("search") or {}
            uptime = timing.get("success_percentage")
            if not isinstance(uptime, (int, float)) or float(uptime) <= 0:
                continue

            ranked.append(
                (
                    float(uptime),
                    cls._search_latency_seconds(item),
                    raw_url.rstrip("/"),
                )
            )

        ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
        return [url for _, _, url in ranked[: cls.PUBLIC_INSTANCES_POOL_LIMIT]]

    @classmethod
    def _get_public_instances(cls) -> List[str]:
        now = time.time()
        with cls._public_instances_lock:
            stale_urls: List[str] = []
            if cls._public_instances_cache is None and cls._public_instances_stale_retry_after > now:
                logger.debug(
                    "[SearXNG] Public instance cold start refresh backoff，Remaining %.0fs",
                    cls._public_instances_stale_retry_after - now,
                )
                return []
            if cls._public_instances_cache is not None:
                cached_at, cached_urls = cls._public_instances_cache
                if now - cached_at < cls.PUBLIC_INSTANCES_CACHE_TTL_SECONDS:
                    return list(cached_urls)
                stale_urls = list(cached_urls)
                if cls._public_instances_stale_retry_after > now:
                    logger.debug(
                        "[SearXNG] Public instance refresh backoff，Continue to use expired cache，Remaining %.0fs",
                        cls._public_instances_stale_retry_after - now,
                    )
                    return stale_urls

            try:
                response = requests.get(
                    cls.PUBLIC_INSTANCES_URL,
                    timeout=cls.PUBLIC_INSTANCES_TIMEOUT_SECONDS,
                )
                if response.status_code != 200:
                    logger.warning(
                        "[SearXNG] Failed to pull public instance list: HTTP %s",
                        response.status_code,
                    )
                else:
                    urls = cls._extract_public_instances(response.json())
                    if urls:
                        cls._public_instances_cache = (now, list(urls))
                        cls._public_instances_stale_retry_after = 0.0
                        logger.info("[SearXNG] Public instance pool refreshed，common %s candidate instances", len(urls))
                        return list(urls)
                    logger.warning("[SearXNG] searx.space No available public instances returned，Keep existing cache")
            except Exception as exc:
                logger.warning("[SearXNG] Failed to pull public instance list: %s", exc)

            if stale_urls:
                cls._public_instances_stale_retry_after = (
                    now + cls.PUBLIC_INSTANCES_STALE_REFRESH_BACKOFF_SECONDS
                )
                logger.warning(
                    "[SearXNG] No more refreshing within，Continue to use expired cache，common %s candidate instances；"
                    "%.0fs No more refreshing within",
                    len(stale_urls),
                    cls.PUBLIC_INSTANCES_STALE_REFRESH_BACKOFF_SECONDS,
                )
                return stale_urls
            cls._public_instances_stale_retry_after = (
                now + cls.PUBLIC_INSTANCES_STALE_REFRESH_BACKOFF_SECONDS
            )
            logger.warning(
                "[SearXNG] Cold start refresh of public instance fails，%.0fs No more refreshing within",
                cls.PUBLIC_INSTANCES_STALE_REFRESH_BACKOFF_SECONDS,
            )
            return []

    def _rotate_candidates(self, pool: List[str], *, max_attempts: int) -> List[str]:
        if not pool or max_attempts <= 0:
            return []
        with self._cursor_lock:
            start = self._cursor % len(pool)
            self._cursor = (self._cursor + 1) % len(pool)
        ordered = pool[start:] + pool[:start]
        return ordered[:max_attempts]

    def _do_search(  # type: ignore[override]
        self,
        query: str,
        base_url: str,
        max_results: int,
        days: int = 7,
        *,
        timeout: int,
        retry_enabled: bool,
    ) -> SearchResponse:
        """Execute one SearXNG search against a specific instance."""
        try:
            base = base_url.rstrip("/")
            search_url = base if base.endswith("/search") else base + "/search"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            params = {
                "q": query,
                "format": "json",
                "time_range": self._time_range(days),
                "pageno": 1,
            }

            request_get = _get_with_retry if retry_enabled else requests.get
            response = request_get(search_url, headers=headers, params=params, timeout=timeout)

            if response.status_code != 200:
                error_msg = self._parse_http_error(response)
                if response.status_code == 403:
                    error_msg = (
                        f"{error_msg}；SearXNG Instance may not be enabled JSON output（Check, please settings.yml），"
                        "or instance/The agent denied this access"
                    )
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg,
                )

            try:
                data = response.json()
            except Exception:
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message="responseJSONParsing failed",
                )

            if not isinstance(data, dict):
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message="Invalid response format",
                )

            raw = data.get("results", [])
            if not isinstance(raw, list):
                raw = []

            results = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                url_val = item.get("url")
                if not url_val:
                    continue
                raw_published_date = item.get("publishedDate")

                snippet = (item.get("content") or item.get("description") or "")[:500]
                published_date = None
                if raw_published_date:
                    try:
                        dt = datetime.fromisoformat(raw_published_date.replace("Z", "+00:00"))
                        published_date = dt.strftime("%Y-%m-%d")
                    except (ValueError, AttributeError):
                        published_date = raw_published_date

                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        snippet=snippet,
                        url=url_val,
                        source=self._extract_domain(url_val),
                        published_date=published_date,
                    )
                )
                if len(results) >= max_results:
                    break

            return SearchResponse(query=query, results=results, provider=self.name, success=True)

        except requests.exceptions.Timeout:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="Request timeout",
            )
        except requests.exceptions.RequestException as e:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=f"Network request failed: {e}",
            )
        except Exception as e:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=f"unknown error: {e}",
            )

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL as source label."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain or "unknown source"
        except Exception:
            return "unknown source"

    def search(self, query: str, max_results: int = 5, days: int = 7) -> SearchResponse:
        """Execute SearXNG search with instance rotation and per-request failover."""
        start_time = time.time()
        if self._base_urls:
            candidates = self._rotate_candidates(
                self._base_urls,
                max_attempts=len(self._base_urls),
            )
            retry_enabled = True
            timeout = self.SELF_HOSTED_TIMEOUT_SECONDS
            empty_error = "SearXNG No available instances configured"
        elif self._use_public_instances:
            public_instances = self._get_public_instances()
            candidates = self._rotate_candidates(
                public_instances,
                max_attempts=min(len(public_instances), self.PUBLIC_INSTANCES_MAX_ATTEMPTS),
            )
            retry_enabled = False
            timeout = self.PUBLIC_INSTANCES_TIMEOUT_SECONDS
            empty_error = "No available public available SearXNG Example"
        else:
            candidates = []
            retry_enabled = False
            timeout = self.PUBLIC_INSTANCES_TIMEOUT_SECONDS
            empty_error = "SearXNG No available instances configured"

        if not candidates:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=empty_error,
                search_time=time.time() - start_time,
            )

        errors: List[str] = []
        for base_url in candidates:
            response = self._do_search(
                query,
                base_url,
                max_results,
                days=days,
                timeout=timeout,
                retry_enabled=retry_enabled,
            )
            response.search_time = time.time() - start_time
            if response.success:
                logger.info(
                    "[%s] search '%s' success，Example=%s，return %s results，time consuming %.2fs",
                    self.name,
                    query,
                    base_url,
                    len(response.results),
                    response.search_time,
                )
                return response

            errors.append(f"{base_url}: {response.error_message or 'unknown error'}")
            logger.warning("[%s] Example %s Search failed: %s", self.name, base_url, response.error_message)

        elapsed = time.time() - start_time
        return SearchResponse(
            query=query,
            results=[],
            provider=self.name,
            success=False,
            error_message="；".join(errors[:3]) if errors else empty_error,
            search_time=elapsed,
        )


class SearchService:
    """
    Search service
    
    Function：
    1. Manage multiple search engines
    2. Automatic failover
    3. Result aggregation and formatting
    4. Enhanced search when data source fails（share price、Trend, etc.）
    5. Hong Kong stocks/U.S. stocks automatically use English search keywords
    """
    
    # Enhanced search keyword template（Ashare Chinese）
    ENHANCED_SEARCH_KEYWORDS = [
        "{name} stock today share price",
        "{name} {code} up to date Quotes Trend",
        "{name} stock analyze Trend chart",
        "{name} KWire technical analysis",
        "{name} {code} ups and downs Volume",
    ]

    # Enhanced search keyword template（Hong Kong stocks/US stocks English）
    ENHANCED_SEARCH_KEYWORDS_EN = [
        "{name} stock price today",
        "{name} {code} latest quote trend",
        "{name} stock analysis chart",
        "{name} technical analysis",
        "{name} {code} performance volume",
    ]
    NEWS_OVERSAMPLE_FACTOR = 2
    NEWS_OVERSAMPLE_MAX = 10
    FUTURE_TOLERANCE_DAYS = 1
    ANALYTICAL_INTEL_LOOKBACK_DAYS = 180
    ANALYTICAL_INTEL_DIMENSIONS = {"market_analysis", "earnings"}
    _CHINESE_TEXT_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
    _US_STOCK_RE = re.compile(r"^[A-Za-z]{1,5}(\.[A-Za-z])?$")
    _DIRECT_NEWS_CATEGORY = "direct_company_news"
    _SECTOR_NEWS_CATEGORY = "sector_related_news"
    _MACRO_NEWS_CATEGORY = "macro_market_news"
    _NEWS_CATEGORY_PRIORITY = {
        _DIRECT_NEWS_CATEGORY: 0,
        _SECTOR_NEWS_CATEGORY: 1,
        _MACRO_NEWS_CATEGORY: 2,
    }
    _AMBIGUOUS_EN_COMPANY_NAMES = {"apple", "meta", "square", "target", "gap"}
    _AMBIGUOUS_EN_CONFIRMING_EVENT_TERMS = (
        "earnings", "revenue", "profit", "guidance", "filing", "buyback",
        "dividend", "lawsuit", "merger", "acquisition",
    )
    _COMPANY_EVENT_TERMS = (
        "announcement", "Disclosure", "release", "acquisition", "repurchase", "Reduce holdings", "Overweight", "litigation", "punishment",
        "performance", "financial report", "Revenue", "net profit", "dividend", "Board of Directors", "shareholders meeting", "Order",
        "cooperate", "Winning the bid", "earnings", "revenue", "profit", "guidance", "filing",
        "sec", "shares", "stock", "buyback", "dividend", "lawsuit", "merger",
        "acquisition", "results", "quarterly", "annual", "announces", "launches",
    )
    _SECTOR_NEWS_TERMS = (
        "industry", "plate", "Industrial chain", "faucet", "concept stocks", "track", "sector", "industry",
        "peers", "competitors", "supply chain", "market share",
    )
    _MACRO_NEWS_TERMS = (
        "Market", "market", "index", "Macro", "central bank", "interest rate", "inflation", "ashare", "Hong Kong stocks",
        "US stocks", "Nasdaq", "Shanghai Stock Exchange", "market", "index", "fed", "inflation",
        "interest rate", "nasdaq", "s&p 500", "dow jones",
    )
    _OFFICIAL_SOURCE_TERMS = (
        "cninfo", "sse.com", "szse.cn", "hkexnews", "sec.gov", "nasdaq.com",
        "nyse.com", "Shanghai Stock Exchange", "Shenzhen Stock Exchange", "Hong Kong Stock Exchange", "stock exchange",
    )
    _OFFICIAL_SOURCE_HOSTS = (
        "cninfo.com.cn", "sse.com", "sse.com.cn", "szse.cn", "hkexnews.hk",
        "sec.gov", "nasdaq.com", "nyse.com",
    )
    _OFFICIAL_SOURCE_LABELS = (
        "cninfo", "hkexnews", "Juchao Information", "Juchao Information Network",
        "Shanghai Stock Exchange", "Shenzhen Stock Exchange", "Hong Kong Stock Exchange", "stock exchange",
        "Shanghai Stock Exchange", "Shenzhen Stock Exchange", "Hong Kong Exchange", "Hong Kong Stock Exchange",
    )
    _LOW_QUALITY_DOWNLOAD_ACTION_TERMS = (
        "download", "Install", "Download and install", "Download and install to mobile phone", "Download link",
        "free download", "Client download", "Application download", "officialappdownload",
        "Installation package", "apk", "download", "install", "installer",
    )
    _LOW_QUALITY_DOWNLOAD_INTENT_TERMS = (
        "Installation package", "Client download", "Application download", "Download and install", "Download and install to mobile phone",
        "Download link", "free download", "Old version download", "Fast version download", "officialappdownload",
    )
    _LOW_QUALITY_APP_CONTEXT_TERMS = (
        "Good reviews", "Version", "Version", "size", "Applicable age", "Developer", "application",
        "ratings", "reviews", "stars", "version", "developer", "package",
    )
    _LOW_QUALITY_APP_METADATA_TERMS = (
        "Version", "size", "Applicable age", "Developer", "application", "app store",
        "Android version", "Apple version", "Official version", "Latest version", "version", "developer",
        "package", "mobile app",
    )
    _LOW_QUALITY_APP_PAGE_DETAIL_TERMS = (
        "client", "Android version", "Apple version", "Official version", "Latest version", "app store",
        "Download and install to mobile phone", "One click download", "Old version download", "Fast version download",
    )
    _LOW_QUALITY_FILE_SIZE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:kb|mb|gb)\b", re.IGNORECASE)
    _LOW_QUALITY_RATING_RE = re.compile(
        r"(?:\d{1,3}\s*%\s*Good reviews|Positive rating|User ratings|"
        r"(?:User)?Rating\s*[:：]?\s*(?:10|[0-9])(?:\.\d{1,2})?|"
        r"\b\d(?:\.\d)?\s*(?:stars?|ratings?|reviews?)\b)",
        re.IGNORECASE,
    )
    _LOW_QUALITY_URL_RE = re.compile(
        r"(?:^|[/_.=-])(?:download|downloads|apk|ipa|exe|dmg|installer|"
        r"software|soft|game|games|app|apps|package)(?:$|[/_.?&=-])",
        re.IGNORECASE,
    )
    _BUSINESS_APP_METRIC_RE = re.compile(
        r"(?:(?:Downloads|Installation volume|Installed capacity|Application download|Application installation|appDownload|appInstallation).{0,12}"
        r"(?:growth|Year-on-year|month-on-month|rise|increase|promote|breakthrough|reach|reach|exceed|super|cumulative|close|keep|new high|fall|decline|reduce|fall back|slow down|flat|Under pressure|downturn)|"
        r"(?:growth|Year-on-year|month-on-month|rise|increase|promote|breakthrough|reach|reach|exceed|super|cumulative|close|keep|new high|fall|decline|reduce|fall back|slow down|flat|Under pressure|downturn)"
        r".{0,12}(?:Downloads|Installation volume|Installed capacity|Application download|Application installation|appDownload|appInstallation)|"
        r"\b(?:downloads?|installs?)\b.{0,16}"
        r"\b(?:grew|growth|rose|increase|increased|surged|reached|reach|reaches|"
        r"hit|hits|topped|totaled|totalled|exceeded|exceeds|surpassed|surpasses|"
        r"fell|fall|declined|decline|decreased|dropped|drop|slowed|flat|weakened)\b|"
        r"\b(?:grew|growth|rose|increase|increased|surged|reached|reach|reaches|"
        r"hit|hits|topped|totaled|totalled|exceeded|exceeds|surpassed|surpasses|"
        r"fell|fall|declined|decline|decreased|dropped|drop|slowed|flat|weakened)\b"
        r".{0,16}\b(?:downloads?|installs?)\b)",
        re.IGNORECASE,
    )
    _ADULT_SERVICE_SPAM_STRONG_TERMS = (
        "Door-to-door special service", "Same city appointment", "Hook up", "compensated dating", "Lou Feng", "Peripheral girl",
        "Peripheral services", "Night package", "Great health care", "Wan style", "push oil",
        "adult services", "adult service", "escort service",
        "sex service", "call girl",
    )
    _ADULT_SERVICE_SPAM_AMBIGUOUS_TERMS = (
        "full service", "pornography",
    )
    _ADULT_SERVICE_SPAM_CONTEXT_TERMS = (
        "Miss", "door-to-door", "reserve", "massage", "massage", "health care", "foot bath", "sauna",
        "clubhouse", "technician", "full set", "combo", "vip",
    )
    _ADULT_SERVICE_SPAM_CONTACT_RE = re.compile(
        r"(?:^|[^a-z0-9])(?:yue|vx|wx|qq|wechat|weixin|WeChat ID?|Micro[news]|"
        r"phone|mobile phone|Contact number|tel|phone)"
        r"[-_:\s：]*[a-z0-9][a-z0-9_-]{2,}(?:[^a-z0-9]|$)",
        re.IGNORECASE,
    )
    _ADULT_SERVICE_SPAM_CONTACT_CONTEXT_TERMS = (
        "Miss", "door-to-door", "massage", "reserve",
        "full set", "Night package", "Great health care", "push oil",
        "Hook up", "compensated dating", "aldult", "pornography",
    )
    _ADULT_SERVICE_REMEDIATION_TERMS = (
        "governance", "rectify", "Removed from shelves", "punishment", "supervision", "blow", "clean up",
        "ban", "Rectify", "Content security", "vulgar content", "Platform risk",
    )
    _ADULT_SERVICE_SOLICITATION_TERMS = (
        "door-to-door", "massage", "reserve", "combo", "Night package", "Great health care",
        "push oil", "connect", "consult", "Add WeChat", "addqq", "vip",
    )

    def __init__(
        self,
        bocha_keys: Optional[List[str]] = None,
        tavily_keys: Optional[List[str]] = None,
        anspire_keys: Optional[List[str]] = None,
        brave_keys: Optional[List[str]] = None,
        serpapi_keys: Optional[List[str]] = None,
        minimax_keys: Optional[List[str]] = None,
        searxng_base_urls: Optional[List[str]] = None,
        searxng_public_instances_enabled: bool = True,
        news_max_age_days: int = 3,
        news_strategy_profile: str = "short",
    ):
        """
        Initialize search service

        Args:
            bocha_keys: Bocha search API Key list
            tavily_keys: Tavily API Key list
            anspire_keys: Anspire Search API Key list
            brave_keys: Brave Search API Key list
            serpapi_keys: SerpAPI Key list
            minimax_keys: MiniMax API Key list
            searxng_base_urls: SearXNG Instance address list（Self-built without quotas）
            searxng_public_instances_enabled: When a self-built instance is not configured，Whether to automatically use public SearXNG Example
            news_max_age_days: News maximum timeliness（sky）
            news_strategy_profile: News window strategy position（ultra_short/short/medium/long）
        """
        self._providers: List[BaseSearchProvider] = []
        self.news_max_age_days = max(1, news_max_age_days)
        raw_profile = (news_strategy_profile or "short").strip().lower()
        self.news_strategy_profile = normalize_news_strategy_profile(news_strategy_profile)
        if raw_profile != self.news_strategy_profile:
            logger.warning(
                "NEWS_STRATEGY_PROFILE '%s' invalid，Reverted to 'short'",
                news_strategy_profile,
            )
        self.news_window_days = resolve_news_window_days(
            news_max_age_days=self.news_max_age_days,
            news_strategy_profile=self.news_strategy_profile,
        )
        self.news_profile_days = NEWS_STRATEGY_WINDOWS.get(
            self.news_strategy_profile,
            NEWS_STRATEGY_WINDOWS["short"],
        )

        # Initialize search engine（Sort by priority）
        # 1. Bocha priority（More free credits，AIsummary）
        if bocha_keys:
            self._providers.append(BochaSearchProvider(bocha_keys))
            logger.info(f"configured Bocha search，common {len(bocha_keys)} indivual API Key")

        # 2. Tavily（More free credits，per month 1000 Second-rate）
        if tavily_keys:
            self._providers.append(TavilySearchProvider(tavily_keys))
            logger.info(f"configured Tavily search，common {len(tavily_keys)} indivual API Key")

        # 3. Brave Search（Privacy first，Global coverage）
        if brave_keys:
            self._providers.append(BraveSearchProvider(brave_keys))
            logger.info(f"configured Brave search，common {len(brave_keys)} indivual API Key")

        # 4. SerpAPI as an alternative（per month 100 Second-rate）
        if serpapi_keys:
            self._providers.append(SerpAPISearchProvider(serpapi_keys))
            logger.info(f"configured SerpAPI search，common {len(serpapi_keys)} indivual API Key")

        # 5. MiniMax（Coding Plan Web Search，Structured results）
        if minimax_keys:
            self._providers.append(MiniMaxSearchProvider(minimax_keys))
            logger.info(f"configured MiniMax search，common {len(minimax_keys)} indivual API Key")

        # 6. SearXNG（Self-built instances are preferred；Public instances can be automatically discovered when not configured）
        searxng_provider = SearXNGSearchProvider(
            searxng_base_urls,
            use_public_instances=bool(searxng_public_instances_enabled and not searxng_base_urls),
        )
        if searxng_provider.is_available:
            self._providers.append(searxng_provider)
            if searxng_base_urls:
                logger.info("configured SearXNG search，common %s self-built instances", len(searxng_base_urls))
            else:
                logger.info("Enabled SearXNG Public instance auto-discovery mode")

        # 7. Anspire Search（Real-time intelligent search optimization）
        if anspire_keys:
            self._providers.insert(0, AnspireSearchProvider(anspire_keys))
            logger.info(f"configured Anspire Search search，common {len(anspire_keys)} indivual API Key")
            
        if not self._providers:
            logger.warning("No search capabilities configured，News search function will not be available")

        # In-memory search result cache: {cache_key: (timestamp, SearchResponse)}
        self._cache: Dict[str, Tuple[float, 'SearchResponse']] = {}
        self._cache_lock = threading.RLock()
        self._cache_inflight: Dict[str, threading.Event] = {}
        # Default cache TTL in seconds (10 minutes)
        self._cache_ttl: int = 600
        logger.info(
            "News timeliness policy is enabled: profile=%s, profile_days=%s, NEWS_MAX_AGE_DAYS=%s, effective_window=%s",
            self.news_strategy_profile,
            self.news_profile_days,
            self.news_max_age_days,
            self.news_window_days,
        )
    
    @staticmethod
    def _is_foreign_stock(stock_code: str) -> bool:
        """Determine whether it is a Hong Kong stock or a US stock"""
        code = stock_code.strip()
        # US stocks：1-5capital letters，like（like BRK.B）
        if SearchService._US_STOCK_RE.match(code):
            return True
        # Hong Kong stocks：bring hk prefix or 5pure digits
        lower = code.lower()
        if lower.startswith('hk'):
            return True
        if code.isdigit() and len(code) == 5:
            return True
        return False

    @classmethod
    def _contains_chinese_text(cls, value: Optional[str]) -> bool:
        """Return True when the input contains CJK characters."""
        return bool(value and cls._CHINESE_TEXT_RE.search(value))

    @classmethod
    def _is_us_stock(cls, stock_code: str) -> bool:
        """US stock index code/US stock index code。"""
        code = (stock_code or "").strip().upper()
        return bool(cls._US_STOCK_RE.match(code) or is_us_index_code(code))

    @classmethod
    def _should_prefer_chinese_news(
        cls,
        stock_code: str,
        stock_name: str,
        focus_keywords: Optional[List[str]] = None,
    ) -> bool:
        """A Stock or Chinese name/Prioritize Chinese information in keyword scenarios。

        Only returns True when there is a positive Chinese signal:
        Chinese characters in keywords/stock_name, or a 6-digit A-stock code.
        Avoids false positives for non-foreign but English contexts like
        ``stock_code="market", stock_name="US market"``.
        """
        if any(cls._contains_chinese_text(keyword) for keyword in (focus_keywords or [])):
            return True
        if cls._contains_chinese_text(stock_name):
            return True
        # Positive A-stock identification: 6-digit numeric codes (e.g. 600519)
        code = (stock_code or "").strip()
        return code.isdigit() and len(code) == 6

    @classmethod
    def _is_chinese_news_result(cls, item: SearchResult) -> bool:
        """Heuristic check for Chinese-language news items."""
        return cls._contains_chinese_text(" ".join(filter(None, [item.title, item.snippet, item.source])))

    @classmethod
    def _prioritize_news_language(
        cls,
        response: SearchResponse,
        *,
        prefer_chinese: bool,
    ) -> Tuple[SearchResponse, int]:
        """Reorder results by preferred language and return preferred-result count."""
        if not prefer_chinese or not response.success or not response.results:
            return response, 0

        chinese_results: List[SearchResult] = []
        other_results: List[SearchResult] = []
        for item in response.results:
            if cls._is_chinese_news_result(item):
                chinese_results.append(item)
            else:
                other_results.append(item)

        return (
            SearchResponse(
                query=response.query,
                results=chinese_results + other_results,
                provider=response.provider,
                success=response.success,
                error_message=response.error_message,
                search_time=response.search_time,
            ),
            len(chinese_results),
        )

    @classmethod
    def _is_better_preferred_news_response(
        cls,
        candidate: SearchResponse,
        *,
        candidate_preferred_count: int,
        best_response: Optional[SearchResponse],
        best_preferred_count: int,
    ) -> bool:
        """Prefer responses with more Chinese items, then more total items."""
        if best_response is None:
            return True
        if candidate_preferred_count != best_preferred_count:
            return candidate_preferred_count > best_preferred_count
        return len(candidate.results) > len(best_response.results)

    @classmethod
    def _brave_search_locale(
        cls,
        stock_code: str,
        *,
        prefer_chinese: bool,
    ) -> Dict[str, str]:
        """Resolve Brave locale hints without forcing US bias onto non-US symbols."""
        if prefer_chinese:
            return {"search_lang": "zh-hans", "country": "CN"}
        if cls._is_us_stock(stock_code):
            return {"search_lang": "en", "country": "US"}
        return {}

    # A-share ETF code prefixes (Shanghai 51/52/56/58, Shenzhen 15/16/18)
    _A_ETF_PREFIXES = ('51', '52', '56', '58', '15', '16', '18')
    _ETF_NAME_KEYWORDS = ('ETF', 'FUND', 'TRUST', 'INDEX', 'TRACKER', 'UNIT')  # US/HK ETF name hints

    @staticmethod
    def is_index_or_etf(stock_code: str, stock_name: str) -> bool:
        """
        Judge if symbol is index-tracking ETF or market index.
        For such symbols, analysis focuses on index movement only, not issuer company risks.
        """
        code = (stock_code or '').strip().split('.')[0]
        if not code:
            return False
        # A-share ETF
        if code.isdigit() and len(code) == 6 and code.startswith(SearchService._A_ETF_PREFIXES):
            return True
        # US index (SPX, DJI, IXIC etc.)
        if is_us_index_code(code):
            return True
        # US/HK ETF: foreign symbol + name contains fund-like keywords
        if SearchService._is_foreign_stock(code):
            name_upper = (stock_name or '').upper()
            return any(kw in name_upper for kw in SearchService._ETF_NAME_KEYWORDS)
        return False

    @property
    def is_available(self) -> bool:
        """Check if a search engine is available"""
        return any(p.is_available for p in self._providers)

    def _cache_key(self, query: str, max_results: int, days: int) -> str:
        """Build a cache key from query parameters."""
        return f"{query}|{max_results}|{days}"

    def _get_cached_locked(self, key: str) -> Optional['SearchResponse']:
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, response = entry
        if time.time() - ts > self._cache_ttl:
            self._cache.pop(key, None)
            return None
        logger.debug(f"Search cache hit: {key[:60]}...")
        return response

    def _get_cached(self, key: str) -> Optional['SearchResponse']:
        """Return cached SearchResponse if still valid, else None."""
        with self._cache_lock:
            return self._get_cached_locked(key)

    def _get_cached_or_reserve(
        self,
        key: str,
    ) -> Tuple[Optional['SearchResponse'], bool, Optional[threading.Event]]:
        with self._cache_lock:
            cached = self._get_cached_locked(key)
            if cached is not None:
                return cached, False, None

            event = self._cache_inflight.get(key)
            if event is None:
                event = threading.Event()
                self._cache_inflight[key] = event
                return None, True, event
            return None, False, event

    def _release_cache_fill(self, key: str, event: threading.Event) -> None:
        with self._cache_lock:
            current = self._cache_inflight.get(key)
            if current is event:
                self._cache_inflight.pop(key, None)
                event.set()

    def _wait_for_cached(self, key: str, event: threading.Event) -> Optional['SearchResponse']:
        event.wait(timeout=max(1.0, min(float(self._cache_ttl), 30.0)))
        return self._get_cached(key)

    def _put_cache(self, key: str, response: 'SearchResponse') -> None:
        """Store a successful SearchResponse in cache."""
        with self._cache_lock:
            # Hard cap: evict oldest entries when cache exceeds limit
            _MAX_CACHE_SIZE = 500
            if len(self._cache) >= _MAX_CACHE_SIZE:
                now = time.time()
                # First pass: remove expired entries
                expired = [k for k, (ts, _) in self._cache.items() if now - ts > self._cache_ttl]
                for k in expired:
                    self._cache.pop(k, None)
                # Second pass: if still over limit, evict oldest entries (FIFO)
                if len(self._cache) >= _MAX_CACHE_SIZE:
                    excess = len(self._cache) - _MAX_CACHE_SIZE + 1
                    oldest = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:excess]
                    for k in oldest:
                        self._cache.pop(k, None)
            self._cache[key] = (time.time(), response)

    def _effective_news_window_days(self) -> int:
        """Resolve effective news window from strategy profile and global max-age."""
        return resolve_news_window_days(
            news_max_age_days=self.news_max_age_days,
            news_strategy_profile=self.news_strategy_profile,
        )

    @classmethod
    def _provider_request_size(cls, max_results: int) -> int:
        """Apply light overfetch before time filtering to avoid sparse outputs."""
        target = max(1, int(max_results))
        return max(target, min(target * cls.NEWS_OVERSAMPLE_FACTOR, cls.NEWS_OVERSAMPLE_MAX))

    @staticmethod
    def _append_unique(values: List[str], value: Optional[str]) -> None:
        cleaned = (value or "").strip()
        if cleaned and cleaned not in values:
            values.append(cleaned)

    @classmethod
    def _stock_code_identity_terms(cls, stock_code: str) -> List[str]:
        """Return code/ticker variants that should count as strong identity hits."""
        raw = (stock_code or "").strip()
        if not raw:
            return []

        terms: List[str] = []
        upper = raw.upper()
        code_for_variants = upper
        if "." in upper:
            base, suffix = upper.rsplit(".", 1)
            if suffix == "HK" and base.isdigit() and 1 <= len(base) <= 5:
                code_for_variants = f"HK{base.zfill(5)}"
            elif suffix in {"SH", "SZ", "SS", "BJ"} and base.isdigit() and len(base) == 6:
                code_for_variants = base
            elif suffix == "US" and re.fullmatch(r"[A-Z]{1,5}", base):
                code_for_variants = base

        is_us_ticker = bool(cls._US_STOCK_RE.match(code_for_variants))
        if not is_us_ticker:
            cls._append_unique(terms, raw)
            cls._append_unique(terms, upper)
            if code_for_variants != upper:
                cls._append_unique(terms, code_for_variants)

        lower = code_for_variants.lower()
        hk_digits = ""
        if lower.startswith("hk"):
            hk_digits = re.sub(r"\D", "", code_for_variants)
        elif code_for_variants.isdigit() and len(code_for_variants) == 5:
            hk_digits = code_for_variants

        if hk_digits:
            padded = hk_digits.zfill(5)
            short = str(int(hk_digits)) if hk_digits.isdigit() else hk_digits.lstrip("0")
            cls._append_unique(terms, padded)
            cls._append_unique(terms, f"HK{padded}")
            cls._append_unique(terms, f"{padded}.HK")
            cls._append_unique(terms, f"{short}.HK")
            cls._append_unique(terms, f"HKEX:{short}")
            return terms

        if code_for_variants.isdigit() and len(code_for_variants) == 6:
            suffix = ".SH" if code_for_variants.startswith(("5", "6", "9")) else ".SZ"
            cls._append_unique(terms, f"{code_for_variants}{suffix}")
            return terms

        if cls._US_STOCK_RE.match(code_for_variants):
            cls._append_unique(terms, f"${code_for_variants}")
            cls._append_unique(terms, f"NASDAQ:{code_for_variants}")
            cls._append_unique(terms, f"NYSE:{code_for_variants}")
            if len(code_for_variants) > 1:
                cls._append_unique(terms, code_for_variants)
            return terms

        return terms

    @classmethod
    def _company_identity_terms(cls, stock_name: str) -> List[str]:
        """Return conservative company-name variants for relevance matching."""
        raw = (stock_name or "").strip()
        if not raw:
            return []

        terms: List[str] = []
        cls._append_unique(terms, raw)

        without_market_suffix = re.sub(r"[-－（(].*$", "", raw).strip()
        cls._append_unique(terms, without_market_suffix)

        if cls._contains_chinese_text(raw):
            cleaned = re.sub(
                r"(Co., Ltd.|limited liability company|Ltd.|holding group|holding|Group|shares|company)$",
                "",
                without_market_suffix,
            ).strip()
            if len(cleaned) >= 4:
                cls._append_unique(terms, cleaned)
        else:
            cleaned = re.sub(
                r"\b(incorporated|inc|corporation|corp|company|co|plc|ltd|limited|holdings?)\.?$",
                "",
                without_market_suffix,
                flags=re.IGNORECASE,
            ).strip()
            if len(cleaned) >= 3:
                cls._append_unique(terms, cleaned)

        return terms

    @classmethod
    def _contains_identity_term(cls, text: str, term: str) -> bool:
        if not text or not term:
            return False

        if cls._contains_chinese_text(term):
            start = 0
            while True:
                index = text.find(term, start)
                if index < 0:
                    return False
                next_char = text[index + len(term):index + len(term) + 1]
                if next_char not in {"town", "village", "County"}:
                    return True
                start = index + len(term)

        lower_text = text.lower()
        lower_term = term.lower()
        if lower_term.startswith("$"):
            return lower_term in lower_text

        pattern = r"(?<![A-Za-z0-9])" + re.escape(lower_term) + r"(?![A-Za-z0-9])"
        return bool(re.search(pattern, lower_text))

    @classmethod
    def _contains_stock_code_identity_term(cls, text: str, term: str) -> bool:
        if not text or not term:
            return False

        if cls._US_STOCK_RE.match(term) and term.upper() == term and not term.startswith("$"):
            ticker_pattern = f"(?:{re.escape(term)}|{re.escape(term.lower())})"
            pattern = (
                r"(?<![A-Za-z0-9$:.])"
                + ticker_pattern
                + r"(?=$|[^A-Za-z0-9.]|\.(?:US|us|O|o|N|n|NYSE|nyse|NASDAQ|nasdaq|AMEX|amex)\b)"
            )
            return bool(re.search(pattern, text))

        return cls._contains_identity_term(text, term)

    @classmethod
    def _contains_any_news_term(cls, text: str, terms: Tuple[str, ...]) -> bool:
        lower = (text or "").lower()
        return any(term.lower() in lower for term in terms)

    @classmethod
    def _contains_any_low_quality_news_term(cls, text: str, terms: Tuple[str, ...]) -> bool:
        lower = (text or "").lower()
        if not lower:
            return False

        for term in terms:
            normalized_term = term.lower()
            if not normalized_term:
                continue
            if normalized_term.isascii() and re.search(r"[a-z0-9]", normalized_term):
                pattern = r"(?<![A-Za-z0-9])" + re.escape(normalized_term) + r"(?![A-Za-z0-9])"
                if re.search(pattern, lower):
                    return True
                continue
            if normalized_term in lower:
                return True
        return False

    @staticmethod
    def _candidate_hostname(value: Any) -> str:
        raw = str(value or "").strip().lower()
        if not raw or re.search(r"\s", raw):
            return ""

        parse_value = (
            raw
            if re.match(r"^[a-z][a-z0-9+.-]*://", raw) or raw.startswith("//")
            else f"//{raw}"
        )
        return (urlparse(parse_value).hostname or "").rstrip(".")

    @staticmethod
    def _source_resembles_hostname(value: Any) -> bool:
        raw = str(value or "").strip().lower()
        if not raw or re.search(r"\s", raw):
            return False
        if re.match(r"^[a-z][a-z0-9+.-]*://", raw) or raw.startswith("//"):
            return True
        return bool(re.search(r"\.[a-z0-9-]{2,}(?::\d+)?/?$", raw))

    @classmethod
    def _is_trusted_official_news_source(cls, item: SearchResult) -> bool:
        """Only trust official exemptions from trusted hosts; fallback to labels only when URL host is absent."""
        url_host = cls._candidate_hostname(item.url)
        source_label = str(item.source or "").strip().lower()
        source_host = (
            cls._candidate_hostname(item.source)
            if cls._source_resembles_hostname(item.source)
            else ""
        )

        if url_host:
            # have URL time URL The host shall prevail，Pretended official release source label/host Pretended official release。
            return any(
                url_host == official_host or url_host.endswith(f".{official_host}")
                for official_host in cls._OFFICIAL_SOURCE_HOSTS
            )

        if source_host:
            return any(
                source_host == official_host or source_host.endswith(f".{official_host}")
                for official_host in cls._OFFICIAL_SOURCE_HOSTS
            )

        return source_label in cls._OFFICIAL_SOURCE_LABELS

    @classmethod
    def _has_low_quality_news_page_signal(cls, item: SearchResult) -> bool:
        """Detect app/download/listing pages without relying on a domain blocklist."""
        content_text = " ".join(filter(None, [item.title, item.snippet])).lower()
        parsed_url = urlparse(item.url or "")
        url_surface = unquote(
            " ".join(filter(None, [parsed_url.netloc, parsed_url.path, parsed_url.query]))
        ).lower()

        has_app_context = cls._contains_any_low_quality_news_term(
            content_text,
            cls._LOW_QUALITY_APP_CONTEXT_TERMS,
        )
        has_app_metadata = cls._contains_any_low_quality_news_term(
            content_text,
            cls._LOW_QUALITY_APP_METADATA_TERMS,
        )
        has_download_action = cls._contains_any_low_quality_news_term(
            content_text,
            cls._LOW_QUALITY_DOWNLOAD_ACTION_TERMS,
        )
        has_download_intent = cls._contains_any_low_quality_news_term(
            content_text,
            cls._LOW_QUALITY_DOWNLOAD_INTENT_TERMS,
        )
        has_app_page_detail = cls._contains_any_low_quality_news_term(
            content_text,
            cls._LOW_QUALITY_APP_PAGE_DETAIL_TERMS,
        )
        has_file_size = bool(cls._LOW_QUALITY_FILE_SIZE_RE.search(content_text))
        has_rating = bool(cls._LOW_QUALITY_RATING_RE.search(content_text))
        has_url_signal = bool(cls._LOW_QUALITY_URL_RE.search(url_surface))
        has_business_app_metric = bool(cls._BUSINESS_APP_METRIC_RE.search(content_text))
        has_app_listing_detail = (
            has_file_size
            or has_rating
            or cls._contains_any_low_quality_news_term(
                content_text,
                (
                    "Version", "Applicable age", "Developer", "app store", "Android version",
                    "Apple version", "Official version", "Latest version", "version", "developer",
                    "package",
                ),
            )
        )
        has_strong_app_page_evidence = (
            has_app_listing_detail
            and (
                has_url_signal
                or has_download_intent
                or (has_download_action and has_app_metadata)
            )
        )
        has_business_app_metric_only = (
            has_business_app_metric
            and not has_strong_app_page_evidence
        )
        has_app_listing_context = (
            not has_business_app_metric_only
            and has_app_context
            and has_app_metadata
            and (has_download_action or has_download_intent)
            and (has_file_size or has_rating)
        )
        has_content_download_page = (
            not has_business_app_metric_only
            and (
                (has_download_intent and (has_app_page_detail or has_file_size or has_rating))
                or (has_download_action and (has_app_metadata or has_file_size))
            )
        )
        has_url_backed_download_page = (
            not has_business_app_metric_only
            and has_url_signal
            and (
                has_file_size
                or has_download_intent
                or (has_download_action and has_app_metadata)
                or (has_app_metadata and has_rating)
            )
        )

        return (
            has_content_download_page
            or has_app_listing_context
            or has_url_backed_download_page
        )

    @classmethod
    def _has_adult_service_spam_news_page_signal(cls, item: SearchResult) -> bool:
        """Detect adult-service spam by content signals instead of domain names."""
        combined_text = " ".join(
            filter(None, [item.title, item.snippet, item.source, item.url])
        ).lower()

        if cls._contains_any_news_term(
            combined_text,
            cls._ADULT_SERVICE_SPAM_STRONG_TERMS,
        ):
            return True
        has_contact_signal = bool(cls._ADULT_SERVICE_SPAM_CONTACT_RE.search(combined_text))
        has_remediation_context = cls._contains_any_news_term(
            combined_text,
            cls._ADULT_SERVICE_REMEDIATION_TERMS,
        )
        if has_remediation_context and not has_contact_signal:
            return False

        if (
            "Periphery" in combined_text
            and cls._contains_any_news_term(
                combined_text,
                ("door-to-door", "Same city", "Hook up", "compensated dating", "Night package", "Great health care", "push oil", "Miss", "technician"),
            )
        ):
            return True

        context_hits = sum(
            1
            for term in cls._ADULT_SERVICE_SPAM_CONTEXT_TERMS
            if term.lower() in combined_text
        )
        has_service_anchor = cls._contains_any_news_term(
            combined_text,
            ("Miss", "Massage", "foot bath", "sauna", "clubhouse", "technician"),
        )
        has_adult_specific_anchor = cls._contains_any_news_term(
            combined_text,
            (
                "Miss", "Hook up", "compensated dating", "Lou Feng", "Periphery", "Night package",
                "Great health care", "Wan style", "push oil", "aldult", "pornography",
            ),
        )
        if has_contact_signal:
            return has_adult_specific_anchor and cls._contains_any_news_term(
                combined_text,
                cls._ADULT_SERVICE_SPAM_CONTACT_CONTEXT_TERMS,
            )
        has_solicitation_signal = cls._contains_any_news_term(
            combined_text,
            cls._ADULT_SERVICE_SOLICITATION_TERMS,
        )
        has_ambiguous_adult_phrase = cls._contains_any_news_term(
            combined_text,
            cls._ADULT_SERVICE_SPAM_AMBIGUOUS_TERMS,
        )
        if has_ambiguous_adult_phrase:
            return has_service_anchor and has_solicitation_signal

        return (
            has_adult_specific_anchor
            and has_service_anchor
            and has_solicitation_signal
            and context_hits >= 3
        )

    @classmethod
    def _score_news_relevance(
        cls,
        item: SearchResult,
        *,
        stock_code: str,
        stock_name: str,
    ) -> SearchResult:
        """Attach conservative, explainable relevance metadata to one news item."""
        title = item.title or ""
        snippet = item.snippet or ""
        url = item.url or ""
        source = item.source or ""
        full_text = " ".join([title, snippet, url, source])

        score = 0
        direct_signal = 0
        reasons: List[str] = []
        has_stock_code_signal = False
        has_unambiguous_company_signal = False
        has_ambiguous_company_signal = False

        def add_reason(reason: str) -> None:
            if reason not in reasons and len(reasons) < 5:
                reasons.append(reason)

        for term in cls._stock_code_identity_terms(stock_code):
            if cls._contains_stock_code_identity_term(title, term):
                score += 55
                direct_signal += 55
                has_stock_code_signal = True
                add_reason(f"Title hits ticker {term}")
                break
        else:
            for term in cls._stock_code_identity_terms(stock_code):
                if cls._contains_stock_code_identity_term(snippet, term):
                    score += 34
                    direct_signal += 34
                    has_stock_code_signal = True
                    add_reason(f"Summary hits ticker {term}")
                    break
            else:
                for term in cls._stock_code_identity_terms(stock_code):
                    if cls._contains_stock_code_identity_term(url, term):
                        score += 18
                        direct_signal += 18
                        has_stock_code_signal = True
                        add_reason(f"Link hits ticker {term}")
                        break

        for term in cls._company_identity_terms(stock_name):
            ambiguous_en = (
                not cls._contains_chinese_text(term)
                and term.lower() in cls._AMBIGUOUS_EN_COMPANY_NAMES
            )
            title_score = 26 if ambiguous_en else 45
            snippet_score = 16 if ambiguous_en else 28
            if cls._contains_identity_term(title, term):
                score += title_score
                direct_signal += title_score
                if ambiguous_en:
                    has_ambiguous_company_signal = True
                else:
                    has_unambiguous_company_signal = True
                add_reason(f"The title hits the company name {term}")
                break
            if cls._contains_identity_term(snippet, term):
                score += snippet_score
                direct_signal += snippet_score
                if ambiguous_en:
                    has_ambiguous_company_signal = True
                else:
                    has_unambiguous_company_signal = True
                add_reason(f"Abstract hits company name {term}")
                break

        has_company_event = cls._contains_any_news_term(full_text, cls._COMPANY_EVENT_TERMS)
        if has_company_event and direct_signal > 0:
            score += 12
            ambiguous_name_only = (
                has_ambiguous_company_signal
                and not has_stock_code_signal
                and not has_unambiguous_company_signal
            )
            has_confirming_event = cls._contains_any_news_term(
                full_text,
                cls._AMBIGUOUS_EN_CONFIRMING_EVENT_TERMS,
            )
            if not ambiguous_name_only or has_confirming_event:
                direct_signal += 12
            add_reason("hit announcement/financial report/Transactions and other corporate event words")

        if cls._is_trusted_official_news_source(item):
            score += 8
            add_reason("Source close to announcement or exchange channel")

        has_sector_signal = cls._contains_any_news_term(full_text, cls._SECTOR_NEWS_TERMS)
        has_macro_signal = cls._contains_any_news_term(full_text, cls._MACRO_NEWS_TERMS)

        if direct_signal >= 38:
            category = cls._DIRECT_NEWS_CATEGORY
        elif has_macro_signal and not direct_signal:
            category = cls._MACRO_NEWS_CATEGORY
            score = max(0, score - 12)
            add_reason("Missed target company identity，classified as macro/market news")
        else:
            category = cls._SECTOR_NEWS_CATEGORY
            if has_sector_signal:
                score += 6
                add_reason("Only hit industry or sector background")
            else:
                add_reason("Missed stock code or full company name，Relegated to background news")

        score = max(0, min(100, score))
        return SearchResult(
            title=item.title,
            snippet=item.snippet,
            url=item.url,
            source=item.source,
            published_date=item.published_date,
            relevance_score=score,
            relevance_category=category,
            relevance_reasons=reasons,
        )

    @classmethod
    def _rank_news_response(
        cls,
        response: SearchResponse,
        *,
        stock_code: str,
        stock_name: str,
        prefer_chinese: bool,
        max_results: int,
        log_scope: str,
    ) -> SearchResponse:
        """Score and sort news so direct company items are not crowded out."""
        if not response.success or not response.results:
            return response

        scored_results = [
            cls._score_news_relevance(item, stock_code=stock_code, stock_name=stock_name)
            for item in response.results
        ]

        indexed_results = list(enumerate(scored_results))

        def sort_key(entry: Tuple[int, SearchResult]) -> Tuple[int, int, int, int]:
            index, result = entry
            category = result.relevance_category or cls._SECTOR_NEWS_CATEGORY
            category_rank = cls._NEWS_CATEGORY_PRIORITY.get(category, 9)
            language_rank = 0 if prefer_chinese and cls._is_chinese_news_result(result) else 1
            if not prefer_chinese:
                language_rank = 0
            score = result.relevance_score or 0
            return (category_rank, language_rank, -score, index)

        ranked_results = [result for _, result in sorted(indexed_results, key=sort_key)]
        limited_results = ranked_results[:max_results]
        category_counts = {
            cls._DIRECT_NEWS_CATEGORY: 0,
            cls._SECTOR_NEWS_CATEGORY: 0,
            cls._MACRO_NEWS_CATEGORY: 0,
        }
        for result in limited_results:
            if result.relevance_category in category_counts:
                category_counts[result.relevance_category] += 1
        if limited_results:
            top = limited_results[0]
            logger.info(
                "[news relevance] %s: direct=%s, sector=%s, macro=%s, top_score=%s, top_category=%s, reasons=%s",
                log_scope,
                category_counts[cls._DIRECT_NEWS_CATEGORY],
                category_counts[cls._SECTOR_NEWS_CATEGORY],
                category_counts[cls._MACRO_NEWS_CATEGORY],
                top.relevance_score,
                top.relevance_category,
                "；".join(top.relevance_reasons or []),
            )

        return SearchResponse(
            query=response.query,
            results=limited_results,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        )

    @classmethod
    def _filter_ranked_news_for_context(
        cls,
        response: SearchResponse,
        *,
        log_scope: str,
    ) -> SearchResponse:
        """Drop obvious non-news pages and zero-relevance fillers from ranked results."""
        if not response.success or not response.results:
            return response

        candidates: List[SearchResult] = []
        dropped_low_quality = 0
        dropped_adult_spam = 0
        dropped_zero_relevance = 0

        for item in response.results:
            is_official_source = cls._is_trusted_official_news_source(item)
            if (
                not is_official_source
                and cls._has_low_quality_news_page_signal(item)
            ):
                dropped_low_quality += 1
                continue
            if (
                not is_official_source
                and cls._has_adult_service_spam_news_page_signal(item)
            ):
                dropped_adult_spam += 1
                continue
            candidates.append(item)

        meaningful_candidates = [
            item
            for item in candidates
            if item.relevance_category == cls._DIRECT_NEWS_CATEGORY
            or (item.relevance_score or 0) > 0
        ]
        if meaningful_candidates:
            dropped_zero_relevance = len(candidates) - len(meaningful_candidates)
            filtered_results = meaningful_candidates
        else:
            filtered_results = candidates

        if dropped_low_quality or dropped_adult_spam or dropped_zero_relevance:
            logger.info(
                "[News access] %s: provider=%s, total=%s, kept=%s, "
                "drop_low_quality=%s, drop_adult_spam=%s, drop_zero_relevance=%s",
                log_scope,
                response.provider,
                len(response.results),
                len(filtered_results),
                dropped_low_quality,
                dropped_adult_spam,
                dropped_zero_relevance,
            )

        return SearchResponse(
            query=response.query,
            results=filtered_results,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        )

    @classmethod
    def _news_relevance_stats(
        cls,
        response: SearchResponse,
        *,
        prefer_chinese: bool,
    ) -> Dict[str, int]:
        results = response.results if response and response.results else []
        return {
            "direct_count": sum(
                1 for item in results if item.relevance_category == cls._DIRECT_NEWS_CATEGORY
            ),
            "preferred_direct_count": sum(
                1
                for item in results
                if (
                    prefer_chinese
                    and item.relevance_category == cls._DIRECT_NEWS_CATEGORY
                    and cls._is_chinese_news_result(item)
                )
            ),
            "preferred_count": sum(
                1 for item in results if prefer_chinese and cls._is_chinese_news_result(item)
            ),
            "max_score": max((item.relevance_score or 0 for item in results), default=0),
            "result_count": len(results),
        }

    @classmethod
    def _is_better_ranked_news_response(
        cls,
        candidate: SearchResponse,
        *,
        candidate_stats: Dict[str, int],
        best_response: Optional[SearchResponse],
        best_stats: Optional[Dict[str, int]],
        prefer_chinese: bool,
    ) -> bool:
        if best_response is None or best_stats is None:
            return True
        if candidate_stats["direct_count"] != best_stats["direct_count"]:
            return candidate_stats["direct_count"] > best_stats["direct_count"]
        if (
            prefer_chinese
            and candidate_stats["preferred_direct_count"] != best_stats["preferred_direct_count"]
        ):
            return candidate_stats["preferred_direct_count"] > best_stats["preferred_direct_count"]
        if prefer_chinese and candidate_stats["preferred_count"] != best_stats["preferred_count"]:
            return candidate_stats["preferred_count"] > best_stats["preferred_count"]
        if candidate_stats["max_score"] != best_stats["max_score"]:
            return candidate_stats["max_score"] > best_stats["max_score"]
        return candidate_stats["result_count"] > best_stats["result_count"]

    @staticmethod
    def _parse_relative_news_date(text: str, now: datetime) -> Optional[date]:
        """Parse common Chinese/English relative-time strings."""
        raw = (text or "").strip()
        if not raw:
            return None

        lower = raw.lower()
        if raw in {"today", "today", "just now"} or lower in {"today", "just now", "now"}:
            return now.date()
        if raw == "yesterday" or lower == "yesterday":
            return (now - timedelta(days=1)).date()
        if raw == "the day before yesterday":
            return (now - timedelta(days=2)).date()

        zh = re.match(r"^\s*(\d+)\s*(minutes|hours|day|week|months|month|year)\s*before\s*$", raw)
        if zh:
            amount = int(zh.group(1))
            unit = zh.group(2)
            if unit == "minute":
                return (now - timedelta(minutes=amount)).date()
            if unit == "Hour":
                return (now - timedelta(hours=amount)).date()
            if unit == "sky":
                return (now - timedelta(days=amount)).date()
            if unit == "week":
                return (now - timedelta(weeks=amount)).date()
            if unit in {"months", "month"}:
                return (now - timedelta(days=amount * 30)).date()
            if unit == "Year":
                return (now - timedelta(days=amount * 365)).date()

        en = re.match(
            r"^\s*(\d+)\s*(minute|minutes|min|mins|hour|hours|day|days|week|weeks|month|months|year|years)\s*ago\s*$",
            lower,
        )
        if en:
            amount = int(en.group(1))
            unit = en.group(2)
            if unit in {"minute", "minutes", "min", "mins"}:
                return (now - timedelta(minutes=amount)).date()
            if unit in {"hour", "hours"}:
                return (now - timedelta(hours=amount)).date()
            if unit in {"day", "days"}:
                return (now - timedelta(days=amount)).date()
            if unit in {"week", "weeks"}:
                return (now - timedelta(weeks=amount)).date()
            if unit in {"month", "months"}:
                return (now - timedelta(days=amount * 30)).date()
            if unit in {"year", "years"}:
                return (now - timedelta(days=amount * 365)).date()

        return None

    @classmethod
    def _normalize_news_publish_date(cls, value: Any) -> Optional[date]:
        """Normalize provider date value into a date object."""
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                local_tz = datetime.now().astimezone().tzinfo or timezone.utc
                return value.astimezone(local_tz).date()
            return value.date()
        if isinstance(value, date):
            return value

        text = str(value).strip()
        if not text:
            return None
        now = datetime.now()
        local_tz = now.astimezone().tzinfo or timezone.utc

        relative_date = cls._parse_relative_news_date(text, now)
        if relative_date:
            return relative_date

        # Unix timestamp fallback
        if text.isdigit() and len(text) in (10, 13):
            try:
                ts = int(text[:10]) if len(text) == 13 else int(text)
                # Provider timestamps are typically UTC epoch seconds.
                # Normalize to local date to keep window checks aligned with local "today".
                return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(local_tz).date()
            except (OSError, OverflowError, ValueError):
                pass

        iso_candidate = text.replace("Z", "+00:00")
        try:
            parsed_iso = datetime.fromisoformat(iso_candidate)
            if parsed_iso.tzinfo is not None:
                return parsed_iso.astimezone(local_tz).date()
            return parsed_iso.date()
        except ValueError:
            pass

        normalized = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text, flags=re.IGNORECASE)

        try:
            parsed_rfc = parsedate_to_datetime(normalized)
            if parsed_rfc:
                if parsed_rfc.tzinfo is not None:
                    return parsed_rfc.astimezone(local_tz).date()
                return parsed_rfc.date()
        except (TypeError, ValueError):
            pass

        zh_match = re.search(r"(\d{4})\s*[year/\-.]\s*(\d{1,2})\s*[month/\-.]\s*(\d{1,2})\s*day?", text)
        if zh_match:
            try:
                return date(int(zh_match.group(1)), int(zh_match.group(2)), int(zh_match.group(3)))
            except ValueError:
                pass

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
            "%Y.%m.%d %H:%M:%S",
            "%Y.%m.%d %H:%M",
            "%Y.%m.%d",
            "%Y%m%d",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
            "%a, %d %b %Y %H:%M:%S %z",
        ):
            try:
                parsed_dt = datetime.strptime(normalized, fmt)
                if parsed_dt.tzinfo is not None:
                    return parsed_dt.astimezone(local_tz).date()
                return parsed_dt.date()
            except ValueError:
                continue

        return None

    def _filter_news_response(
        self,
        response: SearchResponse,
        *,
        search_days: int,
        max_results: int,
        log_scope: str,
        keep_unknown: bool = False,
    ) -> SearchResponse:
        """Hard-filter results by published_date recency and normalize date strings."""
        if not response.success or not response.results:
            return response

        today = datetime.now().date()
        earliest = today - timedelta(days=max(0, int(search_days) - 1))
        latest = today + timedelta(days=self.FUTURE_TOLERANCE_DAYS)

        filtered: List[SearchResult] = []
        dropped_unknown = 0
        dropped_old = 0
        dropped_future = 0

        for item in response.results:
            published = self._normalize_news_publish_date(item.published_date)
            if published is None:
                if keep_unknown:
                    filtered.append(
                        SearchResult(
                            title=item.title,
                            snippet=item.snippet,
                            url=item.url,
                            source=item.source,
                            published_date=item.published_date,
                            relevance_score=item.relevance_score,
                            relevance_category=item.relevance_category,
                            relevance_reasons=item.relevance_reasons,
                        )
                    )
                    if len(filtered) >= max_results:
                        break
                    continue
                dropped_unknown += 1
                continue
            if published < earliest:
                dropped_old += 1
                continue
            if published > latest:
                dropped_future += 1
                continue

            filtered.append(
                SearchResult(
                    title=item.title,
                    snippet=item.snippet,
                    url=item.url,
                    source=item.source,
                    published_date=published.isoformat(),
                    relevance_score=item.relevance_score,
                    relevance_category=item.relevance_category,
                    relevance_reasons=item.relevance_reasons,
                )
            )
            if len(filtered) >= max_results:
                break

        if dropped_unknown or dropped_old or dropped_future:
            logger.info(
                "[news filter] %s: provider=%s, total=%s, kept=%s, drop_unknown=%s, drop_old=%s, drop_future=%s, window=[%s,%s]",
                log_scope,
                response.provider,
                len(response.results),
                len(filtered),
                dropped_unknown,
                dropped_old,
                dropped_future,
                earliest.isoformat(),
                latest.isoformat(),
            )

        return SearchResponse(
            query=response.query,
            results=filtered,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        )

    def _normalize_and_limit_response(
        self,
        response: SearchResponse,
        *,
        max_results: int,
    ) -> SearchResponse:
        """Normalize parseable dates without enforcing freshness filtering."""
        if not response.success or not response.results:
            return response

        normalized_results: List[SearchResult] = []
        for item in response.results[:max_results]:
            normalized_date = self._normalize_news_publish_date(item.published_date)
            normalized_results.append(
                SearchResult(
                    title=item.title,
                    snippet=item.snippet,
                    url=item.url,
                    source=item.source,
                    published_date=(
                        normalized_date.isoformat() if normalized_date is not None else item.published_date
                    ),
                    relevance_score=item.relevance_score,
                    relevance_category=item.relevance_category,
                    relevance_reasons=item.relevance_reasons,
                )
            )

        return SearchResponse(
            query=response.query,
            results=normalized_results,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        )

    @staticmethod
    def _limit_search_response(
        response: SearchResponse,
        *,
        max_results: int,
    ) -> SearchResponse:
        """Trim response results without changing the rest of the metadata."""
        if not response.success or not response.results:
            return response

        limited_results = response.results[:max_results]
        if len(limited_results) == len(response.results):
            return response

        return SearchResponse(
            query=response.query,
            results=limited_results,
            provider=response.provider,
            success=response.success,
            error_message=response.error_message,
            search_time=response.search_time,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, int((time.monotonic() - started_at) * 1000))

    @staticmethod
    def _record_news_search_run(
        *,
        provider: str,
        operation: str,
        success: bool,
        latency_ms: Optional[int] = None,
        record_count: Optional[int] = None,
        cache_hit: Optional[bool] = None,
        error_type: Optional[str] = None,
        error_message: Optional[Any] = None,
    ) -> None:
        record_provider_run(
            data_type="news_search",
            provider=provider,
            operation=operation,
            success=success,
            latency_ms=latency_ms,
            error_type=error_type,
            error_message=error_message,
            cache_hit=cache_hit,
            record_count=record_count,
        )

    def search_stock_news(
        self,
        stock_code: str,
        stock_name: str,
        max_results: int = 5,
        focus_keywords: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        Search stock related news
        
        Args:
            stock_code: Stock code
            stock_name: Stock name
            max_results: Maximum number of results returned
            focus_keywords: List of key words to focus on
            
        Returns:
            SearchResponse object
        """
        # Policy window priority：ultra_short/short/medium/long = 1/3/7/30 sky，
        # and receive unified NEWS_MAX_AGE_DAYS upper limit constraint。
        search_days = self._effective_news_window_days()
        provider_max_results = self._provider_request_size(max_results)
        prefer_chinese = self._should_prefer_chinese_news(
            stock_code,
            stock_name,
            focus_keywords=focus_keywords,
        )

        # Build a search query（Optimize search results）
        is_foreign = self._is_foreign_stock(stock_code)
        if focus_keywords:
            # If keywords are provided，Use keywords directly as queries
            query = " ".join(focus_keywords)
        elif prefer_chinese:
            query = f"{stock_name} {stock_code} stock latest news"
        elif is_foreign:
            # Hong Kong stocks/Use English search keywords for US stocks
            query = f"{stock_name} {stock_code} stock latest news"
        else:
            # Default main query：Stock name + core keywords
            query = f"{stock_name} {stock_code} stock latest news"

        logger.info(
            (
                "Search stock news: %s(%s), query='%s', time range: close%ssky "
                "(profile=%s, NEWS_MAX_AGE_DAYS=%s, prefer_chinese=%s), Target number=%s, providerNumber of requests=%s"
            ),
            stock_name,
            stock_code,
            query,
            search_days,
            self.news_strategy_profile,
            self.news_max_age_days,
            prefer_chinese,
            max_results,
            provider_max_results,
        )

        cache_key = self._cache_key(
            (
                f"{query}|target={stock_code}:{stock_name}|"
                f"news_pref={'zh' if prefer_chinese else 'default'}"
            ),
            max_results,
            search_days,
        )
        cached, cache_owner, cache_event = self._get_cached_or_reserve(cache_key)
        if cached is not None:
            logger.info(f"Cached search results after using concurrent population: {stock_name}({stock_code})")
            self._record_news_search_run(
                provider=cached.provider or "SearchCache",
                operation="search_stock_news_cache",
                success=bool(cached.success),
                latency_ms=0,
                record_count=len(cached.results or []),
                cache_hit=True,
                error_message=cached.error_message,
            )
            return cached

        if not cache_owner and cache_event is not None:
            cached = self._wait_for_cached(cache_key, cache_event)
            if cached is not None:
                logger.info(f"Cached search results after using concurrent population: {stock_name}({stock_code})")
                self._record_news_search_run(
                    provider=cached.provider or "SearchCache",
                    operation="search_stock_news_cache_wait",
                    success=bool(cached.success),
                    latency_ms=0,
                    record_count=len(cached.results or []),
                    cache_hit=True,
                    error_message=cached.error_message,
                )
                return cached
            cached, cache_owner, cache_event = self._get_cached_or_reserve(cache_key)
            if cached is not None:
                logger.info(f"Using cached search results for hits after waiting: {stock_name}({stock_code})")
                self._record_news_search_run(
                    provider=cached.provider or "SearchCache",
                    operation="search_stock_news_cache_retry",
                    success=bool(cached.success),
                    latency_ms=0,
                    record_count=len(cached.results or []),
                    cache_hit=True,
                    error_message=cached.error_message,
                )
                return cached

        try:
            # Try each search engine in sequence（If it is empty after filtering，Continue to try the next engine）
            had_provider_success = False
            best_ranked_response: Optional[SearchResponse] = None
            best_ranked_stats: Optional[Dict[str, int]] = None
            for provider in self._providers:
                if not provider.is_available:
                    continue

                search_kwargs: Dict[str, Any] = {}
                if isinstance(provider, TavilySearchProvider):
                    search_kwargs["topic"] = "news"
                elif isinstance(provider, BraveSearchProvider):
                    search_kwargs.update(
                        self._brave_search_locale(
                            stock_code,
                            prefer_chinese=prefer_chinese,
                        )
                    )

                started_at = time.monotonic()
                try:
                    record_provider_run_started(
                        data_type="news_search",
                        provider=provider.name,
                        operation="search_stock_news",
                    )
                    response = provider.search(query, provider_max_results, days=search_days, **search_kwargs)
                except Exception as exc:
                    self._record_news_search_run(
                        provider=provider.name,
                        operation="search_stock_news",
                        success=False,
                        latency_ms=self._elapsed_ms(started_at),
                        error_type=type(exc).__name__,
                        error_message=exc,
                    )
                    raise
                filtered_response = self._filter_news_response(
                    response,
                    search_days=search_days,
                    max_results=provider_max_results,
                    log_scope=f"{stock_code}:{provider.name}:stock_news",
                )
                had_provider_success = had_provider_success or bool(response.success)

                if filtered_response.success and filtered_response.results:
                    language_response, _preferred_count = self._prioritize_news_language(
                        filtered_response,
                        prefer_chinese=prefer_chinese,
                    )
                    ranked_response = self._rank_news_response(
                        language_response,
                        stock_code=stock_code,
                        stock_name=stock_name,
                        prefer_chinese=prefer_chinese,
                        max_results=provider_max_results,
                        log_scope=f"{stock_code}:{provider.name}:stock_news",
                    )
                    admitted_response = self._filter_ranked_news_for_context(
                        ranked_response,
                        log_scope=f"{stock_code}:{provider.name}:stock_news",
                    )
                    limited_response = self._limit_search_response(
                        admitted_response,
                        max_results=max_results,
                    )
                    admitted_count = len(limited_response.results or [])
                    self._record_news_search_run(
                        provider=provider.name,
                        operation="search_stock_news",
                        success=bool(limited_response.success and limited_response.results),
                        latency_ms=self._elapsed_ms(started_at),
                        record_count=admitted_count,
                        error_type=None if admitted_count else "NoUsableNews",
                        error_message=None if admitted_count else (
                            response.error_message or "No valid news after filtering"
                        ),
                    )
                    if not admitted_count:
                        logger.info(
                            "%s The search was successful but there was no valid news after admission filtering.，Continue to try the next engine",
                            provider.name,
                        )
                        continue

                    stats = self._news_relevance_stats(
                        limited_response,
                        prefer_chinese=prefer_chinese,
                    )
                    if self._is_better_ranked_news_response(
                        limited_response,
                        candidate_stats=stats,
                        best_response=best_ranked_response,
                        best_stats=best_ranked_stats,
                        prefer_chinese=prefer_chinese,
                    ):
                        best_ranked_response = limited_response
                        best_ranked_stats = stats

                    if stats["direct_count"] > 0 and (
                        not prefer_chinese or stats["preferred_direct_count"] > 0
                    ):
                        logger.info(
                            "%s Search successful，recognized %s direct stock news，Return first",
                            provider.name,
                            stats["direct_count"],
                        )
                        self._put_cache(cache_key, limited_response)
                        return limited_response

                    if prefer_chinese and stats["direct_count"] > 0:
                        logger.info(
                            "%s Search successful，recognized %s Direct stock news but lacks Chinese direct hits，Continue to try the next engine",
                            provider.name,
                            stats["direct_count"],
                        )
                        continue

                    if prefer_chinese and stats["preferred_count"] >= max_results:
                        logger.info(
                            "%s Search successful，Chinese results have met the target number but lack direct stock hits，Continue to try the next engine",
                            provider.name,
                        )
                        continue

                    if prefer_chinese and stats["preferred_count"] > 0:
                        logger.info(
                            "%s Search successful，recognized %s/%s Chinese news but lacks direct stock hits，Continue to try the next engine",
                            provider.name,
                            stats["preferred_count"],
                            len(limited_response.results),
                        )
                    else:
                        logger.info(
                            "%s Search successful but no direct stock news identified，Continue to try the next engine",
                            provider.name,
                        )
                else:
                    filtered_count = len(filtered_response.results or []) if filtered_response.success else 0
                    self._record_news_search_run(
                        provider=provider.name,
                        operation="search_stock_news",
                        success=bool(filtered_response.success and filtered_response.results),
                        latency_ms=self._elapsed_ms(started_at),
                        record_count=filtered_count,
                        error_type=None if filtered_count else "NoUsableNews",
                        error_message=None if filtered_count else (
                            response.error_message or "No valid news after filtering"
                        ),
                    )
                    if response.success and not filtered_response.results:
                        logger.info(
                            "%s Search successful but no valid news after filtering，Continue to try the next engine",
                            provider.name,
                        )
                    else:
                        logger.warning(
                            "%s Search failed: %s，try next engine",
                            provider.name,
                            response.error_message,
                        )

            if best_ranked_response is not None:
                self._put_cache(cache_key, best_ranked_response)
                return best_ranked_response

            if had_provider_success:
                return SearchResponse(
                    query=query,
                    results=[],
                    provider="Filtered",
                    success=True,
                    error_message=None,
                )
            
            # all engines fail
            return SearchResponse(
                query=query,
                results=[],
                provider="None",
                success=False,
                error_message="All search engines are unavailable or search failed"
            )
        finally:
            if cache_owner and cache_event is not None:
                self._release_cache_fill(cache_key, cache_event)
    
    def search_stock_events(
        self,
        stock_code: str,
        stock_name: str,
        event_types: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        Search for stock specific events（Annual report preview、Reduce holdings, etc.）
        
        Search specifically for important events related to trading decisions
        
        Args:
            stock_code: Stock code
            stock_name: Stock name
            event_types: Event type list
            
        Returns:
            SearchResponse object
        """
        if event_types is None:
            if self._is_foreign_stock(stock_code):
                event_types = ["earnings report", "insider selling", "quarterly results"]
            else:
                event_types = ["Annual report preview", "Announcement of reduction of holdings", "Performance report"]
        
        # Build targeted queries
        event_query = " OR ".join(event_types)
        query = f"{stock_name} ({event_query})"
        
        logger.info(f"Search stock events: {stock_name}({stock_code}) - {event_types}")
        
        # Try each search engine in sequence
        for provider in self._providers:
            if not provider.is_available:
                continue
            
            response = provider.search(query, max_results=5)
            
            if response.success:
                return response
        
        return SearchResponse(
            query=query,
            results=[],
            provider="None",
            success=False,
            error_message="Event search failed"
        )
    
    def search_comprehensive_intel(
        self,
        stock_code: str,
        stock_name: str,
        max_searches: int = 3
    ) -> Dict[str, SearchResponse]:
        """
        Multi-dimensional intelligence search（Use multiple engines simultaneously、multiple dimensions）
        
        Search dimensions：
        1. latest news - Recent news
        2. Risk investigation - Reduce holdings、punishment、Bad
        3. performance expectations - Annual report preview、Performance report
        
        Args:
            stock_code: Stock code
            stock_name: Stock name
            max_searches: Maximum number of searches
            
        Returns:
            {Dimension name: SearchResponse} dictionary
        """
        results = {}
        search_count = 0

        is_foreign = self._is_foreign_stock(stock_code)
        is_index_etf = self.is_index_or_etf(stock_code, stock_name)

        if is_foreign:
            search_dimensions = [
                {
                    'name': 'latest_news',
                    'query': f"{stock_name} {stock_code} latest news events",
                    'desc': 'latest news',
                    'tavily_topic': 'news',
                    'strict_freshness': True,
                },
                {
                    'name': 'market_analysis',
                    'query': f"{stock_name} analyst rating target price report",
                    'desc': 'Institutional analysis',
                    'tavily_topic': None,
                    'strict_freshness': False,
                },
                {
                    'name': 'risk_check',
                    'query': (
                        f"{stock_name} {stock_code} index performance outlook tracking error"
                        if is_index_etf else f"{stock_name} risk insider selling lawsuit litigation"
                    ),
                    'desc': 'Risk investigation',
                    'tavily_topic': None if is_index_etf else 'news',
                    'strict_freshness': not is_index_etf,
                },
                {
                    'name': 'earnings',
                    'query': (
                        f"{stock_name} {stock_code} index performance composition outlook"
                        if is_index_etf else f"{stock_name} earnings revenue profit growth forecast"
                    ),
                    'desc': 'performance expectations',
                    'tavily_topic': None,
                    'strict_freshness': False,
                },
                {
                    'name': 'industry',
                    'query': (
                        f"{stock_name} {stock_code} index sector allocation holdings"
                        if is_index_etf else f"{stock_name} industry competitors market share outlook"
                    ),
                    'desc': 'Industry analysis',
                    'tavily_topic': None,
                    'strict_freshness': False,
                },
            ]
        else:
            search_dimensions = [
                {
                    'name': 'latest_news',
                    'query': f"{stock_name} {stock_code} up to date news major event",
                    'desc': 'latest news',
                    'tavily_topic': 'news',
                    'strict_freshness': True,
                },
                {
                    'name': 'market_analysis',
                    'query': f"{stock_name} research report target price Rating In-depth analysis",
                    'desc': 'Institutional analysis',
                    'tavily_topic': None,
                    'strict_freshness': False,
                },
                {
                    'name': 'risk_check',
                    'query': (
                        f"{stock_name} Index trend tracking error net worth Performance"
                        if is_index_etf else f"{stock_name} Reduce holdings punishment risk litigation Bad risk"
                    ),
                    'desc': 'Risk investigation',
                    'tavily_topic': None if is_index_etf else 'news',
                    'strict_freshness': not is_index_etf,
                },
                {
                    'name': 'announcements',
                    'query': (
                        f"{stock_name} {stock_code} announcement Index adjustment Ingredient changes"
                        if is_index_etf else f"{stock_name} {stock_code} company announcement Important announcement Shanghai Stock Exchange Shenzhen Stock Exchange cninfo"
                    ),
                    'desc': 'company announcement',
                    'tavily_topic': 'news',
                    'strict_freshness': True,
                },
                {
                    'name': 'earnings',
                    'query': (
                        f"{stock_name} Track performance net worth Track performance"
                        if is_index_etf else f"{stock_name} Performance forecast financial report Revenue net profit year-on-year growth"
                    ),
                    'desc': 'performance expectations',
                    'tavily_topic': None,
                    'strict_freshness': False,
                },
                {
                    'name': 'industry',
                    'query': (
                        f"{stock_name} Index constituents Industry configuration Industry"
                        if is_index_etf else f"{stock_name} Industry competitors market share Industry prospects"
                    ),
                    'desc': 'Industry analysis',
                    'tavily_topic': None,
                    'strict_freshness': False,
                },
            ]
        
        search_days = self._effective_news_window_days()
        target_per_dimension = 3
        provider_max_results = self._provider_request_size(target_per_dimension)

        logger.info(
            (
                "Start multi-dimensional intelligence search: %s(%s), time range: close%ssky "
                "(profile=%s, NEWS_MAX_AGE_DAYS=%s), Target number=%s, providerNumber of requests=%s"
            ),
            stock_name,
            stock_code,
            search_days,
            self.news_strategy_profile,
            self.news_max_age_days,
            target_per_dimension,
            provider_max_results,
        )
        
        # Rotate through different search engines
        provider_index = 0
        
        for dim in search_dimensions:
            if search_count >= max_searches:
                break
            
            # Choose search engine（Take turns）
            available_providers = [p for p in self._providers if p.is_available]
            if not available_providers:
                break
            
            provider = available_providers[provider_index % len(available_providers)]
            provider_index += 1
            
            request_days = (
                self.ANALYTICAL_INTEL_LOOKBACK_DAYS
                if dim['name'] in self.ANALYTICAL_INTEL_DIMENSIONS
                else search_days
            )

            logger.info(
                "[intelligence search] %s: use %s，request window: close%ssky",
                dim['desc'],
                provider.name,
                request_days,
            )

            if isinstance(provider, TavilySearchProvider) and dim.get('tavily_topic'):
                response = provider.search(
                    dim['query'],
                    max_results=provider_max_results,
                    days=request_days,
                    topic=dim['tavily_topic'],
                )
            else:
                response = provider.search(
                    dim['query'],
                    max_results=provider_max_results,
                    days=request_days,
                )
            if dim['strict_freshness']:
                filtered_response = self._filter_news_response(
                    response,
                    search_days=search_days,
                    max_results=provider_max_results,
                    log_scope=f"{stock_code}:{provider.name}:{dim['name']}",
                )
            elif dim['name'] in self.ANALYTICAL_INTEL_DIMENSIONS:
                filtered_response = self._filter_news_response(
                    response,
                    search_days=self.ANALYTICAL_INTEL_LOOKBACK_DAYS,
                    max_results=provider_max_results,
                    keep_unknown=True,
                    log_scope=f"{stock_code}:{provider.name}:{dim['name']}",
                )
            else:
                filtered_response = self._normalize_and_limit_response(
                    response,
                    max_results=provider_max_results,
                )
            filtered_response = self._rank_news_response(
                filtered_response,
                stock_code=stock_code,
                stock_name=stock_name,
                prefer_chinese=self._should_prefer_chinese_news(stock_code, stock_name),
                max_results=provider_max_results,
                log_scope=f"{stock_code}:{provider.name}:{dim['name']}:rank",
            )
            filtered_response = self._filter_ranked_news_for_context(
                filtered_response,
                log_scope=f"{stock_code}:{provider.name}:{dim['name']}:admission",
            )
            filtered_response = self._limit_search_response(
                filtered_response,
                max_results=target_per_dimension,
            )
            results[dim['name']] = filtered_response
            search_count += 1
            
            if response.success:
                logger.info(
                    "[intelligence search] %s: original=%sstrip, After filtering=%sstrip",
                    dim['desc'],
                    len(response.results),
                    len(filtered_response.results),
                )
            else:
                logger.warning(f"[intelligence search] {dim['desc']}: Search failed - {response.error_message}")
            
            # Short delay to avoid requesting too quickly
            time.sleep(0.5)
        
        return results
    
    def format_intel_report(self, intel_results: Dict[str, SearchResponse], stock_name: str) -> str:
        """
        Format intelligence search results into reports
        
        Args:
            intel_results: Multidimensional search results
            stock_name: Stock name
            
        Returns:
            Formatted intelligence report text
        """
        lines = [f"【{stock_name} Intelligence search results】"]
        
        # Dimension display order
        display_order = ['latest_news', 'announcements', 'market_analysis', 'risk_check', 'earnings', 'industry']

        dim_labels = {
            'latest_news': '📰 latest news',
            'announcements': '📋 company announcement',
            'market_analysis': '📈 Institutional analysis',
            'risk_check': '⚠️ Risk investigation',
            'earnings': '📊 performance expectations',
            'industry': '🏭 Industry analysis',
        }

        for dim_name in display_order:
            if dim_name not in intel_results:
                continue
                
            resp = intel_results[dim_name]
            
            # Increase the number of displayed items
            dim_desc = dim_labels.get(dim_name, dim_name)
            
            lines.append(f"\n{dim_desc} (Source: {resp.provider}):")
            if resp.success and resp.results:
                # Increase the number of displayed items
                for i, r in enumerate(resp.results[:4], 1):
                    date_str = f" [{r.published_date}]" if r.published_date else ""
                    lines.append(f"  {i}. {r.title}{date_str}")
                    # If the summary is too short，There may not be enough information
                    snippet = r.snippet[:150] if len(r.snippet) > 20 else r.snippet
                    lines.append(f"     {snippet}...")
                    if r.relevance_category or r.relevance_reasons:
                        relevance_parts = []
                        if r.relevance_category:
                            relevance_parts.append(r.relevance_category)
                        if r.relevance_score is not None:
                            relevance_parts.append(f"score={r.relevance_score}")
                        if r.relevance_reasons:
                            relevance_parts.append(f"Basis: {'；'.join(r.relevance_reasons[:3])}")
                        lines.append(f"     Relevance: {'; '.join(relevance_parts)}")
            else:
                lines.append("  No relevant information found")
        
        return "\n".join(lines)
    
    def batch_search(
        self,
        stocks: List[Dict[str, str]],
        max_results_per_stock: int = 3,
        delay_between: float = 1.0
    ) -> Dict[str, SearchResponse]:
        """
        Batch search news for multiple stocks.
        
        Args:
            stocks: List of stocks
            max_results_per_stock: Max results per stock
            delay_between: Delay between searches (seconds)
            
        Returns:
            Dict of results
        """
        results = {}
        
        for i, stock in enumerate(stocks):
            if i > 0:
                time.sleep(delay_between)
            
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            response = self.search_stock_news(code, name, max_results_per_stock)
            results[code] = response
        
        return results

    def search_stock_price_fallback(
        self,
        stock_code: str,
        stock_name: str,
        max_attempts: int = 3,
        max_results: int = 5
    ) -> SearchResponse:
        """
        Enhance search when data sources fail.
        
        When all data sources (efinance, akshare, tushare, baostock, etc.) fail to get
        stock data, use search engines to find stock trends and price info as supplemental data for AI analysis.
        
        Strategy:
        1. Search using multiple keyword templates
        2. Try all available search engines for each keyword
        3. Aggregate and deduplicate results
        
        Args:
            stock_code: Stock Code
            stock_name: Stock Name
            max_attempts: Max search attempts (using different keywords)
            max_results: Max results to return
            
        Returns:
            SearchResponse object with aggregated results
        """

        if not self.is_available:
            return SearchResponse(
                query=f"{stock_name} Stock price trend",
                results=[],
                provider="None",
                success=False,
                error_message="Search capability not configured"
            )
        
        logger.info(f"[Enhanced search] Data source failed，Start enhanced search: {stock_name}({stock_code})")
        
        all_results = []
        seen_urls = set()
        successful_providers = []
        
        # Search using multiple keyword templates
        is_foreign = self._is_foreign_stock(stock_code)
        keywords = self.ENHANCED_SEARCH_KEYWORDS_EN if is_foreign else self.ENHANCED_SEARCH_KEYWORDS
        for i, keyword_template in enumerate(keywords[:max_attempts]):
            query = keyword_template.format(name=stock_name, code=stock_code)
            
            logger.info(f"[Enhanced search] No. {i+1}/{max_attempts} searches: {query}")
            
            # Try each search engine in sequence
            for provider in self._providers:
                if not provider.is_available:
                    continue
                
                try:
                    response = provider.search(query, max_results=3)
                    
                    if response.success and response.results:
                        # Remove duplicates and add results
                        for result in response.results:
                            if result.url not in seen_urls:
                                seen_urls.add(result.url)
                                all_results.append(result)
                                
                        if provider.name not in successful_providers:
                            successful_providers.append(provider.name)
                        
                        logger.info(f"[Enhanced search] {provider.name} return {len(response.results)} results")
                        break  # Jump to the next keyword after success
                    else:
                        logger.debug(f"[Enhanced search] {provider.name} No result or failure")
                        
                except Exception as e:
                    logger.warning(f"[Enhanced search] {provider.name} Search exception: {e}")
                    continue
            
            # Short delay to avoid requesting too quickly
            if i < max_attempts - 1:
                time.sleep(0.5)
        
        # before interception
        if all_results:
            # before interception max_results strip
            final_results = all_results[:max_results]
            provider_str = ", ".join(successful_providers) if successful_providers else "None"
            
            logger.info(f"[Enhanced search] Finish，Obtained in total {len(final_results)} results（source: {provider_str}）")
            
            return SearchResponse(
                query=f"{stock_name}({stock_code}) Stock price trend",
                results=final_results,
                provider=provider_str,
                success=True,
            )
        else:
            logger.warning(f"[Enhanced search] All searches returned no results")
            return SearchResponse(
                query=f"{stock_name}({stock_code}) Stock price trend",
                results=[],
                provider="None",
                success=False,
                error_message="Enhanced search found no relevant information"
            )

    def search_stock_with_enhanced_fallback(
        self,
        stock_code: str,
        stock_name: str,
        include_news: bool = True,
        include_price: bool = False,
        max_results: int = 5
    ) -> Dict[str, SearchResponse]:
        """
        Comprehensive search interface（Support news and stock price information）
        
        when include_price=True hour，Will search for news and stock price information at the same time。
        Mainly used as a backup plan when the data source completely fails.。
        
        Args:
            stock_code: Stock code
            stock_name: Stock name
            include_news: Whether to search for news
            include_price: Whether to search for stock price/Trend information
            max_results: Maximum number of results per type of search
            
        Returns:
            {'news': SearchResponse, 'price': SearchResponse} dictionary
        """
        results = {}
        
        if include_news:
            results['news'] = self.search_stock_news(
                stock_code, 
                stock_name, 
                max_results=max_results
            )
        
        if include_price:
            results['price'] = self.search_stock_price_fallback(
                stock_code,
                stock_name,
                max_attempts=3,
                max_results=max_results
            )
        
        return results

    def format_price_search_context(self, response: SearchResponse) -> str:
        """
        Format stock price search results as AI Analyze context
        
        Args:
            response: Search response object
            
        Returns:
            formatted text，Can be used directly AI analyze
        """
        if not response.success or not response.results:
            return "【Stock price trend search】No relevant information found，Please refer to other channel data for reference.。"
        
        lines = [
            f"【Stock price trend search results】（source: {response.provider}）",
            "⚠️ Notice：The following information comes from web searches，For reference only，There may be delays or inaccuracies。",
            ""
        ]
        
        for i, result in enumerate(response.results, 1):
            date_str = f" [{result.published_date}]" if result.published_date else ""
            lines.append(f"{i}. 【{result.source}】{result.title}{date_str}")
            lines.append(f"   {result.snippet[:200]}...")
            lines.append("")
        
        return "\n".join(lines)


# === Convenience function ===
_search_service: Optional[SearchService] = None
_search_service_lock = threading.Lock()


def get_search_service() -> SearchService:
    """Get the search service singleton"""
    global _search_service
    
    if _search_service is None:
        with _search_service_lock:
            if _search_service is None:
                from src.config import get_config
                config = get_config()
                
                _search_service = SearchService(
                    bocha_keys=config.bocha_api_keys,
                    tavily_keys=config.tavily_api_keys,
                    anspire_keys=config.anspire_api_keys,
                    brave_keys=config.brave_api_keys,
                    serpapi_keys=config.serpapi_keys,
                    minimax_keys=config.minimax_api_keys,
                    searxng_base_urls=config.searxng_base_urls,
                    searxng_public_instances_enabled=config.searxng_public_instances_enabled,
                    news_max_age_days=config.news_max_age_days,
                    news_strategy_profile=getattr(config, "news_strategy_profile", "short"),
                )
    
    return _search_service


def reset_search_service() -> None:
    """Reset search service（for testing）"""
    global _search_service
    with _search_service_lock:
        _search_service = None


if __name__ == "__main__":
    # Test search service
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    )
    
    # Requires configuration（Requires configuration API Key）
    service = get_search_service()
    
    if service.is_available:
        print("=== Test stock news search ===")
        response = service.search_stock_news("300389", "Absen")
        print(f"search status: {'success' if response.success else 'failed'}")
        print(f"search engine: {response.provider}")
        print(f"number of results: {len(response.results)}")
        print(f"time consuming: {response.search_time:.2f}s")
        print("\n" + response.to_context())
    else:
        print("Search capability not configured，skip test")
