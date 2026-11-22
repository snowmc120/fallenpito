import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, urlunparse
import requests
from bs4 import BeautifulSoup

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def normalize_thread_url(raw_url):
    parsed = urlparse(raw_url)
    clean_path = re.sub(r"/(page-\d+|post-\d+|latest|unread)/?$", "/", parsed.path)
    if not clean_path.endswith("/"):
        clean_path += "/"
    return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))

def get_cache_path(base_url):
    url_hash = hashlib.md5(base_url.encode("utf-8")).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"{url_hash}.json")

def list_cached_threads():
    items = []
    if not os.path.exists(CACHE_DIR):
        return items
    for fname in os.listdir(CACHE_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(CACHE_DIR, fname)
        try:
            mtime = os.path.getmtime(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            url = data.get("url", "")
            if not url:
                continue
            items.append({
                "title": data.get("title") or url,
                "url": url,
                "img_count": len(data.get("images", [])),
                "vid_count": len(data.get("videos", [])),
                "cmt_count": len(data.get("comments", [])),
                "lnk_count": len(data.get("links", [])),
                "mtime": mtime
            })
        except Exception:
            continue
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items

def detect_total_pages(soup):
    max_p = 1
    for a in soup.select(".pageNav-main a, .pageNav a"):
        txt = a.get_text(strip=True)
        if txt.isdigit():
            max_p = max(max_p, int(txt))
        m = re.search(r"/page-(\d+)", a.get("href", ""))
        if m:
            max_p = max(max_p, int(m.group(1)))

    simple = soup.select_one(".pageNavSimple-el--current")
    if simple:
        m = re.search(r"(?:của|of|/)\s*(\d+)", simple.get_text(strip=True), re.I)
        if m:
            max_p = max(max_p, int(m.group(1)))

    if max_p == 1 and (soup.select_one("link[rel='next']") or soup.select_one(".pageNav-jump--next, .pageNavSimple-el--next")):
        max_p = 50
    return max_p

def is_junk_icon(img_tag, full_url):
    """Lọc triệt để smilies, emoji, reaction, icon giao diện của XenForo/web"""
    classes = " ".join(img_tag.get("class", [])).lower()
    if any(k in classes for k in ["smilie", "emoji", "reaction", "avatar", "icon"]):
        return True

    url_lower = full_url.lower()
    junk_patterns = [
        "/smilies/", "smilie", "emoji", "twemoji", "joypixels", "emojione",
        "avatar", "data/avatars", "/styles/", "/reactions/", "reaction",
        "blank.gif", "spacer.gif", "/assets/icons/", "svg"
    ]
    if any(p in url_lower for p in junk_patterns):
        return True

    # Lọc ảnh có thuộc tính width/height khai báo sẵn quá nhỏ (<= 64px)
    for attr in ("width", "height"):
        val = str(img_tag.get(attr, "")).replace("px", "").strip()
        if val.isdigit() and int(val) <= 64:
            return True

    return False

def parse_html(html_text, page_url, page_num):
    soup = BeautifulSoup(html_text, "html.parser")
    images, videos, comments, links = [], [], [], []
    thread_domain = urlparse(page_url).netloc

    posts = soup.select("article.message") or soup.select(".message-inner")
    for post in posts:
        author_el = post.select_one(".message-name, .username")
        author = author_el.get_text(strip=True) if author_el else "Ẩn danh"

        body = post.select_one(".message-body .bbWrapper") or post.select_one(".bbWrapper")
        if not body:
            continue

        for quote in body.select("blockquote"):
            quote.decompose()

        for img in body.find_all("img"):
            src = img.get("data-src") or img.get("data-url") or img.get("src")
            if not src or src.startswith("data:"):
                continue
            full_url = urljoin(page_url, src)
            if is_junk_icon(img, full_url):
                continue
            images.append({"name": full_url.split("/")[-1].split("?")[0] or "img.jpg", "url": full_url, "page": page_num})

        for vid in body.find_all(["video", "source"]):
            src = vid.get("data-src") or vid.get("src")
            if not src:
                continue
            full_url = urljoin(page_url, src)
            videos.append({"name": full_url.split("/")[-1].split("?")[0] or "vid.mp4", "url": full_url, "page": page_num})

        for a in body.find_all("a", href=True):
            href = urljoin(page_url, a["href"])
            parsed_h = urlparse(href)
            if parsed_h.scheme in ("http", "https") and parsed_h.netloc and parsed_h.netloc != thread_domain:
                links.append({"author": author, "url": href, "page": page_num})

        text = body.get_text(" ", strip=True)
        if len(text) > 1:
            comments.append({"author": author, "text": text[:350], "page": page_num})

    return soup, images, videos, comments, links

def crawl_fast_stream(raw_url, cookie, max_pages, force_refresh=False):
    base_url = normalize_thread_url(raw_url)
    cache_file = get_cache_path(base_url)

    if not force_refresh and os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        yield {"cached": True, "data": cached_data}
        return

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if cookie:
        headers["Cookie"] = cookie
    session.headers.update(headers)

    res1 = session.get(base_url, timeout=15)
    if res1.status_code != 200:
        yield {"error": f"HTTP {res1.status_code} (Kiểm tra lại Cookie)"}
        return

    soup1, imgs1, vids1, cmts1, lks1 = parse_html(res1.text, base_url, 1)
    title_el = soup1.select_one("h1.p-title-value") or soup1.title
    title = title_el.get_text(strip=True) if title_el else base_url

    total_pages = min(detect_total_pages(soup1), max_pages)

    all_images, all_videos, all_comments, all_links = [], [], [], []
    seen = set()

    def merge_batch(imgs, vids, cmts, lks):
        new_i, new_v, new_l = [], [], []
        for x in imgs:
            if x["url"] not in seen:
                seen.add(x["url"])
                all_images.append(x)
                new_i.append(x)
        for x in vids:
            if x["url"] not in seen:
                seen.add(x["url"])
                all_videos.append(x)
                new_v.append(x)
        for x in lks:
            if x["url"] not in seen:
                seen.add(x["url"])
                all_links.append(x)
                new_l.append(x)
        all_comments.extend(cmts)
        return new_i, new_v, cmts, new_l

    ni, nv, nc, nl = merge_batch(imgs1, vids1, cmts1, lks1)
    yield {"progress": True, "done_pages": 1, "total": total_pages, "images": ni, "videos": nv, "comments": nc, "links": nl}

    if total_pages > 1:
        def fetch_worker(p):
            p_url = f"{base_url}page-{p}"
            try:
                r = session.get(p_url, timeout=15)
                if r.status_code != 200:
                    return p, None
                if f"page-{p}" not in r.url and r.url.rstrip("/") == base_url.rstrip("/"):
                    return p, None
                _, i, v, c, l = parse_html(r.text, p_url, p)
                return p, (i, v, c, l)
            except Exception:
                return p, None

        completed = 1
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(fetch_worker, p) for p in range(2, total_pages + 1)]
            for fut in as_completed(futures):
                completed += 1
                _, result = fut.result()
                if result:
                    ni, nv, nc, nl = merge_batch(*result)
                    yield {
                        "progress": True, "done_pages": completed, "total": total_pages,
                        "images": ni, "videos": nv, "comments": nc, "links": nl
                    }
                else:
                    yield {"progress": True, "done_pages": completed, "total": total_pages}

    final_bundle = {
        "title": title,
        "url": base_url,
        "images": all_images,
        "videos": all_videos,
        "comments": all_comments,
        "links": all_links
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(final_bundle, f, ensure_ascii=False)

    yield {"done": True, "total_crawled": total_pages}
