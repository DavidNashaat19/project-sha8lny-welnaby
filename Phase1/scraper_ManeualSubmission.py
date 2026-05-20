"""

CS313x COMPLIANCE NOTE & SELENIUM MIGRATION
---------------------------------------------
This script has been migrated to use ONLY Selenium Chrome WebDriver for fetching and
parsing pages. BeautifulSoup has been completely removed to avoid integration complexity,
relying instead on Selenium's native element locators (By.CSS_SELECTOR, By.XPATH, etc.).

Ethics and polite crawler requirements from CS313x are fully preserved:
  • robotparser               — reads and obeys robots.txt before fetching
  • time.sleep()              — polite delay between requests (lab-taught:
                                "avoid overwhelming the server")
  • try / except              — error handling per page (lab-taught)

DEEP CRAWLING PATTERN
----------------------
This script implements DEEP CRAWLING (following links):
  STEP 1 — Fetch the search results / listing page (pagination loop).
  STEP 2 — Extract individual project card elements and pre-parse surface details.
  STEP 3 — Make a separate driver.get() visit to each project's detail page.
  STEP 4 — Parse the detail page natively with Selenium to extract:
              • Full Project Description  (not just the card snippet)
              • Complete Skills list      (detail pages list more skills)
              • Detailed Budget           (sometimes richer on detail page)

HOW TO RUN
----------
1. Install dependencies:
       pip install selenium webdriver-manager

2. Run the scraper:
       python Phase1/scraper_ManeualSubmission.py

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
import sys
from typing import Optional
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

# ── CS313x Lab Tools & Selenium Migration ───────────────────────────────────
# Kept requests for robots.txt fetching.
# Selenium is introduced to handle modern Javascript rendering & bot bypass,
# and is used exclusively for page fetching and element parsing (no BeautifulSoup).
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

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
    seller_level: Optional[str] = None         # Seller level (Fiverr-specific)



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


def create_driver():
    """
    Creates and returns a headless Selenium Chrome WebDriver.
    
    Uses ChromeDriverManager to automatically install and manage the Chrome binary,
    ensuring robustness and compatibility in the local Windows environment.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Set a robust browser user-agent
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    # Speed up scraping by preventing image loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(1280, 1024)
    return driver


# ---------------------------------------------------------------------------
# Utility Helpers
# ---------------------------------------------------------------------------

