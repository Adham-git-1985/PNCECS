import requests
from bs4 import BeautifulSoup
import json
import time

base_url = "https://www.pncecs.plo.ps"
category_id = 3  # رقم التصنيف
page_number = 1
id_counter = 1

all_news = []
visited_links = set()

def extract_news_links(page_url):
    print(f"📄 معالجة الصفحة: {page_url}")
    resp = requests.get(page_url)
    resp.encoding = 'utf-8'
    if resp.status_code != 200:
        print("❌ فشل تحميل الصفحة.")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    links = []

    for article in soup.find_all("h2", class_="entry-title"):
        a_tag = article.find("a")
        if a_tag and a_tag["href"] not in visited_links:
            title = a_tag.text.strip()
            link = a_tag["href"]
            links.append({"title": title, "link": link})
            visited_links.add(link)

    return links

def extract_full_content(news_item):
    try:
        response = requests.get(news_item['link'])
        response.encoding = 'utf-8'
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            content_div = soup.find('div', class_='entry-content')
            if content_div:
                content_text = content_div.get_text(separator='\n', strip=True)
                news_item['content'] = content_text
            else:
                news_item['content'] = "❌ لم يتم العثور على المحتوى."
        else:
            news_item['content'] = "❌ فشل تحميل صفحة التفاصيل."
    except Exception as e:
        news_item['content'] = f"⚠️ خطأ: {str(e)}"
    return news_item

# التصفح عبر الصفحات
while True:
    page_url = f"{base_url}/?cat={category_id}&paged={page_number}"
    news_links = extract_news_links(page_url)

    if not news_links:
        print("🛑 لم يتم العثور على أخبار جديدة. التوقف.")
        break

    print(f"✅ تم العثور على {len(news_links)} خبر في الصفحة {page_number}")
    for item in news_links:
        item['id'] = id_counter
        id_counter += 1
        full_item = extract_full_content(item)
        all_news.append(full_item)
        print(f"📰 تم استخراج: {item['title'][:50]}...")
        time.sleep(1)

    page_number += 1

# حفظ النتائج
with open("full_news.json", "w", encoding="utf-8") as f:
    json.dump(all_news, f, ensure_ascii=False, indent=4)

print(f"\n✅✅ تم استخراج {len(all_news)} خبرًا من كل الصفحات وحفظها في full_news.json")
