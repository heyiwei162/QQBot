import random, json
with open("./cos_all.json", "r", encoding="utf-8") as f:
    tips = json.load(f)
            

tip = random.choice(tips)
# tip = tips[110]
print(f"找到的帖子{tip}")
urls = tip["urls"]
print(type(urls[0]['width']))