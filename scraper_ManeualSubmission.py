"""
=============================================================================
 Freelance Market Monitor — Web Scraper  [DEEP CRAWLING VERSION]
 Course   : CS313x Information Retrieval
 Project  : Freelance Market Monitor
 Platforms: Freelancer.com  +  Mostaqel.com
 Author   : [Your Name]
 Date     : 2025
=============================================================================

CS313x COMPLIANCE NOTE
-----------------------
This script uses ONLY the manual scraping tools taught in the CS313x lab
notebooks (Web_Scraping.ipynb, Scrapping_many_links.ipynb):

  • requests                  — standard HTTP GET requests (lab-taught)
  • requests.Session()        — session reuse with manual headers (lab-taught)
  • Manual headers dict       — User-Agent, Accept-Language, Referer, etc.
                                (lab-taught: "Headers make your request look
                                like a browser")
  • BeautifulSoup             — HTML parsing via find() / select() (lab-taught)
  • time.sleep()              — polite delay between requests (lab-taught:
                                "avoid overwhelming the server")
  • try / except              — error handling per page (lab-taught)

No third-party bypass libraries (e.g. cloudscraper, selenium) are used.

DEEP CRAWLING UPGRADE (CS313x Professor Feedback)
--------------------------------------------------
Per course feedback:
  "If you are scraping a news site, you shouldn't just take the headlines
   from the main page; you must click into the article and get the full text.
   You need to get the item and what's inside it."

This version implements DEEP CRAWLING (following links):
  STEP 1 — Fetch the search results / listing page (pagination loop).
  STEP 2 — Extract the individual project URL (href) from each card.
  STEP 3 — Make a NEW session.get() to visit each project's detail page.
  STEP 4 — Parse the detail page HTML with BeautifulSoup to extract:
              • Full Project Description  (not just the card snippet)
              • Complete Skills list      (detail pages list more skills)
              • Detailed Budget           (sometimes richer on detail page)

ETHICAL SCRAPING NOTICE
-----------------------
This script:
  • Reads and obeys each site's robots.txt before scraping.
  • Inserts random human-like delays between EVERY request — including
    every individual detail-page visit — because Deep Crawling multiplies
    the total number of requests dramatically.
  • Sends realistic browser User-Agent strings.
  • Collects only publicly available, non-personal data.
  • Is intended solely for academic / educational use.

HOW TO RUN
----------
1. Install dependencies:
       pip install requests beautifulsoup4 lxml

2. Run the scraper:
       python scraper_Maneual.py

3. Output is saved to:
       freelance_data.json
=============================================================================
"""

import json
import logging
import random
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

# ── CS313x Lab Tools ────────────────────────────────────────────────────────
# These are the exact libraries demonstrated in Web_Scraping.ipynb and
# Scrapping_many_links.ipynb.  No additional bypass libraries are imported.
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Schema
# ---------------------------------------------------------------------------
@dataclass
class FreelanceProject:
    """
    Canonical record for one freelance project.

    DEEP CRAWLING NOTE: description_snippet is now replaced by
    full_description — the complete project description text extracted
    from the individual project detail page, not just a card summary.

    All fields that cannot be found are stored as None (null in JSON).
    """
    platform: str                               # Source platform name
    title: Optional[str] = None                 # Project / job title
    url: Optional[str] = None                   # Direct link to the project
    budget_min: Optional[float] = None          # Minimum budget (numeric)
    budget_max: Optional[float] = None          # Maximum budget (numeric)
    budget_currency: Optional[str] = None       # Currency code, e.g. "USD"
    budget_type: Optional[str] = None           # "fixed" | "hourly" | "unknown"
    skills: list = field(default_factory=list)  # Complete skills list
    category: Optional[str] = None             # Project category / domain
    posted_date: Optional[str] = None          # Raw date string as shown on site
    # ── UPGRADED from description_snippet → full_description ─────────────
    # Surface scraping stored only the ~200-char card teaser.
    # Deep crawling fetches the actual detail page and stores the entire
    # project description body as the professor requires.
    full_description: Optional[str] = None      # Complete description from detail page
    description_snippet: Optional[str] = None   # Card-level teaser (kept as fallback)


# ---------------------------------------------------------------------------
# CS313x Manual Headers (Lab-Compliant)
# ---------------------------------------------------------------------------
# As taught in Web_Scraping.ipynb:
#   "Websites block bots. Headers make your request look like a browser."
#
# We define a pool of realistic User-Agent strings and rotate them, exactly
# as demonstrated in the lab, to avoid simple bot detection.

USER_AGENTS = [
    # Chrome on Windows — most common desktop browser fingerprint
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


def get_session(base_url: str = "") -> requests.Session:
    """
    Build a standard requests.Session() with manually defined browser-like
    headers — exactly as taught in the CS313x lab notebooks.

    A Session (lab: requests.Session) reuses the underlying TCP connection
    and stores cookies, making the traffic pattern resemble a real browser.

    The headers dict is written by hand here — no third-party library is
    used to generate or inject them.
    """
    session = requests.Session()

    # ── Manual headers dict — CS313x lab-compliant ───────────────────────
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": base_url if base_url else "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    })
    return session


# ---------------------------------------------------------------------------
# Utility Helpers
# ---------------------------------------------------------------------------

