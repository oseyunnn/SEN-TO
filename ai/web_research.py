"""Controlled, source-hierarchy-enforced external web research for SEN'TO."""

from __future__ import annotations

from datetime import date
import html
import ipaddress
import json
import os
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from ai.validator import is_safe_source_url

OFFICIAL_DOMAINS = (
    "senate.gov.ph",
    "congress.gov.ph",
    "officialgazette.gov.ph",
    "sc.judiciary.gov.ph",
    "elibrary.judiciary.gov.ph",
    "comelec.gov.ph",
    "coa.gov.ph",
    "ombudsman.gov.ph",
    "dbm.gov.ph",
    "pna.gov.ph",
    "pia.gov.ph",
    "gov.ph",
)

CREDIBLE_SECONDARY_DOMAINS = (
    "rappler.com",
    "inquirer.net",
    "philstar.com",
    "mb.com.ph",
    "abs-cbn.com",
    "gmanetwork.com",
    "manilatimes.net",
    "bworldonline.com",
    "verafiles.org",
    "pcij.org",
    "reuters.com",
    "apnews.com",
    "en.wikipedia.org",
)

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: str, limit: int = 900) -> str:
    text = html.unescape(_TAG_RE.sub(" ", value or ""))
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) not in {"Cc", "Cf", "Cs"} or ch == " ")
    text = " ".join(text.split())
    return text[:limit].strip()


def _is_public_https_url(url: str | None) -> bool:
    if not is_safe_source_url(url):
        return False
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"}:
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    except ValueError:
        pass
    return True


def _source_tier(url: str) -> tuple[int, str, str]:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS):
        return (1, "official_record", host)
    if any(host == d or host.endswith("." + d) for d in CREDIBLE_SECONDARY_DOMAINS):
        return (2, "secondary_news", host)
    return (99, "other", host)


class WebResearcher:
    """Controlled external search prioritizing official Philippine government and credible news sources."""

    def __init__(self, enabled: bool | None = None, timeout: float = 7.0, max_results: int = 4):
        if enabled is None:
            env_val = os.environ.get("SENTO_ENABLE_WEB_SEARCH", "true").strip().casefold()
            self.enabled = env_val not in {"0", "false", "no", "off"}
        else:
            self.enabled = bool(enabled)
        self.timeout = timeout
        self.max_results = max(1, min(6, int(max_results)))

    def _search_google_news_rss(self, search_query: str) -> list[tuple[int, str, str, str, str, str, str | None]]:
        url = f"https://news.google.com/rss/search?q={quote_plus(search_query)}&hl=en-PH&gl=PH&ceid=PH:en"
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SENTO-Civic-Research/1.0)"})
            xml_bytes = urlopen(req, timeout=self.timeout).read(524288)
            root = ET.fromstring(xml_bytes)
        except (HTTPError, URLError, TimeoutError, OSError, ET.ParseError):
            return []

        results: list[tuple[int, str, str, str, str, str, str | None]] = []
        for item in root.findall("./channel/item"):
            title = _clean_text(item.findtext("title") or "", limit=220)
            pub_date = _clean_text(item.findtext("pubDate") or "", limit=64) or None
            source_el = item.find("source")
            source_name = _clean_text(source_el.text if source_el is not None else "", limit=100)
            source_url = source_el.attrib.get("url") if source_el is not None else None
            article_link = (item.findtext("link") or "").strip()

            check_url = source_url if _is_public_https_url(source_url) else article_link
            if not _is_public_https_url(check_url):
                continue
            tier, source_type, host = _source_tier(check_url)
            if tier > 2:
                continue
            display_url = article_link if _is_public_https_url(article_link) else check_url
            snippet = f"{title} ({source_name or host}, {pub_date or 'date not stated'})."
            results.append((tier, source_type, source_name or host, display_url, title or host, snippet, pub_date))
        return results

    def _search_wikipedia(self, search_query: str) -> list[tuple[int, str, str, str, str, str, str | None]]:
        url = (
            "https://en.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={quote_plus(search_query)}&format=json&srlimit=2"
        )
        try:
            req = Request(url, headers={"User-Agent": "SENTO-Civic-Research/1.0 (civic-education)"})
            payload = json.loads(urlopen(req, timeout=self.timeout).read(131072).decode("utf-8", errors="ignore"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            return []

        results: list[tuple[int, str, str, str, str, str, str | None]] = []
        for hit in payload.get("query", {}).get("search", []):
            title = _clean_text(hit.get("title") or "", limit=160)
            snippet = _clean_text(hit.get("snippet") or "", limit=600)
            if not title or not snippet:
                continue
            page_url = f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
            results.append((
                2,
                "research_organization",
                "Wikipedia (encyclopedic overview; verify against primary Senate records)",
                page_url,
                title,
                snippet,
                None,
            ))
        return results

    def search(self, query: str, senator: dict | None = None, *, general_civic: bool = False) -> list[dict]:
        if not self.enabled or not query or not query.strip():
            return []

        senator_name = (senator or {}).get("name", "")
        senator_id = (senator or {}).get("id", "general")
        cleaned_query = re.sub(r"\(Context:.*?\)", "", query, flags=re.DOTALL).strip()
        if general_civic:
            news_query = f"{cleaned_query} Philippines Senate"
        else:
            news_query = f"{senator_name} {cleaned_query}".strip()

        candidates: list[tuple[int, str, str, str, str, str, str | None]] = []
        candidates.extend(self._search_google_news_rss(f"site:gov.ph {news_query}"))
        candidates.extend(self._search_google_news_rss(news_query))
        candidates.extend(self._search_wikipedia(news_query))

        seen_titles: set[str] = set()
        deduped: list[tuple[int, str, str, str, str, str, str | None]] = []
        for item in sorted(candidates, key=lambda row: row[0]):
            key = item[4].casefold()[:80]
            if key in seen_titles:
                continue
            seen_titles.add(key)
            deduped.append(item)

        today = date.today().isoformat()
        results: list[dict] = []
        for idx, (tier, source_type, issuer, url, title, snippet, pub_date) in enumerate(deduped[: self.max_results], start=1):
            results.append({
                "chunk_id": f"web-{senator_id}-{idx}",
                "senator_id": senator_id,
                "curation_status": "external_research",
                "verification_status": "external_retrieved",
                "section": "Official external source" if tier == 1 else "Credible external source",
                "relevant_period": pub_date or f"Retrieved {today}",
                "text": snippet,
                "citation_sources": [
                    {
                        "source_id": f"WEB-{idx}",
                        "title": title,
                        "issuing_body": issuer,
                        "source_type": source_type,
                        "source_url": url,
                        "publication_date": pub_date,
                        "retrieved_at": today,
                        "relevant_period": pub_date or f"Retrieved {today}",
                        "locator": "External search result (live retrieval)",
                        "verification_status": "external_retrieved",
                    }
                ],
                "retrieval": {
                    "method": "controlled_web_research",
                    "tier": tier,
                },
            })
        return results
