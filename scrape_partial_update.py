import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from hashlib import md5

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# تحميل الأخبار الحالية
def load_existing_news(path="full_news.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            news = json.load(f)
            return news, set(item["title"] for item in news)
    except FileNotFoundError:
        return [], set()

# استخراج روابط الأخبار
def extract_news_links(page_url):
    response = requests.get(page_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []

    for article in soup.find_all("h2", class_="entry-title"):
        a_tag = article.find("a")
        if a_tag:
            title = a_tag.text.strip()
            link = a_tag["href"]
            links.append({"title": title, "link": link})

    return links

# استخراج المحتوى الكامل
def extract_full_content(news_item):
    try:
        response = requests.get(news_item['link'])
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find('div', class_='entry-content')
        content = content_div.get_text(separator='\n', strip=True) if content_div else ''
        news_item['content'] = content or "❌ لم يتم العثور على المحتوى."
    except Exception as e:
        news_item['content'] = f"⚠️ خطأ: {str(e)}"
    return news_item

# تحديث الأخبار
def update_news():
    base_url = "https://www.pncecs.plo.ps"
    page_url = f"{base_url}/?cat=3"

    existing_news, existing_titles = load_existing_news()
    new_links = extract_news_links(page_url)
    new_items = []

    for item in new_links:
        if item["title"] not in existing_titles:
            logging.info(f"🆕 إضافة خبر: {item['title'][:50]}")
            full_item = extract_full_content(item)
            full_item["url"] = item["link"]
            full_item["id"] = md5(item["link"].encode()).hexdigest()
            new_items.append(full_item)
            time.sleep(1)

    updated_news = new_items + existing_news

    with open("full_news.json", "w", encoding="utf-8") as f:
        json.dump(updated_news, f, ensure_ascii=False, indent=4)

    logging.info(f"\n✅ تم تحديث الملف. أضيف {len(new_items)} خبر جديد.")

if __name__ == "__main__":
    update_news()