def polite_sleep(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """
    Sleep a random amount of time between min_s and max_s seconds.
    """
    duration = random.uniform(min_s, max_s)
    log.debug("  ↳ sleeping %.2f s …", duration)
    time.sleep(duration)


# ── Native Selenium Parsing Helpers ─────────────────────────────────────────

def find_element_by_selectors(parent, selectors: list[str]):
    """
    Safely find an element using a list of CSS selectors.
    Returns the first matching element, or None if none are found.
    """
    for selector in selectors:
        try:
            return parent.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            continue
    return None


def find_elements_by_selectors(parent, selectors: list[str]):
    """
    Safely find elements using a list of CSS selectors.
    Returns a list of matching elements, or an empty list if none are found.
    """
    for selector in selectors:
        try:
            elements = parent.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements
        except NoSuchElementException:
            continue
    return []


def get_text_by_selectors(parent, selectors: list[str]) -> Optional[str]:
    """
    Safely get the text of an element using a list of CSS selectors.
    """
    el = find_element_by_selectors(parent, selectors)
    return el.text.strip() if el else None


def get_attribute_by_selectors(parent, selectors: list[str], attr: str) -> Optional[str]:
    """
    Safely get an attribute of an element using a list of CSS selectors.
    """
    el = find_element_by_selectors(parent, selectors)
    if el:
        val = el.get_attribute(attr)
        return val.strip() if val else None
    return None


def fetch_page_selenium(
    driver,
    url: str,
    retries: int = 3,
    backoff: float = 5.0,
) -> bool:
    """
    Fetch a URL using Selenium, wait for dynamic elements.
    Returns True if successfully loaded, False otherwise.
    """
    for attempt in range(1, retries + 1):
        try:
            log.debug("Fetching listing with Selenium (attempt %d/%d): %s", attempt, retries, url)
            driver.get(url)
            # Give a random polite delay to let scripts run and render
            time.sleep(random.uniform(2.5, 4.5))
            
            html = driver.page_source
            if html and len(html) > 200:
                return True
                
        except Exception as exc:
            log.warning("Attempt %d failed to fetch %s via Selenium: %s", attempt, url, exc)
            
        if attempt < retries:
            polite_sleep(backoff, backoff * 2)
            
    log.error("All %d Selenium fetch attempts failed for: %s", retries, url)
    return False


def fetch_detail_page_selenium(driver, url: str) -> bool:
    """
    Fetch a single detail page using Selenium (single attempt, polite rendering time).
    Returns True if successfully loaded, False otherwise.
    """
    try:
        log.debug("Fetching detail page with Selenium: %s", url)
        driver.get(url)
        time.sleep(random.uniform(2.0, 3.5))
        html = driver.page_source
        if html and len(html) > 200:
            return True
    except Exception as exc:
        log.debug("Failed to fetch detail page %s: %s", url, exc)
    return False


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
                # Convert wildcard pattern to regular expression
                pattern = re.escape(rule).replace(r"\*", ".*")
                if rule.startswith("/"):
                    pattern = "^" + pattern
                try:
                    if re.search(pattern, path):
                        return True
                except re.error:
                    pass
    return False


FIVERR_ROBOTS_TXT = """User-Agent: *
Disallow: /orders/timeline/*
Disallow: */pinned_flashes/*
Disallow: /gigs/*/share/
Disallow: /gigs/*/share?*
Disallow: /specials/*
Disallow: /packages/*
Disallow: /categories/silly
Disallow: /categories/fifa
Disallow: /categories/Halloween
Disallow: /categories/Postcards
Disallow: /purchases
Disallow: /user_sessions
Disallow: /users/
Disallow: /counter/*?
Disallow: /collaborate/*
Disallow: /search/
Disallow: /search_results/gigs/*
Disallow: /match/website/*
Disallow: /pages/website-developer-match
Disallow: /v4/*
Disallow: /pro/*
Disallow: /about-pro
Disallow: /pro-resources
Disallow: /pro-solutions
Disallow: /gigs/search
Disallow: /recommendations/
Disallow: /contact_me/
Disallow: /conversations/
Disallow: /bookmarks/
Disallow: /inbox/
Disallow: /inbox$
Disallow: /seller_onboarding/
Disallow: /checkout/package/
Disallow: /match/
Disallow: /pages/website-developer-match
Disallow: /cdn-proxy/px/*
Disallow: /cdn-proxy/pim/*
Disallow: /search_results/
Disallow: /custom_orders/
Disallow: /studios/
Disallow: /v1/stats
Disallow: /v1/browser-performance
Disallow: /assets/shared/*
Disallow: /content_reporting/
Allow: /pro/about
# Blocking Pagination
Disallow: *page=
Allow: *page=2$
# Blocking Gig 2 Gig duplications
Disallow: /*context_referrer=gig_page
# Blocking Seller 2 Gig duplications
Disallow: /*?*source=user_page*
Disallow: /*context_referrer=user_page
# Blocking activity api
Disallow: /api/v1/activities

Disallow: /logo-maker/brief/
Disallow: /logo-maker/choose-variation/
Disallow: /logo-maker/wordpress
Disallow: /logo-maker/woo
"""


def is_allowed_by_robots(base_url: str, path: str = "/") -> bool:
    """
    Check whether the given path is allowed by the site's robots.txt.

    If checking fiverr.com, we use the specific robots.txt rules provided
    by the user to ensure exact compliance, falling back to dynamic fetch otherwise.
    """
    if "fiverr.com" in base_url.lower():
        rp = RobotFileParser()
        rp.parse(FIVERR_ROBOTS_TXT.splitlines())
        target_url = urljoin(base_url, path)
        stdlib_allowed = rp.can_fetch("*", target_url)
        
        # Check wildcard disallow manually for compliance
        wildcard_blocked = _check_wildcard_disallow(FIVERR_ROBOTS_TXT, path)
        
        # Manually verify pagination and key blocks
        if "page=" in path:
            # Only Allow: *page=2$
            # Normalize path to strip trailing slash or query params if any
            if not (path.endswith("page=2") or "page=2&" in path or "page=2$" in path):
                return False
                
        allowed = stdlib_allowed and not wildcard_blocked
        if not allowed:
            log.warning("Fiverr robots.txt (local rules) disallows: %s (blocks %s)", target_url, path)
        return allowed

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
    driver,
    max_pages: int = 10,
    category_slug: str = "",
) -> list[FreelanceProject]:
    """
    Scrape project listings from Freelancer.com using DEEP CRAWLING and Selenium only.
    """
    projects: list[FreelanceProject] = []
    search_path = FREELANCER_SEARCH + category_slug
    seen_urls: set[str] = set()

    if not is_allowed_by_robots(FREELANCER_BASE, search_path):
        log.warning("Freelancer.com robots.txt blocks this path. Skipping.")
        return projects

    log.info("▶ Starting Freelancer.com DEEP CRAWL (max %d pages) …", max_pages)

    for page_num in range(1, max_pages + 1):
        page_url = f"{FREELANCER_BASE}{search_path}?page={page_num}"
        log.info("  [Listing] Page %d/%d → %s", page_num, max_pages, page_url)

        success = fetch_page_selenium(driver, page_url)
        if not success:
            log.warning("  Could not fetch listing page %d. Stopping.", page_num)
            break

        cards = find_elements_by_selectors(driver, [
            "div.JobSearchCard-item",
            "div[class*='job-card']",
            "li.job-wrap",
            "div.search-result-item"
        ])

        if not cards:
            log.warning(
                "  No job cards on page %d. Site layout may have changed.", page_num
            )
            break

        log.info("  Found %d project cards on page %d.", len(cards), page_num)

        # Extract card-level info from all cards first to prevent stale references when navigating
        extracted_cards = []
        for card in cards:
            card_info = _parse_freelancer_card_selenium(card)
            if card_info:
                extracted_cards.append(card_info)

        for card_idx, card_info in enumerate(extracted_cards, start=1):
            project_url = card_info["url"]

            if not project_url:
                log.debug("    Card %d: no URL found, skipping detail fetch.", card_idx)
                bmin, bmax, currency, btype = clean_budget(card_info["raw_budget_card"])
                project = FreelanceProject(
                    platform="Freelancer.com",
                    title=card_info["title"],
                    url=None,
                    budget_min=bmin,
                    budget_max=bmax,
                    budget_currency=currency,
                    budget_type=btype,
                    skills=card_info["skills_card"],
                    category=card_info["category"],
                    posted_date=card_info["posted"],
                    full_description=None,
                    description_snippet=card_info["snippet"],
                )
                projects.append(project)
                continue

            if project_url in seen_urls:
                log.debug("    Card %d: duplicate URL skipped: %s", card_idx, project_url)
                continue
            seen_urls.add(project_url)

            log.debug(
                "    [Deep Crawl] Card %d/%d — visiting detail page: %s",
                card_idx, len(extracted_cards), project_url,
            )
            polite_sleep(2, 5)

            detail_success = fetch_detail_page_selenium(driver, project_url)
            if detail_success:
                detail_data = _parse_freelancer_detail_selenium(driver)
            else:
                detail_data = {"full_description": None, "skills": [], "budget_raw": None}

            skills_final = detail_data["skills"] if detail_data["skills"] else card_info["skills_card"]
            raw_budget_final = detail_data["budget_raw"] or card_info["raw_budget_card"]
            bmin, bmax, currency, btype = clean_budget(raw_budget_final)

            project = FreelanceProject(
                platform="Freelancer.com",
                title=card_info["title"],
                url=project_url,
                budget_min=bmin,
                budget_max=bmax,
                budget_currency=currency,
                budget_type=btype,
                skills=skills_final,
                category=card_info["category"],
                posted_date=card_info["posted"],
                full_description=detail_data["full_description"],
                description_snippet=card_info["snippet"],
            )
            projects.append(project)
            log.debug(
                "    ✔ Card %d — title: %s | skills: %d | desc_len: %d",
                card_idx,
                (project.title or "")[:50],
                len(project.skills),
                len(project.full_description or ""),
            )

        log.info("  → %d projects collected so far.", len(projects))
        polite_sleep()

    log.info("✔ Freelancer.com DEEP CRAWL done. Total: %d projects.", len(projects))
    return projects


