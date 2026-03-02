import os
import re
import json
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- روابط الأخبار ---
urls = [
    "https://www.pncecs.plo.ps/?page_id=5867",
    "https://www.pncecs.plo.ps/?p=5841",
    "https://www.pncecs.plo.ps/?p=5785",
    "https://www.pncecs.plo.ps/?p=5827",
    "https://www.pncecs.plo.ps/?p=5832",
    "https://www.pncecs.plo.ps/?p=5822",
    "https://www.pncecs.plo.ps/?p=5811",
    "https://www.pncecs.plo.ps/?p=5802",
    "https://www.pncecs.plo.ps/?p=5791",
    "https://www.pncecs.plo.ps/?p=5853",
    "https://www.pncecs.plo.ps/?p=5777",
    "https://www.pncecs.plo.ps/?p=5769",
    "https://www.pncecs.plo.ps/?p=5761",
    "https://www.pncecs.plo.ps/?p=5752"
]

# --- المسارات ---
image_dir = os.path.join("static", "images", "cultural_forum")
os.makedirs(image_dir, exist_ok=True)

json_path = "cultural_forum_data.json"
existing_data = []

if os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        existing_data = json.load(f)

titles_in_json = [x["title"] for x in existing_data]

# --- دالة استخراج التاريخ ---
def extract_date(text):
    """
    تبحث عن أنماط تواريخ عربية مثل 27/08/2018 أو 3/9/2018
    """
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if match:
        d, m, y = match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return None


# --- استخراج محتوى صفحة واحدة ---
def scrape_page(url):
    try:
        print(f"📰 جاري معالجة: {url}")
        res = requests.get(url, verify=False, timeout=20)
        if res.status_code != 200:
            print(f"⚠️ لم يتم الوصول إلى الصفحة: {url}")
            return None

        soup = BeautifulSoup(res.text, "html.parser")

        # --- العنوان ---
        title_tag = soup.find("h1", class_="entry-title")
        title = title_tag.get_text(strip=True) if title_tag else "بدون عنوان"

        # --- المحتوى ---
        content_div = soup.find("div", class_="entry-content")
        content = str(content_div) if content_div else ""

        # --- استخراج التاريخ من النص ---
        text_for_date = content_div.get_text(" ", strip=True) if content_div else ""
        date = extract_date(text_for_date)

        # --- استخراج جميع الصور ---
        image_filenames = []
        if content_div:
            img_tags = content_div.find_all("img")
            for img_tag in img_tags:
                img_url = img_tag.get("src")
                if not img_url:
                    continue

                filename = os.path.basename(img_url.split("?")[0])
                image_path = os.path.join(image_dir, filename)

                # تحميل الصورة إذا لم تكن موجودة
                if not os.path.exists(image_path):
                    try:
                        img_data = requests.get(img_url, verify=False, timeout=10).content
                        with open(image_path, "wb") as f:
                            f.write(img_data)
                        print(f"✅ تم تحميل الصورة: {filename}")
                    except Exception as e:
                        print(f"⚠️ فشل تحميل الصورة {img_url}: {e}")
                        continue
                else:
                    print(f"⏭️ الصورة موجودة مسبقًا: {filename}")

                if filename not in image_filenames:
                    image_filenames.append(filename)

        return {
            "title": title,
            "content": content,
            "date": date or "",
            "images": image_filenames
        }

    except Exception as e:
        print(f"❌ خطأ أثناء معالجة {url}: {e}")
        return None


# --- التنفيذ ---
new_data = []
for link in urls:
    result = scrape_page(link)
    if result:
        # إذا الخبر موجود مسبقًا → حدثه بدل إضافته
        updated = False
        for item in existing_data:
            if item["title"] == result["title"]:
                item.update(result)
                updated = True
                break
        if not updated:
            new_data.append(result)

# دمج الجديد مع القديم
if new_data:
    existing_data.extend(new_data)

# حفظ التحديثات
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(existing_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ تم تحديث {len(existing_data)} خبرًا في {json_path}")
print(f"📁 الصور محفوظة في: {image_dir}")