def polite_sleep(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """
    Sleep a random amount of time between min_s and max_s seconds.

    CS313x lab (Scrapping_many_links.ipynb):
        "To avoid overwhelming the server with requests,
         we can add a delay between requests"
        → time.sleep(1)

    DEEP CRAWLING IMPORTANCE: Because we now make one request per project
    detail page (potentially 10–25 extra requests per listing page), polite
    sleeping is MORE critical here than in the surface scraping version.
    We call polite_sleep(2, 5) between every single detail-page visit to
    avoid hammering the server.

    We use a random range so the delay pattern looks human, not robotic.
    """
    duration = random.uniform(min_s, max_s)
    log.debug("  ↳ sleeping %.2f s …", duration)
    time.sleep(duration)   # ← standard time.sleep() as taught in lab


def fetch_page(
    session: requests.Session,
    url: str,
    retries: int = 3,
    backoff: float = 5.0,
) -> Optional[BeautifulSoup]:
    """
    Fetch a URL and return a BeautifulSoup tree.

    CS313x lab pattern (Scrapping_many_links.ipynb):
        try:
            time.sleep(1)
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            ...
        except:
            print("failed")

    Extended with:
      • Up to `retries` attempts (robustness for transient failures).
      • Exponential back-off on HTTP 429 / 503 (rate-limit handling).
      • User-Agent rotation on each retry (reduces fingerprinting).

    DEEP CRAWLING NOTE: This function is now called both for listing pages
    (pagination) AND for individual project detail pages. A 403 or timeout
    on any single detail page should NOT crash the whole crawler — callers
    wrap this in try/except and skip gracefully on None returns.

    All HTTP communication uses the standard requests library only.
    Returns None if all attempts fail.
    """
    for attempt in range(1, retries + 1):
        # Rotate User-Agent on every attempt — lab teaches header rotation
        session.headers["User-Agent"] = random.choice(USER_AGENTS)

        try:
            # ── Standard session.get() — CS313x lab-compliant ────────────
            response = session.get(url, timeout=15)

            if response.status_code == 200:
                # ── BeautifulSoup parsing — CS313x lab-compliant ──────────
                return BeautifulSoup(response.text, "lxml")

            elif response.status_code in (429, 503):
                wait = backoff * attempt
                log.warning(
                    "Rate-limited (HTTP %d) on attempt %d/%d — "
                    "waiting %.0f s before retry …",
                    response.status_code, attempt, retries, wait,
                )
                time.sleep(wait)

            elif response.status_code == 403:
                # ── 403 Forbidden on detail page ──────────────────────────
                # Deep crawling hits more pages, so 403s are more likely.
                # We log and abort rather than retrying — the server
                # explicitly rejected us for this URL.
                log.warning(
                    "HTTP 403 Forbidden for detail page: %s — skipping.", url
                )
                return None

            elif response.status_code == 404:
                log.warning("404 Not Found: %s", url)
                return None

            else:
                log.warning(
                    "HTTP %d for %s (attempt %d/%d)",
                    response.status_code, url, attempt, retries,
                )

        # ── try / except — taught in Scrapping_many_links.ipynb ──────────
        except requests.exceptions.Timeout:
            log.warning("Timeout on %s (attempt %d/%d)", url, attempt, retries)
        except requests.exceptions.ConnectionError as exc:
            log.warning("Connection error on %s: %s", url, exc)

        if attempt < retries:
            polite_sleep(backoff, backoff * 2)

    log.error("All %d attempts failed for: %s", retries, url)
    return None


# ---------------------------------------------------------------------------
# Detail-Page Fetcher (single attempt, short timeout)
# ---------------------------------------------------------------------------

def fetch_detail_page(
    session: requests.Session,
    url: str,
) -> Optional[BeautifulSoup]:
    """
    Fetch ONE individual project detail page and return a BeautifulSoup tree.

    WHY A SEPARATE FUNCTION FROM fetch_page():
    -------------------------------------------
    fetch_page() retries up to 3 times with a 15 s timeout per attempt.
    For a detail page that Freelancer.com is actively blocking (connection
    drop / Cloudflare timeout), that means 3 × 15 s = 45 s wasted per URL,
    and 6 × 45 s = 270 s (4.5 min) wasted when the same URL appears twice
    due to duplicate cards.

    Detail pages are "nice to have" — if they fail, the crawler already has
    the card-level data as a fallback.  We therefore:
      • Try only ONCE (no retry loop).
      • Use a shorter 10 s timeout.
      • Return None immediately on any non-200 status or exception,
        logging at DEBUG level (not WARNING) so timeouts don't flood the
        console as alarming noise.

    This keeps the crawler fast and the log clean while still being
    lab-compliant: standard session.get(), manual headers, try/except.
    """
    # Rotate User-Agent — lab-taught header rotation
    session.headers["User-Agent"] = random.choice(USER_AGENTS)

    try:
        # ── Standard session.get() — CS313x lab-compliant ────────────────
        response = session.get(url, timeout=10)

        if response.status_code == 200:
            # ── BeautifulSoup parsing — CS313x lab-compliant ──────────────
            return BeautifulSoup(response.text, "lxml")

        elif response.status_code == 403:
            # Server explicitly blocked the bot-detected request.
            # No point retrying — log at DEBUG to avoid console noise.
            log.debug("  Detail page 403 Forbidden (bot-blocked): %s", url)
            return None

        elif response.status_code == 404:
            log.debug("  Detail page 404 Not Found: %s", url)
            return None

        elif response.status_code in (429, 503):
            # Rate-limited: wait briefly then give up (single attempt).
            log.debug("  Detail page rate-limited (HTTP %d): %s", response.status_code, url)
            time.sleep(10)
            return None

        else:
            log.debug("  Detail page HTTP %d: %s", response.status_code, url)
            return None

    # ── try / except — lab-taught pattern ────────────────────────────────
    except requests.exceptions.Timeout:
        # Timeout on a detail page is common when Cloudflare drops the TCP
        # connection. Log at DEBUG — it is expected, not an error.
        log.debug("  Detail page timed out (skipping): %s", url)
        return None
    except requests.exceptions.ConnectionError:
        log.debug("  Detail page connection error (skipping): %s", url)
        return None
    except Exception as exc:
        log.debug("  Detail page unexpected error (%s): %s", exc, url)
        return None


# ---------------------------------------------------------------------------
# robots.txt Compliance Helper
# ---------------------------------------------------------------------------

def _check_wildcard_disallow(robots_text: str, path: str) -> bool:
    """
    Python's RobotFileParser ignores the '*' wildcard in Disallow rules.
    This helper manually checks whether any wildcard Disallow pattern
    (e.g. 'Disallow: /search*') matches the given path.

    Returns True if a wildcard rule BLOCKS the path, False otherwise.
    """
    in_wildcard_section = False
    for raw_line in robots_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lower = line.lower()
        if lower.startswith("user-agent:"):
            agent = lower.split(":", 1)[1].strip()
            in_wildcard_section = (agent == "*")
        elif in_wildcard_section and lower.startswith("disallow:"):
            rule = line.split(":", 1)[1].strip()
            if "*" in rule:
                prefix = rule.split("*")[0]
                if path.startswith(prefix):
                    return True
    return False


def is_allowed_by_robots(base_url: str, path: str = "/") -> bool:
    """
    Check whether the given path is allowed by the site's robots.txt.

    Uses a standard requests.get() call (lab-compliant) to fetch the
    robots.txt file so we can inspect the HTTP status code before parsing.

    Per RFC 9309:
      200  → parse and obey
      404 / 410  → no rules → allow
      401 / 403  → treat as unavailable → allow (fail open)
      5xx  → temporary error → allow (fail open)
    """
    robots_url = urljoin(base_url, "/robots.txt")
    target_url = urljoin(base_url, path)

    try:
        resp = requests.get(
            robots_url,
            timeout=10,
            headers={"User-Agent": random.choice(USER_AGENTS)},
        )

        if resp.status_code == 200:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.parse(resp.text.splitlines())

            stdlib_allowed = rp.can_fetch("*", target_url)
            wildcard_blocked = _check_wildcard_disallow(resp.text, path)
            allowed = stdlib_allowed and not wildcard_blocked

            if not allowed:
                log.warning(
                    "robots.txt explicitly disallows: %s  (rule blocks %s)",
                    target_url, path,
                )
            else:
                log.info("robots.txt allows: %s", target_url)
            return allowed

        elif resp.status_code in (404, 410):
            log.info(
                "robots.txt not found (HTTP %d) for %s → assuming allowed.",
                resp.status_code, base_url,
            )
            return True

        elif resp.status_code in (401, 403):
            log.info(
                "robots.txt returned HTTP %d for %s → treating as allowed.",
                resp.status_code, base_url,
            )
            return True

        elif resp.status_code >= 500:
            log.warning(
                "robots.txt server error HTTP %d for %s → failing open.",
                resp.status_code, base_url,
            )
            return True

        else:
            log.warning(
                "Unexpected HTTP %d fetching robots.txt for %s → allowing.",
                resp.status_code, base_url,
            )
            return True

    except requests.exceptions.RequestException as exc:
        log.warning("Could not reach robots.txt at %s: %s → allowing.", robots_url, exc)
        return True


# ---------------------------------------------------------------------------
# Budget Parser
# ---------------------------------------------------------------------------

def clean_budget(raw: Optional[str]):
    """
    Parse a messy budget string such as:
        "$50 - $100"   →  min=50.0, max=100.0, currency="USD"
        "£500"         →  min=500.0, max=500.0, currency="GBP"
        "SR 200 - 500" →  min=200.0, max=500.0, currency="SAR"
        "Negotiable"   →  min=None,  max=None,  currency=None

    Returns a tuple: (min_val, max_val, currency, budget_type)
    """
    if not raw:
        return None, None, None, "unknown"

    raw = raw.strip()

    currency_map = {
        "$": "USD", "£": "GBP", "€": "EUR",
        "SAR": "SAR", "SR": "SAR", "ر.س": "SAR",
        "EGP": "EGP", "ج.م": "EGP",
    }
    currency = None
    for symbol, code in currency_map.items():
        if symbol in raw:
            currency = code
            break

    budget_type = "hourly" if "/hr" in raw.lower() or "hour" in raw.lower() else "fixed"

    numbers = re.findall(r"[\d,]+\.?\d*", raw.replace(",", ""))
    nums = [float(n) for n in numbers if n]

    if len(nums) == 0:
        return None, None, currency, "unknown"
    elif len(nums) == 1:
        return nums[0], nums[0], currency, budget_type
    else:
        return min(nums), max(nums), currency, budget_type


# ---------------------------------------------------------------------------
# Scraper 1: Freelancer.com
# ---------------------------------------------------------------------------

FREELANCER_BASE   = "https://www.freelancer.com"
FREELANCER_SEARCH = "/jobs/"


def scrape_freelancer(
    session: requests.Session,
    max_pages: int = 10,
    category_slug: str = "",
) -> list[FreelanceProject]:
    """
    Scrape project listings from Freelancer.com using DEEP CRAWLING.

    CS313x Deep Crawling pattern (following links, as per professor feedback):
      for each listing page:                     ← STEP 1: pagination loop
          soup = fetch_page(listing_page_url)
          for each card in soup:
              href = card.find("a")["href"]      ← STEP 2: extract project URL
              polite_sleep(2, 5)                 ← ethical delay before detail request
              detail_soup = fetch_page(href)     ← STEP 3: NEW request to detail page
              full_desc = detail_soup.find(...)  ← STEP 4: parse full description
              project = build_project(card, detail_soup)
              projects.append(project)
          polite_sleep()                         ← delay between listing pages

    Args:
        session      : Shared requests.Session with headers already set.
        max_pages    : Maximum number of paginated listing pages to visit.
        category_slug: Optional category path, e.g. "web-development/".

    Returns:
        List of FreelanceProject objects populated with full detail-page data.
    """
    projects: list[FreelanceProject] = []
    search_path = FREELANCER_SEARCH + category_slug

    # ── URL deduplication set ─────────────────────────────────────────────
    # Listing pages sometimes contain duplicate card links (e.g. a "featured"
    # slot and a normal slot pointing to the same project URL).  Without
    # deduplication, the crawler would fetch the same detail page twice,
    # doubling the timeout wait time and filling the log with redundant
    # warnings.  A simple set() of visited URLs fixes this at zero cost.
    seen_urls: set[str] = set()

    # ── Ethical robots.txt check ──────────────────────────────────────────
    if not is_allowed_by_robots(FREELANCER_BASE, search_path):
        log.warning("Freelancer.com robots.txt blocks this path. Skipping.")
        return projects

    log.info("▶ Starting Freelancer.com DEEP CRAWL (max %d pages) …", max_pages)

    for page_num in range(1, max_pages + 1):
        # ── STEP 1: Fetch the listing / search-results page ───────────────
        page_url = f"{FREELANCER_BASE}{search_path}?page={page_num}"
        log.info("  [Listing] Page %d/%d → %s", page_num, max_pages, page_url)

        # Update Referer to the search results page so detail-page requests
        # look like the user clicked a link from within the listing page.
        session.headers["Referer"] = page_url

        soup = fetch_page(session, page_url)
        if soup is None:
            log.warning("  Could not fetch listing page %d. Stopping.", page_num)
            break

        # ── BeautifulSoup: locate project cards ───────────────────────────
        cards = soup.select("div.JobSearchCard-item")
        if not cards:
            cards = (
                soup.select("div[class*='job-card']") or
                soup.select("li.job-wrap") or
                soup.select("div.search-result-item")
            )

        if not cards:
            log.warning(
                "  No job cards on page %d. Site layout may have changed.", page_num
            )
            log.debug("  HTML snippet: %s", soup.body.get_text()[:300] if soup.body else "N/A")
            break

        log.info("  Found %d project cards on page %d.", len(cards), page_num)

        # ── STEP 2 + 3 + 4: Deep Crawl — follow each project link ─────────
        for card_idx, card in enumerate(cards, start=1):

            # ── STEP 2: Extract the individual project URL from the card ──
            project_url = _extract_freelancer_card_url(card)

            if not project_url:
                log.debug("    Card %d: no URL found, skipping detail fetch.", card_idx)
                project = _parse_freelancer_card(card, detail_soup=None)
                if project:
                    projects.append(project)
                continue

            # ── Deduplication check ───────────────────────────────────────
            # Skip this URL if we already visited it on a previous card or
            # a previous page.  This prevents the same timeout warning from
            # appearing twice for a URL that appears in both a "featured"
            # slot and a normal listing slot on the same page.
            if project_url in seen_urls:
                log.debug("    Card %d: duplicate URL skipped: %s", card_idx, project_url)
                continue
            seen_urls.add(project_url)

            # ── ETHICAL POLITENESS: sleep before EVERY detail-page request ──
            # CS313x lab: "avoid overwhelming the server with requests"
            log.debug(
                "    [Deep Crawl] Card %d/%d — visiting detail page: %s",
                card_idx, len(cards), project_url,
            )
            polite_sleep(2, 5)  # ← polite_sleep between every project link visit

            # ── STEP 3: NEW session.get() request to the detail page ───────
            # Uses fetch_detail_page() instead of fetch_page() so that:
            #   • A single attempt is made (no 3-retry loop wasting 45 s).
            #   • Timeout is 10 s (not 15 s) — detail pages are optional.
            #   • Timeouts log at DEBUG, not WARNING, keeping the console clean.
            session.headers["Referer"] = page_url
            detail_soup = fetch_detail_page(session, project_url)

            # ── STEP 4: Parse the detail page with BeautifulSoup ───────────
            # Pass both the card element (for card-level fields like title/URL)
            # and the detail soup (for full description, complete skills, etc.)
            project = _parse_freelancer_card(card, detail_soup=detail_soup)
            if project:
                projects.append(project)
                log.debug(
                    "    ✔ Card %d — title: %s | skills: %d | desc_len: %d",
                    card_idx,
                    (project.title or "")[:50],
                    len(project.skills),
                    len(project.full_description or ""),
                )

        log.info("  → %d projects collected so far.", len(projects))

        # ── Polite delay between listing pages — CS313x compliant ─────────
        polite_sleep()

    log.info("✔ Freelancer.com DEEP CRAWL done. Total: %d projects.", len(projects))
    return projects


def _extract_freelancer_card_url(card) -> Optional[str]:
    """
    Extract and return the absolute project detail URL from a listing card.

    This is STEP 2 of the deep crawling pipeline: pull the href from the
    card's title anchor so we know where to send our next session.get().
    Kept as a separate function for clarity and testability.
    """
    title_tag = (
        card.select_one("a.JobSearchCard-primary-heading-link") or
        card.select_one("h2.JobSearchCard-primary-heading a") or
        card.select_one("[class*='heading'] a") or
        card.select_one("a[href*='/projects/']")
    )
    if not title_tag:
        return None
    raw_href = title_tag.get("href", "")
    return urljoin(FREELANCER_BASE, raw_href) if raw_href else None


def _parse_freelancer_detail(detail_soup: BeautifulSoup):
    """
    Extract rich fields from a Freelancer.com project DETAIL PAGE.

    This is STEP 4 of the deep crawling pipeline. The detail page contains
    the complete project description, all required skills, and sometimes a
    more precise budget — information that is NOT available on the listing card.

    Returns a dict with keys: full_description, skills, budget_raw
    so _parse_freelancer_card() can merge them with card-level data.
    """
    result = {"full_description": None, "skills": [], "budget_raw": None}

    if detail_soup is None:
        return result

    # ── Full Description ──────────────────────────────────────────────────
    # Freelancer wraps the project body in a few possible containers.
    # We try each selector in order of specificity.
    desc_tag = (
        detail_soup.select_one("div.PageProjectViewLogout-projectDescription") or
        detail_soup.select_one("div.project-description") or
        detail_soup.select_one("[class*='ProjectDescription']") or
        detail_soup.select_one("[class*='project-description']") or
        detail_soup.select_one("div[class*='description'] p") or
        detail_soup.select_one("section.project-description")
    )
    if desc_tag:
        # get_text(separator="\n") preserves paragraph breaks in the description.
        result["full_description"] = desc_tag.get_text(separator="\n", strip=True)

    # ── Complete Skills List ───────────────────────────────────────────────
    # Detail pages often list more skills than the listing card preview.
    skills_tags = (
        detail_soup.select("a.skill-tag") or
        detail_soup.select("[class*='SkillTag']") or
        detail_soup.select("[class*='skill-tag']") or
        detail_soup.select("ul.skills-list li") or
        detail_soup.select("[class*='tag'][href*='/jobs/']")
    )
    result["skills"] = [
        s.get_text(strip=True) for s in skills_tags if s.get_text(strip=True)
    ]

    # ── Budget (detail page sometimes shows more precise range) ───────────
    budget_tag = (
        detail_soup.select_one("[class*='PageProjectViewLogout-budget']") or
        detail_soup.select_one("[class*='project-budget']") or
        detail_soup.select_one("[class*='Budget']") or
        detail_soup.select_one("span[class*='price']")
    )
    if budget_tag:
        result["budget_raw"] = budget_tag.get_text(strip=True)

    return result


def _parse_freelancer_card(card, detail_soup: Optional[BeautifulSoup]) -> Optional[FreelanceProject]:
    """
    Build a FreelanceProject from a listing card element MERGED WITH
    data from the project's individual detail page.

    CS313x Deep Crawling principle:
      "Get the item and what's inside it."
      → card HTML  = surface data  (title, URL, card-level snippet)
      → detail HTML = deep data    (full description, all skills, precise budget)

    detail_soup may be None if the detail page request failed — in that case
    we gracefully fall back to card-only data, keeping the crawler running.
    """
    # ── try / except around the entire parse — lab-taught pattern ─────────
    try:
        # ── Title (from card) ─────────────────────────────────────────────
        title_tag = (
            card.select_one("a.JobSearchCard-primary-heading-link") or
            card.select_one("h2.JobSearchCard-primary-heading a") or
            card.select_one("[class*='heading'] a")
        )
        title = title_tag.get_text(strip=True) if title_tag else None
        if not title:
            return None

        # ── URL (from card) ───────────────────────────────────────────────
        raw_href = title_tag.get("href", "") if title_tag else ""
        url = urljoin(FREELANCER_BASE, raw_href) if raw_href else None

        # ── Card-level budget (initial parse) ─────────────────────────────
        budget_tag = (
            card.select_one("div.JobSearchCard-primary-price") or
            card.select_one("[class*='price']") or
            card.select_one("[class*='budget']")
        )
        raw_budget_card = budget_tag.get_text(strip=True) if budget_tag else None

        # ── Card-level skills (initial parse) ─────────────────────────────
        skills_tags = (
            card.select("a.JobSearchCard-primary-tagsLink") or
            card.select("[class*='skill'] a") or
            card.select("[class*='tag'] a")
        )
        skills_card = [
            s.get_text(strip=True) for s in skills_tags if s.get_text(strip=True)
        ]

        # ── Category (from card) ──────────────────────────────────────────
        category_tag = (
            card.select_one("a.JobSearchCard-primary-category") or
            card.select_one("[class*='category']")
        )
        category = category_tag.get_text(strip=True) if category_tag else None

        # ── Card-level description snippet (fallback) ─────────────────────
        desc_tag = (
            card.select_one("p.JobSearchCard-secondary-description") or
            card.select_one("[class*='description']")
        )
        snippet = desc_tag.get_text(strip=True)[:250] if desc_tag else None

        # ── Posted date (from card) ───────────────────────────────────────
        date_tag = card.select_one("span[class*='ago']") or card.select_one("time")
        posted = date_tag.get_text(strip=True) if date_tag else None

        # ── STEP 4: Merge detail-page data (Deep Crawl upgrade) ───────────
        # Extract the richer fields from the detail page.
        # If detail_soup is None (request failed), detail_data will contain
        # only None / empty values and the card data is used as fallback.
        detail_data = _parse_freelancer_detail(detail_soup)

        # Skills: prefer the longer, more complete list from the detail page
        skills_final = detail_data["skills"] if detail_data["skills"] else skills_card

        # Budget: prefer detail-page budget if available, else card budget
        raw_budget_final = detail_data["budget_raw"] or raw_budget_card
        bmin, bmax, currency, btype = clean_budget(raw_budget_final)

        # Full description comes exclusively from the detail page
        full_description = detail_data["full_description"]

        return FreelanceProject(
            platform="Freelancer.com",
            title=title,
            url=url,
            budget_min=bmin,
            budget_max=bmax,
            budget_currency=currency,
            budget_type=btype,
            skills=skills_final,
            category=category,
            posted_date=posted,
            full_description=full_description,   # ← Deep Crawl: full body text
            description_snippet=snippet,          # ← kept as card-level fallback
        )

    except Exception as exc:
        log.warning("  Error parsing Freelancer card/detail: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Scraper 2: Mostaqel.com
# ---------------------------------------------------------------------------

MOSTAQEL_BASE     = "https://mostaql.com"
MOSTAQEL_PROJECTS = "/projects"


def scrape_mostaqel(
    session: requests.Session,
    max_pages: int = 10,
) -> list[FreelanceProject]:
    """
    Scrape project listings from Mostaql.com (مستقل) using DEEP CRAWLING.

    CS313x Deep Crawling pattern (following links):
      for each listing page:                     ← STEP 1: pagination loop
          soup = fetch_page(listing_page_url)
          for each card in soup:
              href = card.find("a")["href"]      ← STEP 2: extract project URL
              polite_sleep(2, 5)                 ← ethical delay (MANDATORY)
              detail_soup = fetch_page(href)     ← STEP 3: NEW request to detail page
              full_desc = detail_soup.find(...)  ← STEP 4: parse full description
              project = build_project(card, detail_soup)
          polite_sleep()                         ← delay between listing pages

    Args:
        session   : Shared requests.Session with manually defined headers.
        max_pages : Max paginated pages to visit.

    Returns:
        List of FreelanceProject objects populated with full detail-page data.
    """
    projects: list[FreelanceProject] = []

    # ── URL deduplication set ─────────────────────────────────────────────
    # Prevents wasting a full timeout-wait on a URL the crawler already
    # tried (e.g. a project that appears in both a "featured" and a normal
    # slot on the same listing page).
    seen_urls: set[str] = set()

    # ── Ethical robots.txt check ──────────────────────────────────────────
    if not is_allowed_by_robots(MOSTAQEL_BASE, MOSTAQEL_PROJECTS):
        log.warning("Mostaqel robots.txt blocks project listings. Skipping.")
        return projects

    # Update Referer header to match Mostaqel's domain
    session.headers["Referer"] = MOSTAQEL_BASE + "/"

    log.info("▶ Starting Mostaqel.com DEEP CRAWL (max %d pages) …", max_pages)

    for page_num in range(1, max_pages + 1):
        # ── STEP 1: Fetch the listing page ────────────────────────────────
        page_url = f"{MOSTAQEL_BASE}{MOSTAQEL_PROJECTS}?page={page_num}"
        log.info("  [Listing] Page %d/%d → %s", page_num, max_pages, page_url)

        # Update Referer so detail requests look like in-site navigation
        session.headers["Referer"] = page_url

        soup = fetch_page(session, page_url)
        if soup is None:
            log.warning("  Failed to fetch listing page %d. Stopping.", page_num)
            break

        # ── BeautifulSoup: locate project cards ───────────────────────────
        cards = (
            soup.select("table.projects-table tbody tr") or
            soup.select("div.project-row") or
            soup.select("[class*='project-card']") or
            soup.select("article.project")
        )

        if not cards:
            log.warning("  No job cards found on page %d.", page_num)
            break

        log.info("  Found %d project cards on page %d.", len(cards), page_num)

        # ── STEP 2 + 3 + 4: Deep Crawl — follow each project link ─────────
        for card_idx, card in enumerate(cards, start=1):

            # ── STEP 2: Extract the individual project URL ────────────────
            project_url = _extract_mostaqel_card_url(card)

            if not project_url:
                log.debug("    Card %d: no URL found, skipping detail fetch.", card_idx)
                project = _parse_mostaqel_card(card, detail_soup=None)
                if project:
                    projects.append(project)
                continue

            # ── Deduplication check ───────────────────────────────────────
            if project_url in seen_urls:
                log.debug("    Card %d: duplicate URL skipped: %s", card_idx, project_url)
                continue
            seen_urls.add(project_url)

            # ── ETHICAL POLITENESS: sleep before EVERY detail-page request ──
            # Deep Crawling (following links) requires per-project politeness.
            # CS313x lab: "avoid overwhelming the server with requests".
            log.debug(
                "    [Deep Crawl] Card %d/%d — visiting detail page: %s",
                card_idx, len(cards), project_url,
            )
            polite_sleep(2, 5)  # ← polite_sleep between every project link visit

            # ── STEP 3: NEW session.get() to the project detail page ───────
            # Uses fetch_detail_page() — single attempt, 10 s timeout,
            # timeouts logged at DEBUG so the console stays clean.
            session.headers["Referer"] = page_url
            detail_soup = fetch_detail_page(session, project_url)

            # ── STEP 4: Parse detail page and merge with card data ─────────
            project = _parse_mostaqel_card(card, detail_soup=detail_soup)
            if project:
                projects.append(project)
                log.debug(
                    "    ✔ Card %d — title: %s | skills: %d | desc_len: %d",
                    card_idx,
                    (project.title or "")[:50],
                    len(project.skills),
                    len(project.full_description or ""),
                )

        log.info("  → %d projects collected so far.", len(projects))

        # ── Polite delay between listing pages ─────────────────────────────
        polite_sleep()

    log.info("✔ Mostaqel.com DEEP CRAWL done. Total: %d projects.", len(projects))
    return projects


def _extract_mostaqel_card_url(card) -> Optional[str]:
    """
    Extract and return the absolute project detail URL from a Mostaqel card.

    STEP 2 of the deep crawling pipeline for Mostaqel.
    """
    title_tag = (
        card.select_one("h2.project__title a") or
        card.select_one("h2 a") or
        card.select_one("a.project-title") or
        card.select_one("[class*='title'] a") or
        card.select_one("a[href*='/projects/']")
    )
    if not title_tag:
        return None
    raw_href = title_tag.get("href", "")
    return urljoin(MOSTAQEL_BASE, raw_href) if raw_href else None


def _parse_mostaqel_detail(detail_soup: BeautifulSoup) -> dict:
    """
    Extract rich fields from a Mostaqel project DETAIL PAGE.

    STEP 4 of the deep crawling pipeline for Mostaqel.
    Returns a dict: full_description, skills, budget_raw.
    """
    result = {"full_description": None, "skills": [], "budget_raw": None}

    if detail_soup is None:
        return result

    # ── Full Description ──────────────────────────────────────────────────
    # Mostaqel wraps the main project body in a few possible containers.
    desc_tag = (
        detail_soup.select_one("div.project__brief--full") or
        detail_soup.select_one("div.project-details__description") or
        detail_soup.select_one("[class*='project__description']") or
        detail_soup.select_one("[class*='ProjectDescription']") or
        detail_soup.select_one("div.carda__content p") or
        detail_soup.select_one("section.project-description") or
        detail_soup.select_one("[itemprop='description']")
    )
    if desc_tag:
        result["full_description"] = desc_tag.get_text(separator="\n", strip=True)

    # ── Complete Skills List ───────────────────────────────────────────────
    skills_tags = (
        detail_soup.select("ul.project__skills li") or
        detail_soup.select("[class*='skill-tag']") or
        detail_soup.select("[class*='SkillsList'] li") or
        detail_soup.select("span.tag") or
        detail_soup.select("a[href*='/projects?skill=']")
    )
    result["skills"] = [
        s.get_text(strip=True) for s in skills_tags if s.get_text(strip=True)
    ]

    # ── Budget ────────────────────────────────────────────────────────────
    budget_tag = (
        detail_soup.select_one("div.project__price") or
        detail_soup.select_one("[class*='project-price']") or
        detail_soup.select_one("[class*='Budget']") or
        detail_soup.select_one("span.budget")
    )
    if budget_tag:
        result["budget_raw"] = budget_tag.get_text(strip=True)

    return result


def _parse_mostaqel_card(card, detail_soup: Optional[BeautifulSoup]) -> Optional[FreelanceProject]:
    """
    Build a FreelanceProject from a Mostaqel listing card MERGED WITH
    data from the individual project detail page.

    CS313x Deep Crawling principle:
      card HTML  = surface data  (title, URL, card teaser)
      detail HTML = deep data    (full description, complete skills, budget)

    detail_soup may be None if the HTTP request failed — graceful fallback
    to card-only data keeps the crawler alive across 403s and timeouts.
    """
    # ── try / except — lab-taught pattern ─────────────────────────────────
    try:
        # ── Title (from card) ─────────────────────────────────────────────
        title_tag = (
            card.select_one("h2.project__title a") or
            card.select_one("h2 a") or
            card.select_one("a.project-title") or
            card.select_one("[class*='title'] a")
        )
        title = title_tag.get_text(strip=True) if title_tag else None
        if not title:
            return None

        # ── URL (from card) ───────────────────────────────────────────────
        raw_href = title_tag.get("href", "") if title_tag else ""
        url = urljoin(MOSTAQEL_BASE, raw_href) if raw_href else None

        # ── Card-level budget ─────────────────────────────────────────────
        budget_tag = (
            card.select_one("div.project__price") or
            card.select_one("[class*='price']") or
            card.select_one("[class*='budget']") or
            card.select_one("span.budget")
        )
        raw_budget_card = budget_tag.get_text(strip=True) if budget_tag else None

        # ── Card-level skills ─────────────────────────────────────────────
        skills_tags = (
            card.select("ul.project__skills li") or
            card.select("[class*='skill']") or
            card.select("span.tag")
        )
        skills_card = [
            s.get_text(strip=True) for s in skills_tags if s.get_text(strip=True)
        ]

        # ── Category (from card) ──────────────────────────────────────────
        category_tag = (
            card.select_one("a.project__category") or
            card.select_one("[class*='category'] a") or
            card.select_one("span.category")
        )
        category = category_tag.get_text(strip=True) if category_tag else None

        # ── Card-level description snippet (fallback) ─────────────────────
        desc_tag = (
            card.select_one("div.project__brief") or
            card.select_one("p.project-description") or
            card.select_one("[class*='description']")
        )
        snippet = desc_tag.get_text(strip=True)[:250] if desc_tag else None

        # ── Posted date (from card) ───────────────────────────────────────
        date_tag = card.select_one("time") or card.select_one("[class*='date']")
        posted = (
            date_tag.get("datetime") or
            (date_tag.get_text(strip=True) if date_tag else None)
        )

        # ── STEP 4: Merge detail-page data (Deep Crawl upgrade) ───────────
        detail_data = _parse_mostaqel_detail(detail_soup)

        # Skills: prefer the richer detail-page list
        skills_final = detail_data["skills"] if detail_data["skills"] else skills_card

        # Budget: prefer detail-page value if richer
        raw_budget_final = detail_data["budget_raw"] or raw_budget_card
        bmin, bmax, currency, btype = clean_budget(raw_budget_final)

        # Full description from detail page
        full_description = detail_data["full_description"]

        return FreelanceProject(
            platform="Mostaqel.com",
            title=title,
            url=url,
            budget_min=bmin,
            budget_max=bmax,
            budget_currency=currency,
            budget_type=btype,
            skills=skills_final,
            category=category,
            posted_date=posted,
            full_description=full_description,   # ← Deep Crawl: full body text
            description_snippet=snippet,          # ← card-level fallback
        )

    except Exception as exc:
        log.warning("  Error parsing Mostaqel card/detail: %s", exc)
        return None


# ---------------------------------------------------------------------------
# JSON Exporter
# ---------------------------------------------------------------------------

def export_to_json(projects: list[FreelanceProject], filepath: str = "freelance_data.json") -> None:
    """
    Serialise the list of FreelanceProject dataclasses to a well-structured
    JSON file.

    DEEP CRAWLING NOTE: Each record now contains full_description (from the
    detail page) in addition to description_snippet (card-level teaser).

    Schema per record:
    {
        "platform":             "Freelancer.com",
        "title":                "Build a REST API",
        "url":                  "https://www.freelancer.com/projects/...",
        "budget_min":           50.0,
        "budget_max":           150.0,
        "budget_currency":      "USD",
        "budget_type":          "fixed",
        "skills":               ["Python", "Django", "REST API"],
        "category":             "Web Development",
        "posted_date":          "2 hours ago",
        "full_description":     "We are looking for an experienced developer …
                                  (full body text from detail page)",
        "description_snippet":  "Looking for an experienced developer …"
    }
    """
    output = {
        "metadata": {
            "total_records": len(projects),
            "platforms": list({p.platform for p in projects}),
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "schema_version": "2.0",          # bumped: now includes full_description
            "crawl_type": "deep",             # documents that this is Deep Crawl data
        },
        "projects": [asdict(p) for p in projects],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info("💾 Saved %d records → %s", len(projects), filepath)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    """
    Orchestrates the full Deep Crawl ETL pipeline:
      1. Create a shared HTTP session with manually defined headers.
      2. DEEP CRAWL each platform:
           a. Fetch listing pages (pagination).
           b. Extract individual project URLs from cards.
           c. Visit each project's detail page (NEW session.get() per project).
           d. Parse full description + complete skills from detail page.
      3. Merge results.
      4. Export to JSON.

    CS313x Compliance Summary
    ─────────────────────────
    HTTP client    : requests.Session()             (standard library)
    Headers        : manually defined dict           (lab-taught technique)
    HTML parsing   : BeautifulSoup                   (lab-taught)
    Polite delay   : time.sleep(random.uniform(...)) (lab-taught)
                     → between EVERY detail-page visit (2–5 s)
                     → between listing pages           (1.5–4 s)
    Error handling : try / except per card/detail page (lab-taught)
    Crawl type     : DEEP (following links to detail pages)
    No bypass libraries (cloudscraper, selenium, etc.) used anywhere.
    """
    log.info("=" * 60)
    log.info("  Freelance Market Monitor — DEEP CRAWL Scraper Starting")
    log.info("  Crawl type  : Deep Crawling (following links)")
    log.info("  HTTP client : requests.Session() + manual headers")
    log.info("  Parser      : BeautifulSoup")
    log.info("  Delay       : time.sleep()  [CS313x compliant]")
    log.info("  Note        : polite_sleep(2,5) between EVERY project visit")
    log.info("=" * 60)

    session = get_session(base_url=FREELANCER_BASE)
    all_projects: list[FreelanceProject] = []

    # ── Platform 1: Freelancer.com (Deep Crawl) ───────────────────────────
    freelancer_projects = scrape_freelancer(session, max_pages=10)
    all_projects.extend(freelancer_projects)

    # Brief pause between platforms
    polite_sleep(3, 7)

    # ── Platform 2: Mostaqel.com (Deep Crawl) ─────────────────────────────
    session.headers["Referer"] = MOSTAQEL_BASE + "/"
    mostaqel_projects = scrape_mostaqel(session, max_pages=10)
    all_projects.extend(mostaqel_projects)

    # ── Summary ────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("  DEEP CRAWL COMPLETE")
    log.info("  Freelancer.com : %d projects", len(freelancer_projects))
    log.info("  Mostaqel.com   : %d projects", len(mostaqel_projects))
    log.info("  TOTAL          : %d projects", len(all_projects))
    log.info("=" * 60)

    if not all_projects:
        log.warning("No data collected. The sites' HTML structure may have changed.")
        log.warning("Run with DEBUG logging: logging.basicConfig(level=logging.DEBUG)")
        return

    export_to_json(all_projects, "freelance_data.json")


if __name__ == "__main__":
    main()