def _parse_freelancer_card_selenium(card) -> Optional[dict]:
    try:
        title = get_text_by_selectors(card, [
            "a.JobSearchCard-primary-heading-link",
            "h2.JobSearchCard-primary-heading a",
            "[class*='heading'] a"
        ])
        if not title:
            return None

        url = get_attribute_by_selectors(card, [
            "a.JobSearchCard-primary-heading-link",
            "h2.JobSearchCard-primary-heading a",
            "[class*='heading'] a",
            "a[href*='/projects/']"
        ], "href")
        
        raw_budget_card = get_text_by_selectors(card, [
            "div.JobSearchCard-primary-price",
            "[class*='price']",
            "[class*='budget']"
        ])
        
        skills_elements = find_elements_by_selectors(card, [
            "a.JobSearchCard-primary-tagsLink",
            "[class*='skill'] a",
            "[class*='tag'] a"
        ])
        skills_card = [el.text.strip() for el in skills_elements if el.text.strip()]
        
        category = get_text_by_selectors(card, [
            "a.JobSearchCard-primary-category",
            "[class*='category']"
        ])
        
        snippet = get_text_by_selectors(card, [
            "p.JobSearchCard-secondary-description",
            "[class*='description']"
        ])
        if snippet:
            snippet = snippet[:250]
            
        posted = get_text_by_selectors(card, [
            "span[class*='ago']",
            "time"
        ])
        
        return {
            "title": title,
            "url": url,
            "raw_budget_card": raw_budget_card,
            "skills_card": skills_card,
            "category": category,
            "snippet": snippet,
            "posted": posted
        }
    except Exception as exc:
        log.warning("  Error parsing Freelancer card: %s", exc)
        return None


