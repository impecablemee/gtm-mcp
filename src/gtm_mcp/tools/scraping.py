"""Website scraping — Apify residential proxy with retry, direct fallback, HTML cleanup.

3-layer fallback: Apify proxy → direct fetch → HTTP fallback.
Retries on 429/5xx with exponential backoff.
BeautifulSoup + CSS selector cleanup for clean text extraction.
"""
import asyncio
import random
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

MAX_TEXT_LENGTH = 50_000
_request_count = 0


def _validate_url(url: str) -> tuple[bool, str, str]:
    """Validate and normalize URL. Returns (is_valid, normalized_url, error)."""
    if not url:
        return False, "", "INVALID_URL: URL is empty"
    url = url.strip()
    if url in ("--", "-", "n/a", "N/A", "na", "NA", "none", "None", "null", ""):
        return False, "", "INVALID_URL: No URL provided"
    if len(url) < 4:
        return False, "", "INVALID_URL: URL is too short"
    if " " in url or "\n" in url:
        return False, "", "INVALID_URL: URL contains invalid characters"
    url = re.sub(r"^(https?:/*)?", "", url, flags=re.IGNORECASE).rstrip("/")
    if not url or "." not in url.split("/")[0]:
        return False, "", "INVALID_URL: No valid domain found"
    normalized = f"https://{url}"
    try:
        parsed = urlparse(normalized)
        if not parsed.netloc:
            return False, "", "INVALID_URL: Could not parse URL"
        parts = parsed.netloc.split(".")
        if len(parts) < 2 or len(parts[-1]) < 2:
            return False, "", "INVALID_URL: Invalid domain format"
    except Exception:
        return False, "", "INVALID_URL: URL parsing failed"
    return True, normalized, ""


def _get_headers() -> dict:
    """Realistic browser headers with rotating user agent."""
    global _request_count
    _request_count += 1
    return {
        "User-Agent": USER_AGENTS[_request_count % len(USER_AGENTS)],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def _get_proxy(apify_proxy_password: Optional[str]) -> Optional[str]:
    """Build Apify residential proxy URL with session ID."""
    if not apify_proxy_password:
        return None
    session_id = f"scrape_{random.randint(10000, 99999)}"
    return f"http://groups-RESIDENTIAL,session-{session_id}:{apify_proxy_password}@proxy.apify.com:8000"


def _is_retryable(status_code: Optional[int], error: str) -> bool:
    """Check if failure is worth retrying."""
    if status_code and (status_code == 429 or status_code >= 500):
        return True
    if "UPSTREAM" in error or "TIMEOUT" in error:
        return True
    return False


def _clean_html(html: str) -> str:
    """Extract readable text from HTML. Removes nav, footer, cookies, popups, sidebars."""
    try:
        soup = BeautifulSoup(html, "lxml")

        # Remove non-content HTML elements
        for tag in soup.find_all([
            "script", "style", "nav", "header", "footer", "aside",
            "noscript", "iframe", "svg", "path", "meta", "link",
            "form", "button", "input", "select", "textarea",
        ]):
            tag.decompose()

        # Remove elements with common non-content CSS classes/IDs
        for selector in [
            '[class*="nav"]', '[class*="menu"]', '[class*="sidebar"]',
            '[class*="footer"]', '[class*="header"]', '[class*="cookie"]',
            '[class*="popup"]', '[class*="modal"]', '[class*="banner"]',
            '[class*="advertisement"]', '[class*="social"]', '[class*="share"]',
            '[id*="nav"]', '[id*="menu"]', '[id*="sidebar"]',
            '[id*="footer"]', '[id*="header"]', '[id*="cookie"]',
        ]:
            try:
                for el in soup.select(selector):
                    el.decompose()
            except Exception:
                pass

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:MAX_TEXT_LENGTH]
    except Exception:
        return ""


def _is_binary(content: bytes) -> bool:
    if not content:
        return False
    sample = content[:8192]
    non_printable = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))
    return non_printable / len(sample) > 0.15


