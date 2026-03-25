"""Website diagnostics module — AI crawler check, citability scoring, llms.txt generation.

Provides three diagnostic functions that analyze a target website for GEO optimization:
1. check_crawlers() — Parse robots.txt for 14 AI crawler access status
2. score_citability() — Score content blocks on 5 dimensions (0-100)
3. generate_llmstxt() — Validate existing + generate recommended llms.txt

All functions are stateless and safe to call from threads.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# 14 AI crawlers grouped by tier
AI_CRAWLERS = [
    {"name": "GPTBot", "operator": "OpenAI", "tier": 1, "purpose": "ChatGPT Search + training"},
    {"name": "OAI-SearchBot", "operator": "OpenAI", "tier": 1, "purpose": "ChatGPT Search only"},
    {"name": "ChatGPT-User", "operator": "OpenAI", "tier": 1, "purpose": "User browsing"},
    {"name": "ClaudeBot", "operator": "Anthropic", "tier": 1, "purpose": "Claude web search"},
    {"name": "PerplexityBot", "operator": "Perplexity", "tier": 1, "purpose": "Perplexity Search"},
    {"name": "Google-Extended", "operator": "Google", "tier": 2, "purpose": "Gemini training"},
    {"name": "GoogleOther", "operator": "Google", "tier": 2, "purpose": "Google AI research"},
    {"name": "Applebot-Extended", "operator": "Apple", "tier": 2, "purpose": "Apple Intelligence"},
    {"name": "Amazonbot", "operator": "Amazon", "tier": 2, "purpose": "Alexa AI"},
    {"name": "FacebookBot", "operator": "Meta", "tier": 2, "purpose": "Meta AI"},
    {"name": "CCBot", "operator": "Common Crawl", "tier": 3, "purpose": "Training data"},
    {"name": "anthropic-ai", "operator": "Anthropic", "tier": 3, "purpose": "Claude training"},
    {"name": "Bytespider", "operator": "ByteDance", "tier": 3, "purpose": "TikTok AI"},
    {"name": "cohere-ai", "operator": "Cohere", "tier": 3, "purpose": "Cohere training"},
]


# ─── 1. AI Crawler Check ──────────────────────────────────────────────


def check_crawlers(url: str) -> dict:
    """Parse robots.txt and check access status for 14 AI crawlers."""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{base_url}/robots.txt"

    result = {
        "robots_url": robots_url,
        "robots_exists": False,
        "crawlers": [],
        "sitemaps": [],
        "summary": {"tier1_allowed": 0, "tier1_total": 5, "tier2_allowed": 0, "tier2_total": 5},
        "score": 0,
        "errors": [],
    }

    try:
        resp = requests.get(robots_url, headers=DEFAULT_HEADERS, timeout=15)
        if resp.status_code != 200:
            if resp.status_code == 404:
                result["errors"].append("No robots.txt found")
                for c in AI_CRAWLERS:
                    result["crawlers"].append({**c, "status": "no_robots_txt"})
                result["summary"]["tier1_allowed"] = 5
                result["summary"]["tier2_allowed"] = 5
                result["score"] = 80  # No robots.txt means nothing is blocked
            else:
                result["errors"].append(f"robots.txt returned {resp.status_code}")
            return result

        result["robots_exists"] = True
        content = resp.text

        # Parse robots.txt
        lines = content.split("\n")
        current_agent = None
        agent_rules = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            lower = line.lower()
            if lower.startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
                if current_agent not in agent_rules:
                    agent_rules[current_agent] = []
            elif lower.startswith("disallow:") and current_agent:
                path = line.split(":", 1)[1].strip()
                agent_rules[current_agent].append(("Disallow", path))
            elif lower.startswith("allow:") and current_agent:
                path = line.split(":", 1)[1].strip()
                agent_rules[current_agent].append(("Allow", path))
            elif lower.startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                if not sitemap_url.startswith("http"):
                    sitemap_url = "http" + sitemap_url
                result["sitemaps"].append(sitemap_url)

        # Determine status for each crawler
        for crawler in AI_CRAWLERS:
            name = crawler["name"]
            status = "allowed"

            if name in agent_rules:
                rules = agent_rules[name]
                if any(d == "Disallow" and p == "/" for d, p in rules):
                    status = "blocked"
                elif any(d == "Disallow" and p for d, p in rules):
                    status = "partial"
                else:
                    status = "allowed"
            elif "*" in agent_rules:
                wildcard = agent_rules["*"]
                if any(d == "Disallow" and p == "/" for d, p in wildcard):
                    status = "blocked_wildcard"
                else:
                    status = "allowed_default"
            else:
                status = "allowed_default"

            entry = {**crawler, "status": status}
            result["crawlers"].append(entry)

            if crawler["tier"] == 1 and status in ("allowed", "allowed_default", "no_robots_txt"):
                result["summary"]["tier1_allowed"] += 1
            elif crawler["tier"] == 2 and status in ("allowed", "allowed_default", "no_robots_txt"):
                result["summary"]["tier2_allowed"] += 1

        # Score: Tier 1 (50%), Tier 2 (25%), no blanket block (15%), sitemap (10%)
        t1 = result["summary"]["tier1_allowed"]
        t2 = result["summary"]["tier2_allowed"]
        score = int((t1 / 5) * 50 + (t2 / 5) * 25)

        # Check for blanket block
        has_blanket = "*" in agent_rules and any(
            d == "Disallow" and p == "/" for d, p in agent_rules["*"]
        )
        if not has_blanket:
            score += 15

        if result["sitemaps"]:
            score += 10

        result["score"] = min(score, 100)

    except requests.exceptions.Timeout:
        result["errors"].append("Timeout fetching robots.txt")
    except requests.exceptions.ConnectionError as e:
        result["errors"].append(f"Connection error: {str(e)[:200]}")
    except Exception as e:
        result["errors"].append(f"Error: {str(e)[:200]}")

    return result


# ─── 2. Citability Scoring ─────────────────────────────────────────────


def _score_passage(text: str, heading: str = None) -> dict:
    """Score a single passage for AI citability (0-100)."""
    words = text.split()
    word_count = len(words)
    if word_count < 10:
        return None

    scores = {}

    # 1. Answer Block Quality (30%)
    abq = 0
    definition_patterns = [
        r"\b\w+\s+is\s+(?:a|an|the)\s",
        r"\b\w+\s+refers?\s+to\s",
        r"\b\w+\s+means?\s",
        r"\b\w+\s+(?:can be |are )?defined\s+as\s",
    ]
    for p in definition_patterns:
        if re.search(p, text, re.IGNORECASE):
            abq += 15
            break

    first_60 = " ".join(words[:60])
    if any(re.search(p, first_60, re.IGNORECASE) for p in [
        r"\b(?:is|are|was|were|means?|refers?)\b", r"\d+%", r"\$[\d,]+",
        r"\d+\s+(?:million|billion|thousand)",
    ]):
        abq += 15

    if heading and heading.endswith("?"):
        abq += 10

    sentences = re.split(r"[.!?]+", text)
    short_clear = sum(1 for s in sentences if 5 <= len(s.split()) <= 25)
    if sentences:
        abq += int((short_clear / len(sentences)) * 10)

    if re.search(r"(?:according to|research shows|studies? (?:show|indicate|suggest|found))", text, re.IGNORECASE):
        abq += 10

    scores["answer_block_quality"] = min(abq, 30)

    # 2. Self-Containment (25%)
    sc = 0
    if 134 <= word_count <= 167:
        sc += 10
    elif 100 <= word_count <= 200:
        sc += 7
    elif 80 <= word_count <= 250:
        sc += 4
    elif word_count >= 30:
        sc += 2

    pronoun_count = len(re.findall(
        r"\b(?:it|they|them|their|this|that|these|those|he|she|his|her)\b", text, re.IGNORECASE
    ))
    if word_count > 0:
        ratio = pronoun_count / word_count
        if ratio < 0.02:
            sc += 8
        elif ratio < 0.04:
            sc += 5
        elif ratio < 0.06:
            sc += 3

    proper_nouns = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text))
    if proper_nouns >= 3:
        sc += 7
    elif proper_nouns >= 1:
        sc += 4

    scores["self_containment"] = min(sc, 25)

    # 3. Structural Readability (20%)
    sr = 0
    if sentences:
        avg_len = word_count / len(sentences)
        if 10 <= avg_len <= 20:
            sr += 8
        elif 8 <= avg_len <= 25:
            sr += 5
        else:
            sr += 2

    if re.search(r"(?:first|second|third|finally|additionally|moreover|furthermore)", text, re.IGNORECASE):
        sr += 4
    if re.search(r"(?:\d+[\.\)]\s|\b(?:step|tip|point)\s+\d+)", text, re.IGNORECASE):
        sr += 4
    if "\n" in text:
        sr += 4

    scores["structural_readability"] = min(sr, 20)

    # 4. Statistical Density (15%)
    sd = 0
    sd += min(len(re.findall(r"\d+(?:\.\d+)?%", text)) * 3, 6)
    sd += min(len(re.findall(r"\$[\d,]+(?:\.\d+)?", text)) * 3, 5)
    sd += min(len(re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\s+(?:users|customers|pages|sites|companies|people|percent|times)", text, re.IGNORECASE)) * 2, 4)
    if re.findall(r"\b20(?:2[3-6]|1\d)\b", text):
        sd += 2

    scores["statistical_density"] = min(sd, 15)

    # 5. Uniqueness Signals (10%)
    us = 0
    if re.search(r"(?:our (?:research|study|data|analysis)|we (?:found|discovered|analyzed))", text, re.IGNORECASE):
        us += 5
    if re.search(r"(?:case study|for example|for instance|real-world)", text, re.IGNORECASE):
        us += 3
    if re.search(r"(?:using|with|via|through)\s+[A-Z][a-z]+", text):
        us += 2

    scores["uniqueness_signals"] = min(us, 10)

    total = sum(scores.values())
    if total >= 80:
        grade, label = "A", "Highly Citable"
    elif total >= 65:
        grade, label = "B", "Good"
    elif total >= 50:
        grade, label = "C", "Moderate"
    elif total >= 35:
        grade, label = "D", "Low"
    else:
        grade, label = "F", "Poor"

    return {
        "heading": heading,
        "word_count": word_count,
        "total_score": total,
        "grade": grade,
        "label": label,
        "breakdown": scores,
        "preview": " ".join(words[:25]) + ("..." if word_count > 25 else ""),
    }


def score_citability(url: str) -> dict:
    """Analyze all content blocks on a page for citability."""
    result = {
        "url": url,
        "total_blocks": 0,
        "average_score": 0,
        "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
        "top_blocks": [],
        "bottom_blocks": [],
        "optimal_length_count": 0,
        "errors": [],
    }

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        result["errors"].append(f"Failed to fetch page: {str(e)[:200]}")
        return result

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove non-content elements
    for el in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "form"]):
        el.decompose()

    # Extract content blocks between headings
    blocks = []
    current_heading = "Introduction"
    current_paragraphs = []

    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table"]):
        if el.name.startswith("h"):
            if current_paragraphs:
                combined = " ".join(current_paragraphs)
                if len(combined.split()) >= 20:
                    blocks.append({"heading": current_heading, "content": combined})
            current_heading = el.get_text(strip=True)
            current_paragraphs = []
        else:
            text = el.get_text(strip=True)
            if text and len(text.split()) >= 5:
                current_paragraphs.append(text)

    if current_paragraphs:
        combined = " ".join(current_paragraphs)
        if len(combined.split()) >= 20:
            blocks.append({"heading": current_heading, "content": combined})

    # Score each block
    scored = []
    for block in blocks:
        s = _score_passage(block["content"], block["heading"])
        if s:
            scored.append(s)

    if not scored:
        result["errors"].append("No scoreable content blocks found")
        return result

    result["total_blocks"] = len(scored)
    result["average_score"] = round(sum(b["total_score"] for b in scored) / len(scored), 1)

    for b in scored:
        result["grade_distribution"][b["grade"]] += 1
        if 134 <= b["word_count"] <= 167:
            result["optimal_length_count"] += 1

    sorted_blocks = sorted(scored, key=lambda x: x["total_score"], reverse=True)
    result["top_blocks"] = sorted_blocks[:5]
    result["bottom_blocks"] = sorted_blocks[-5:] if len(sorted_blocks) > 5 else []

    return result


# ─── 3. llms.txt Generator ────────────────────────────────────────────


def _validate_llmstxt(base_url: str) -> dict:
    """Check if llms.txt exists and validate its format."""
    llms_url = f"{base_url}/llms.txt"
    llms_full_url = f"{base_url}/llms-full.txt"

    result = {
        "url": llms_url,
        "exists": False,
        "format_valid": False,
        "has_title": False,
        "has_description": False,
        "has_sections": False,
        "has_links": False,
        "section_count": 0,
        "link_count": 0,
        "issues": [],
        "suggestions": [],
        "full_exists": False,
    }

    try:
        resp = requests.get(llms_url, headers=DEFAULT_HEADERS, timeout=15)
        if resp.status_code == 200:
            result["exists"] = True
            content = resp.text
            lines = content.strip().split("\n")

            if lines and lines[0].startswith("# "):
                result["has_title"] = True
            else:
                result["issues"].append("Missing title (should start with '# Site Name')")

            for line in lines:
                if line.startswith("> "):
                    result["has_description"] = True
                    break
            if not result["has_description"]:
                result["issues"].append("Missing description blockquote")

            sections = [l for l in lines if l.startswith("## ")]
            result["section_count"] = len(sections)
            result["has_sections"] = len(sections) > 0
            if not result["has_sections"]:
                result["issues"].append("No sections found")

            links = re.findall(r"- \[.+\]\(.+\)", content)
            result["link_count"] = len(links)
            result["has_links"] = len(links) > 0
            if not result["has_links"]:
                result["issues"].append("No page links found")

            result["format_valid"] = all([
                result["has_title"], result["has_description"],
                result["has_sections"], result["has_links"],
            ])

            if result["link_count"] < 5:
                result["suggestions"].append("Add more key pages (aim for 10-20)")
            if result["section_count"] < 2:
                result["suggestions"].append("Add more sections to organize content")
    except Exception:
        pass

    try:
        resp = requests.get(llms_full_url, headers=DEFAULT_HEADERS, timeout=10)
        if resp.status_code == 200:
            result["full_exists"] = True
    except Exception:
        pass

    return result


def generate_llmstxt(url: str) -> dict:
    """Validate existing llms.txt and generate a recommended version."""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    result = {
        "url": url,
        "existing": {},
        "generated_llmstxt": "",
        "generated_llmstxt_full": "",
        "pages_analyzed": 0,
        "sections": {},
        "errors": [],
    }

    # Step 1: Validate existing
    result["existing"] = _validate_llmstxt(base_url)

    # Step 2: Generate recommended version
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        result["errors"].append(f"Failed to fetch homepage: {str(e)[:200]}")
        return result

    # Extract site name and description
    title_tag = soup.find("title")
    site_name = title_tag.get_text(strip=True).split("|")[0].split("-")[0].strip() if title_tag else parsed.netloc
    meta_desc = soup.find("meta", attrs={"name": "description"})
    site_description = meta_desc.get("content", "") if meta_desc else f"Official website of {site_name}"

    # Discover and categorize pages
    pages = {
        "Main Pages": [],
        "Products & Services": [],
        "Resources & Blog": [],
        "Company": [],
        "Support": [],
    }

    seen_urls = set()
    max_pages = 30

    # Try sitemap first
    try:
        sitemap_url = f"{base_url}/sitemap.xml"
        sitemap_resp = requests.get(sitemap_url, headers=DEFAULT_HEADERS, timeout=10)
        if sitemap_resp.status_code == 200:
            sitemap_soup = BeautifulSoup(sitemap_resp.text, "lxml")
            for url_tag in sitemap_soup.find_all("url"):
                loc = url_tag.find("loc")
                if loc and len(seen_urls) < max_pages:
                    page_url = loc.text.strip()
                    if urlparse(page_url).netloc == parsed.netloc:
                        seen_urls.add(page_url)
    except Exception:
        pass

    # Also crawl homepage links
    for link in soup.find_all("a", href=True):
        if len(seen_urls) >= max_pages:
            break
        href = urljoin(base_url, link["href"])
        link_text = link.get_text(strip=True)
        if not link_text or len(link_text) < 2:
            continue
        parsed_href = urlparse(href)
        if parsed_href.netloc != parsed.netloc:
            continue
        if href in seen_urls:
            continue
        if any(ext in href for ext in [".pdf", ".jpg", ".png", ".gif", ".css", ".js"]):
            continue
        if "#" in href and href.split("#")[0] in seen_urls:
            continue
        seen_urls.add(href)

    # Categorize discovered pages
    for page_url in seen_urls:
        path = urlparse(page_url).path.lower()
        # Try to get link text from homepage
        link_el = soup.find("a", href=lambda h: h and urljoin(base_url, h) == page_url)
        title = link_el.get_text(strip=True) if link_el else path.strip("/").split("/")[-1].replace("-", " ").title()
        if not title or len(title) < 2:
            title = path.strip("/").split("/")[-1].replace("-", " ").title() or "Page"

        entry = {"url": page_url, "title": title}

        if any(kw in path for kw in ["/pricing", "/feature", "/product", "/solution", "/demo", "/plan"]):
            pages["Products & Services"].append(entry)
        elif any(kw in path for kw in ["/blog", "/article", "/resource", "/guide", "/learn", "/docs", "/news"]):
            pages["Resources & Blog"].append(entry)
        elif any(kw in path for kw in ["/about", "/team", "/career", "/contact", "/press", "/partner"]):
            pages["Company"].append(entry)
        elif any(kw in path for kw in ["/help", "/support", "/faq", "/status"]):
            pages["Support"].append(entry)
        else:
            pages["Main Pages"].append(entry)

    result["pages_analyzed"] = len(seen_urls)

    # Generate llms.txt (concise)
    llms_lines = [f"# {site_name}", f"> {site_description}", ""]
    for section, section_pages in pages.items():
        if section_pages:
            llms_lines.append(f"## {section}")
            for page in section_pages[:10]:
                llms_lines.append(f"- [{page['title']}]({page['url']})")
            llms_lines.append("")

    llms_lines.extend([
        "## Contact",
        f"- Website: {base_url}",
        f"- Email: contact@{parsed.netloc}",
        "",
    ])
    result["generated_llmstxt"] = "\n".join(llms_lines)

    # Generate llms-full.txt (with descriptions from meta tags)
    full_lines = [f"# {site_name}", f"> {site_description}", ""]
    for section, section_pages in pages.items():
        if section_pages:
            full_lines.append(f"## {section}")
            for page in section_pages:
                # Fetch page description (with short timeout)
                desc = ""
                try:
                    page_resp = requests.get(page["url"], headers=DEFAULT_HEADERS, timeout=5)
                    page_soup = BeautifulSoup(page_resp.text, "lxml")
                    page_meta = page_soup.find("meta", attrs={"name": "description"})
                    if page_meta:
                        desc = page_meta.get("content", "")
                except Exception:
                    pass
                if desc:
                    full_lines.append(f"- [{page['title']}]({page['url']}): {desc}")
                else:
                    full_lines.append(f"- [{page['title']}]({page['url']})")
            full_lines.append("")

    full_lines.extend([
        "## Contact",
        f"- Website: {base_url}",
        f"- Email: contact@{parsed.netloc}",
        "",
    ])
    result["generated_llmstxt_full"] = "\n".join(full_lines)
    result["sections"] = {k: len(v) for k, v in pages.items()}

    return result


# ─── Orchestrator ──────────────────────────────────────────────────────


def run_all_diagnostics(url: str) -> dict:
    """Run all 3 diagnostic checks in parallel. Returns combined result."""
    result = {"url": url, "crawler_check": None, "citability": None, "llmstxt": None}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(check_crawlers, url): "crawler_check",
            pool.submit(score_citability, url): "citability",
            pool.submit(generate_llmstxt, url): "llmstxt",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                result[key] = future.result(timeout=60)
            except Exception as e:
                result[key] = {"error": str(e)[:200]}

    return result