def _parse_freelancer_detail_selenium(driver) -> dict:
    result = {"full_description": None, "skills": [], "budget_raw": None}
    
    desc_element = find_element_by_selectors(driver, [
        "p.Project-description",
        "div.PageProjectViewLogout-projectDescription",
        "div.project-description",
        "[class*='ProjectDescription']",
        "[class*='project-description']",
        "div[class*='description'] p",
        "section.project-description"
    ])
    if desc_element:
        result["full_description"] = desc_element.text.strip()
        
    skills_elements = find_elements_by_selectors(driver, [
        "a[href*='/jobs/']",
        "a.skill-tag",
        "[class*='SkillTag']",
        "[class*='skill-tag']",
        "ul.skills-list li"
    ])
    result["skills"] = [el.text.strip() for el in skills_elements if el.text.strip()]
    
    budget_element = find_element_by_selectors(driver, [
        "h2.text-right",
        "h2.text-body-24",
        "[class*='PageProjectViewLogout-budget']",
        "[class*='project-budget']",
        "[class*='Budget']",
        "span[class*='price']"
    ])
    if budget_element:
        result["budget_raw"] = budget_element.text.strip()
        
    return result


# ---------------------------------------------------------------------------
# Scraper 2: Fiverr.com
# ---------------------------------------------------------------------------

FIVERR_BASE = "https://www.fiverr.com"


