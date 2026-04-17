import os
import traceback


BLOCKED_DOMAINS = [
    'nytimes.com', 'wsj.com', 'ft.com', 'bloomberg.com',
    'washingtonpost.com', 'economist.com', 'newyorker.com',
    'wired.com', 'theatlantic.com', 'hbr.org',
    'businessinsider.com', 'axios.com',
]


def fetch_article_content(url):
    print(f"[fetcher] Starting fetch for: {url}")

    if not url or not url.startswith('http'):
        print(f"[fetcher] Invalid URL: {url}")
        return None, "scraper_blocked"

    try:
        domain = url.split('/')[2].lower().replace('www.', '')
    except (IndexError, AttributeError):
        domain = ''
    for blocked in BLOCKED_DOMAINS:
        if blocked in domain:
            print(f"[fetcher] Known blocked domain: {domain}")
            return None, "scraper_blocked"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    try:
        import requests
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        print(f"[fetcher] HTTP status: {response.status_code}")
        print(f"[fetcher] Content-Type: {response.headers.get('Content-Type', 'unknown')}")

        if response.status_code in (401, 403, 429):
            print(f"[fetcher] Blocked with status {response.status_code}")
            return None, "scraper_blocked"

        if response.status_code != 200:
            print(f"[fetcher] Non-200 status: {response.status_code}")
            return None, "scraper_blocked"

        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            print(f"[fetcher] Non-HTML content type: {content_type}")
            return None, "scraper_blocked"

        text_lower = response.text.lower()
        soft_block_signals = [
            'subscribe to continue', 'subscribe to read',
            'sign in to read', 'create a free account',
            'javascript is required', 'enable javascript',
            'please enable cookies', 'access denied',
            'this content is for subscribers',
        ]
        for signal in soft_block_signals:
            if signal in text_lower and len(response.text) < 5000:
                print(f"[fetcher] Soft block detected: '{signal}'")
                return None, "scraper_blocked"

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("[fetcher] BeautifulSoup not installed!")
            return None, "scraper_blocked"

        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup(['script', 'style', 'nav', 'header',
                         'footer', 'aside', 'iframe', 'noscript',
                         'form', 'button']):
            tag.decompose()

        for class_name in ['navbar', 'nav-bar', 'cookie', 'banner',
                           'advertisement', 'ad-', 'sidebar',
                           'related-articles', 'newsletter']:
            for el in soup.find_all(class_=lambda x: x and class_name in str(x).lower()):
                el.decompose()

        content = None

        article = soup.find('article')
        if article:
            content = article.get_text(separator=' ', strip=True)
            print(f"[fetcher] Strategy 1 (article tag): {len(content)} chars")

        if not content or len(content) < 300:
            main = soup.find('main')
            if main:
                content = main.get_text(separator=' ', strip=True)
                print(f"[fetcher] Strategy 2 (main tag): {len(content)} chars")

        if not content or len(content) < 300:
            content_classes = [
                'article-body', 'article-content', 'article__body',
                'article__content', 'story-body', 'story__body',
                'post-content', 'post__content', 'entry-content',
                'content-body', 'articleBody', 'article-text',
                'story-content', 'page-content', 'body-content',
                'article-copy', 'js-article-body',
            ]
            for cls in content_classes:
                el = soup.find(class_=lambda x: x and cls in (
                    ' '.join(x) if isinstance(x, list) else str(x)
                ))
                if el:
                    candidate = el.get_text(separator=' ', strip=True)
                    if len(candidate) > 300:
                        content = candidate
                        print(f"[fetcher] Strategy 3 (class '{cls}'): {len(content)} chars")
                        break

        if not content or len(content) < 300:
            paragraphs = soup.find_all('p')
            content = ' '.join(
                p.get_text(strip=True) for p in paragraphs
                if len(p.get_text(strip=True)) > 40
            )
            print(f"[fetcher] Strategy 4 (paragraphs): {len(content)} chars")

        if not content or len(content) < 150:
            print(f"[fetcher] Insufficient content: {len(content) if content else 0} chars")
            return None, "scraper_blocked"

        content = ' '.join(content.split())
        if len(content) > 8000:
            content = content[:8000] + '...'

        print(f"[fetcher] Success: {len(content)} chars extracted")
        return content, None

    except Exception as e:
        print(f"[fetcher] Unexpected error: {e}")
        traceback.print_exc()
        return None, "scraper_blocked"


def generate_article_summary(title, content):
    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()

    print(f"[fetcher] Generating summary for: {title[:60]}")

    try:
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-2.5-flash-lite')

        prompt = f"""Summarise this news article in exactly 4-6 sentences. \
Be factual and concise. Include the key data points, findings, \
or announcements. Do not editorialize. Do not mention the publication name.

Article title: {title}

Article content:
{content}

Return only the summary text. No labels, no preamble."""

        response = model.generate_content(prompt)
        summary = response.text.strip()
        print(f"[fetcher] Summary generated: {len(summary)} chars")
        return summary

    except Exception as e:
        print(f"[fetcher] Summary generation error: {e}")
        return None
