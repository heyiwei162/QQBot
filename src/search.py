import requests
from PIL import Image
import pytesseract

# ===================== 配置区 =====================
API_TOKEN = "bTz2cn3W00SU5K53fuUccP2iYJdbnIgNlAHUCD8ddAuH9cUo2Y9zfmplbbrDZc"
STUDY_API_URL = "https://study.jszkk.com/api/open/seek"
HEADERS = {
    "Authorization": API_TOKEN,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"
}
# =================================================

# 本地图片OCR识别
def ocr_local_image(img_path: str):
    try:
        img = Image.open(img_path)
        # chi_sim 中文包，没有中文识别包会乱码
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text.strip()
    except Exception as e:
        print("图片识别失败：", e)
        return ""

# 文本搜题
def search_by_text(question_text: str):
    if not question_text:
        return {"err": "未识别到题目文字"}
    params = {"q": question_text}
    try:
        resp = requests.get(STUDY_API_URL, headers=HEADERS, params=params, timeout=12)
        data = resp.json()
        return data
    except Exception as e:
        return {"err": f"请求异常:{str(e)}"}

# 入口：本地图片搜题
def local_img_search(type, scr):
    if type == 0:
        text = scr
    elif type == 1:
        text = ocr_local_image(scr)
    print("识别文字:\n", text)
    return search_by_text(text)


# ============调用示例============
if __name__ == "__main__":
    result = search_by_text("计算机的特点是（）。")
    print("搜题结果：", result)