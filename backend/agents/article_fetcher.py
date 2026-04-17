import os
import requests
import traceback
from bs4 import BeautifulSoup


def fetch_article_content(url):
    print(f"[fetcher] Fetching article: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        print(f"[fetcher] Status: {response.status_code}")

        if response.status_code in (403, 401, 429):
            return None, "scraper_blocked"
        if response.status_code == 200 and 'text/html' not in response.headers.get('Content-Type', ''):
            return None, "scraper_blocked"
        if response.status_code != 200:
            return None, f"http_error_{response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup(['script', 'style', 'nav', 'header',
                         'footer', 'aside', 'advertisement',
                         'iframe', 'noscript', 'form']):
            tag.decompose()

        content = None

        article = soup.find('article')
        if article:
            content = article.get_text(separator=' ', strip=True)

        if not content or len(content) < 200:
            main = soup.find('main')
            if main:
                content = main.get_text(separator=' ', strip=True)

        if not content or len(content) < 200:
            for class_name in [
                'article-body', 'article-content', 'story-body',
                'post-content', 'entry-content', 'content-body',
                'article__body', 'article__content', 'story__body',
                'post__content', 'articleBody', 'article-text',
            ]:
                div = soup.find(class_=class_name)
                if div:
                    content = div.get_text(separator=' ', strip=True)
                    if len(content) > 200:
                        break

        if not content or len(content) < 200:
            paragraphs = soup.find_all('p')
            content = ' '.join(
                p.get_text(strip=True) for p in paragraphs
                if len(p.get_text(strip=True)) > 50
            )

        if not content or len(content) < 100:
            return None, "scraper_blocked"

        content = ' '.join(content.split())

        if len(content) > 8000:
            content = content[:8000] + '...'

        print(f"[fetcher] Extracted {len(content)} characters")
        return content, None

    except requests.exceptions.Timeout:
        print(f"[fetcher] Timeout for {url}")
        return None, "scraper_blocked"
    except requests.exceptions.ConnectionError:
        print(f"[fetcher] Connection error for {url}")
        return None, "scraper_blocked"
    except Exception as e:
        print(f"[fetcher] Error: {e}")
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