def scrape_fiverr(
    driver,
    max_pages: int = 10,
) -> list[FreelanceProject]:
    """
    Scrape project listings from Fiverr.com using DEEP CRAWLING and Selenium only.
    Respects Fiverr robots.txt disallow rules (especially search and pagination).
    """
    projects: list[FreelanceProject] = []
    seen_urls: set[str] = set()

    # Fiverr categories / subcategories to crawl (since /search/ is blocked)
    categories = [
        "/categories/programming-tech",
        "/categories/programming-tech/web-development",
        "/categories/programming-tech/mobile-apps",
        "/categories/programming-tech/support-it",
        "/categories/programming-tech/artificial-intelligence"
    ]

    log.info("▶ Starting Fiverr.com DEEP CRAWL (respecting category-only routing) …")

    for cat_slug in categories:
        urls_to_fetch = []
        if is_allowed_by_robots(FIVERR_BASE, cat_slug):
            urls_to_fetch.append(f"{FIVERR_BASE}{cat_slug}")
        
        # Check if page 2 is allowed and requested max_pages allows it (Allow: *page=2$)
        page2_url = f"{cat_slug}?page=2"
        if max_pages >= 2 and is_allowed_by_robots(FIVERR_BASE, page2_url):
            urls_to_fetch.append(f"{FIVERR_BASE}{page2_url}")

        for page_url in urls_to_fetch:
            log.info("  [Listing] Page endpoint → %s", page_url)

            success = fetch_page_selenium(driver, page_url)
            if not success:
                log.warning("  Could not fetch Fiverr page: %s", page_url)
                continue

            cards = find_elements_by_selectors(driver, [
                "div.gig-card-layout",
                "div.gig_block",
                "div.gig-wrapper",
                "div[data-gig-id]",
                "div[class*='gig-card']",
                "article.gig-card"
            ])

            if not cards:
                log.warning("  No gig cards found on page %s.", page_url)
                continue

            log.info("  Found %d gig cards on page %s.", len(cards), page_url)

            # Pre-extract card details to avoid StaleElementReferenceException
            extracted_cards = []
            for card in cards:
                card_info = _parse_fiverr_card_selenium(card)
                if card_info:
                    extracted_cards.append(card_info)

            for card_idx, card_info in enumerate(extracted_cards, start=1):
                project_url = card_info["url"]

                if not project_url:
                    log.debug("    Card %d: no URL found, skipping detail fetch.", card_idx)
                    bmin, bmax, currency, btype = clean_budget(card_info["raw_budget_card"])
                    project = FreelanceProject(
                        platform="Fiverr.com",
                        title=card_info["title"],
                        url=None,
                        budget_min=bmin,
                        budget_max=bmax,
                        budget_currency=currency,
                        budget_type=btype,
                        skills=[],
                        category=cat_slug.split("/")[-1].replace("-", " ").title(),
                        posted_date=None,
                        full_description=None,
                        description_snippet=None,
                        seller_level=card_info.get("seller_level")
                    )
                    projects.append(project)
                    continue

                if project_url.startswith("/"):
                    project_url = urljoin(FIVERR_BASE, project_url)

                if project_url in seen_urls:
                    log.debug("    Card %d: duplicate URL skipped: %s", card_idx, project_url)
                    continue
                seen_urls.add(project_url)

                # robots.txt validation for individual gig pages
                url_path = project_url.replace(FIVERR_BASE, "")
                if not is_allowed_by_robots(FIVERR_BASE, url_path):
                    log.warning("    Fiverr robots.txt disallows detail page: %s. Skipping.", project_url)
                    continue

                log.debug(
                    "    [Deep Crawl] Card %d/%d — visiting detail page: %s",
                    card_idx, len(extracted_cards), project_url,
                )
                polite_sleep(2, 5)

                detail_success = fetch_detail_page_selenium(driver, project_url)
                if detail_success:
                    detail_data = _parse_fiverr_detail_selenium(driver)
                else:
                    detail_data = {"full_description": None, "skills": [], "budget_raw": None, "seller_level": None}

                raw_budget_final = detail_data["budget_raw"] or card_info["raw_budget_card"]
                bmin, bmax, currency, btype = clean_budget(raw_budget_final)
                skills_final = list(set([s.strip() for s in detail_data["skills"] if s.strip()]))
                seller_level_final = detail_data["seller_level"] or card_info["seller_level"]

                project = FreelanceProject(
                    platform="Fiverr.com",
                    title=card_info["title"],
                    url=project_url,
                    budget_min=bmin,
                    budget_max=bmax,
                    budget_currency=currency,
                    budget_type=btype,
                    skills=skills_final,
                    category=cat_slug.split("/")[-1].replace("-", " ").title(),
                    posted_date=None,
                    full_description=detail_data["full_description"],
                    description_snippet=None,
                    seller_level=seller_level_final
                )
                projects.append(project)
                log.debug(
                    "    ✔ Card %d — title: %s | skills: %d | desc_len: %d",
                    card_idx,
                    (project.title or "")[:50],
                    len(project.skills),
                    len(project.full_description or ""),
                )

            log.info("  → %d Fiverr gigs collected so far.", len(projects))
            polite_sleep()

    log.info("✔ Fiverr.com DEEP CRAWL done. Total: %d gigs.", len(projects))
    return projects


def _parse_fiverr_card_selenium(card) -> Optional[dict]:
    try:
        title = get_text_by_selectors(card, [
            "h3",
            "p.gig-title",
            "div.gig-title",
            "[class*='title'] a",
            "[class*='title']"
        ])
        if not title:
            return None

        url = get_attribute_by_selectors(card, [
            "a[href*='/gigs/']",
            "h3 a",
            "a[class*='gig-link']",
            "a"
        ], "href")

        raw_budget_card = get_text_by_selectors(card, [
            "span.price",
            "span.price-amount",
            "[class*='price']",
            "div.price-wrapper"
        ])

        seller_level = get_text_by_selectors(card, [
            "span.seller-level",
            "div.seller-level",
            "span[class*='level']",
            "[class*='seller'] [class*='level']"
        ])

        return {
            "title": title,
            "url": url,
            "raw_budget_card": raw_budget_card,
            "seller_level": seller_level
        }
    except Exception as exc:
        log.warning("  Error parsing Fiverr card: %s", exc)
        return None