async def _fetch(url: str, proxy: Optional[str], timeout: float) -> dict:
    """Single fetch attempt with proxy or direct."""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            verify=True,
            proxy=proxy,
        ) as client:
            resp = await client.get(url, headers=_get_headers())
            sc = resp.status_code

            if sc == 403:
                return {"success": False, "error": "BLOCKED: Access denied (403)", "status_code": 403}
            if sc == 404:
                return {"success": False, "error": "NOT_FOUND: Page does not exist (404)", "status_code": 404}
            if sc == 429:
                return {"success": False, "error": "RATE_LIMITED: Too many requests (429)", "status_code": 429}
            if sc >= 500:
                return {"success": False, "error": f"SERVER_ERROR: HTTP {sc}", "status_code": sc}
            if sc >= 400:
                return {"success": False, "error": f"ERROR: HTTP {sc}", "status_code": sc}

            if _is_binary(resp.content):
                return {"success": False, "error": "BINARY: Not a text page", "status_code": sc}

            text = _clean_html(resp.text)
            if not text or len(text) < 50:
                return {"success": False, "error": "EMPTY: No text content", "status_code": sc}

            return {"success": True, "text": text, "status_code": sc, "text_length": len(text)}

    except httpx.TimeoutException:
        return {"success": False, "error": f"TIMEOUT: No response within {timeout}s", "status_code": None}
    except httpx.ConnectError as e:
        err = str(e).lower()
        if "ssl" in err or "certificate" in err:
            return {"success": False, "error": "SSL_ERROR: Certificate verification failed", "status_code": None}
        if "nodename" in err or "getaddrinfo" in err or "name or service not known" in err:
            return {"success": False, "error": "DNS_ERROR: Domain not found", "status_code": None}
        return {"success": False, "error": "CONNECTION_ERROR: Could not connect", "status_code": None}
    except httpx.TooManyRedirects:
        return {"success": False, "error": "REDIRECT_ERROR: Too many redirects", "status_code": None}
    except Exception as e:
        return {"success": False, "error": f"ERROR: {str(e)[:100]}", "status_code": None}


async def scrape_website(
    url: str,
    apify_proxy_password: Optional[str] = None,
    timeout: float = 15.0,
) -> dict:
    """Scrape a website with 3-layer fallback and retry on 429/5xx.

    Layer 1: Apify residential proxy (if configured)
    Layer 2: Direct fetch (no proxy) — fallback when proxy fails
    Layer 3: HTTP fallback (when HTTPS fails on either layer)

    Retries 429/5xx with exponential backoff (2s, 4s).
    """
    is_valid, normalized, error = _validate_url(url)
    if not is_valid:
        return {"success": False, "error": error, "url": url}

    proxy = _get_proxy(apify_proxy_password)

    # Layer 1: Apify proxy (with retries)
    result = await _fetch(normalized, proxy, timeout)

    for attempt in range(2):
        if result["success"] or not _is_retryable(result.get("status_code"), result.get("error", "")):
            break
        await asyncio.sleep((attempt + 1) * 2)  # 2s, 4s
        result = await _fetch(normalized, proxy, timeout)

    if result["success"]:
        result["url"] = url
        return result

    # Layer 2: Direct fetch (no proxy) — when proxy fails on 5xx/connection
    if proxy:
        err = result.get("error", "")
        if "UPSTREAM" in err or "CONNECTION" in err or "TIMEOUT" in err or "SERVER_ERROR" in err:
            direct = await _fetch(normalized, None, timeout)
            if direct["success"]:
                direct["url"] = url
                return direct
            # Also try HTTP direct
            if "CONNECTION" in direct.get("error", "") or "SSL" in direct.get("error", ""):
                http_direct = await _fetch(normalized.replace("https://", "http://"), None, timeout)
                if http_direct["success"]:
                    http_direct["url"] = url
                    return http_direct

    # Layer 3: HTTP fallback (with proxy)
    if "CONNECTION" in result.get("error", "") or "SSL" in result.get("error", ""):
        http_result = await _fetch(normalized.replace("https://", "http://"), proxy, timeout)
        if http_result["success"]:
            http_result["url"] = url
            return http_result

    result["url"] = url
    return result


async def scrape_batch(
    urls: list[str],
    apify_proxy_password: Optional[str] = None,
    timeout: float = 15.0,
    max_concurrent: int = 50,
) -> dict:
    """Scrape many URLs in parallel with concurrency pool.

    Uses asyncio.Semaphore to limit concurrent requests (default 50).
    Returns results for all URLs in one call — much faster than
    calling scrape_website() individually from the agent.
    """
    sem = asyncio.Semaphore(max_concurrent)
    results: list[dict] = []

    async def process(url: str, idx: int):
        async with sem:
            result = await scrape_website(url, apify_proxy_password, timeout)
            result["index"] = idx
            results.append(result)

    await asyncio.gather(
        *[process(url, i) for i, url in enumerate(urls)],
        return_exceptions=True,
    )

    # Sort by original order
    results.sort(key=lambda r: r.get("index", 0))

    success = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    return {
        "success": True,
        "data": {
            "total": len(urls),
            "scraped": len(success),
            "failed": len(failed),
            "results": results,
        },
    }
