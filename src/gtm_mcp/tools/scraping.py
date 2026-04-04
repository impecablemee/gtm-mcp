"""Website scraping tool — httpx + BeautifulSoup, optional Apify proxy."""
import re
import random
from typing import Optional

import httpx
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

MAX_TEXT_LENGTH = 50_000
BINARY_THRESHOLD = 0.15


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["nav", "header", "footer", "aside", "script", "style", "noscript"]):
        tag.decompose()
    # Remove cookie banners
    for el in soup.find_all(attrs={"class": re.compile(r"cookie|consent|banner|popup", re.I)}):
        el.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:MAX_TEXT_LENGTH]


def _is_binary(content: bytes) -> bool:
    if not content:
        return False
    sample = content[:8192]
    non_printable = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))
    return non_printable / len(sample) > BINARY_THRESHOLD


async def scrape_website(
    url: str,
    apify_proxy_password: Optional[str] = None,
    timeout: float = 15.0,
) -> dict:
    """Scrape a website and return cleaned text. No credits."""
    url = _normalize_url(url)
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    proxy = None
    if apify_proxy_password:
        proxy = f"http://auto:{apify_proxy_password}@proxy.apify.com:8000"

    errors = []
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                proxy=proxy,
                verify=True,
            ) as client:
                resp = await client.get(url, headers=headers)

            if _is_binary(resp.content):
                return {"success": False, "error": "Binary content detected", "url": url}

            text = _clean_html(resp.text)
            return {
                "success": True,
                "url": url,
                "text": text,
                "status_code": resp.status_code,
                "text_length": len(text),
            }
        except httpx.ConnectError:
            # Try HTTP fallback on SSL error
            if url.startswith("https://") and attempt == 0:
                url = url.replace("https://", "http://", 1)
                continue
            errors.append("Connection error")
        except httpx.TimeoutException:
            errors.append(f"Timeout ({timeout}s)")
        except Exception as e:
            errors.append(str(e))

        # Exponential backoff
        if attempt < 2:
            import asyncio
            await asyncio.sleep(2 ** (attempt + 1))

    return {"success": False, "error": "; ".join(errors), "url": url}