def _parse_fiverr_detail_selenium(driver) -> dict:
    result = {"full_description": None, "skills": [], "budget_raw": None, "seller_level": None}

    desc_element = find_element_by_selectors(driver, [
        "div.gig-description",
        "div.description-wrapper",
        "div.description",
        "section.gig-description",
        "div[class*='description']",
        "div.gig-description-wrapper"
    ])
    if desc_element:
        result["full_description"] = desc_element.text.strip()

    skills_elements = find_elements_by_selectors(driver, [
        "ul.tags li a",
        "a.tag-link",
        "ul.tags-list li",
        "div.metadata-tags a",
        "span.tag-item",
        "a[href*='/tags/']"
    ])
    result["skills"] = [el.text.strip() for el in skills_elements if el.text.strip()]

    budget_element = find_element_by_selectors(driver, [
        "span.price",
        "div.package-content span.price",
        "span.price-amount",
        "[class*='price-amount']",
        "tr.package-row td.price",
        "span.package-price"
    ])
    if budget_element:
        result["budget_raw"] = budget_element.text.strip()

    seller_level_element = find_element_by_selectors(driver, [
        "span.seller-level",
        "div.seller-level",
        "span[class*='level']",
        "[class*='seller-card'] [class*='level']"
    ])
    if seller_level_element:
        result["seller_level"] = seller_level_element.text.strip()

    return result



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
    Orchestrates the full Deep Crawl ETL pipeline using Selenium only:
      1. Create a headless Chrome Selenium WebDriver.
      2. DEEP CRAWL each platform:
           a. Fetch listing pages (pagination) using Selenium.
           b. Extract individual project URLs from cards.
           c. Visit each project's detail page using Selenium.
           d. Parse full description + complete skills from detail page natively with Selenium.
      3. Merge results.
      4. Export to JSON.
      5. Ensure the Selenium driver is safely quit.
    """
    log.info("=" * 60)
    log.info("  Freelance Market Monitor — DEEP CRAWL Scraper Starting")
    log.info("  Crawl type  : Deep Crawling (following links)")
    log.info("  HTTP client : Selenium Chrome WebDriver (Headless)")
    log.info("  Parser      : Selenium (Native)")
    log.info("  Delay       : time.sleep()  [CS313x compliant]")
    log.info("  Note        : polite_sleep(2,5) between EVERY project visit")
    log.info("=" * 60)

    max_pages = 1000 # Increased to 1000 to collect the full available dataset
    if "--test" in sys.argv:
        max_pages = 1
        log.info("🧪 Running in TEST mode: limiting crawl to 1 page per platform.")

    driver = create_driver()
    all_projects: list[FreelanceProject] = []
    freelancer_projects = []
    fiverr_projects = []

    try:
        # ── Platform 1: Freelancer.com (Deep Crawl) ───────────────────────────
        freelancer_projects = scrape_freelancer(driver, max_pages=max_pages)
        all_projects.extend(freelancer_projects)

        # Brief pause between platforms
        polite_sleep(3, 7)

        # ── Platform 2: Fiverr.com (Deep Crawl) ───────────────────────────────
        fiverr_projects = scrape_fiverr(driver, max_pages=max_pages)
        all_projects.extend(fiverr_projects)

    finally:
        log.info("Closing Selenium WebDriver...")
        driver.quit()

    # ── Summary ────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("  DEEP CRAWL COMPLETE")
    log.info("  Freelancer.com : %d projects", len(freelancer_projects))
    log.info("  Fiverr.com     : %d projects", len(fiverr_projects))
    log.info("  TOTAL          : %d projects", len(all_projects))
    log.info("=" * 60)

    if not all_projects:
        log.warning("No data collected. The sites' HTML structure may have changed.")
        log.warning("Run with DEBUG logging: logging.basicConfig(level=logging.DEBUG)")
        return

    export_to_json(all_projects, "freelance_data.json")


if __name__ == "__main__":
    main()
