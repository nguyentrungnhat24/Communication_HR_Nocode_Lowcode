import os
import io
import base64
import requests
import mimetypes
import re
import json
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()

app = Flask(__name__)

# Hugging Face API (nếu bạn muốn dùng AI gen background)
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"

# Thay đổi các giá trị này
ACCESS_TOKEN = "EAAZAmeBmEFmIBPvP059wFc6T15CTXvAcZBIZBXm9evzBMOXd1QYk57QGpnJJ5vGoSgmJpvnmI19YLzxZC1nxaHZBYFZCXA3KQZBj1CTLHP5ej6vdwiPiOKgaE48LIqktvrazJVqsm1QsDLYNxd8zKlnnGxexLZAMEIoO9wWUF55gxpOPZBws9fFX9yZBGIGzi9e1ZBrsxr0fDJWlokZAFQDuNlZAppa3U"  
PAGE_ID = "791285820738242"


# Fonts
FONT_BOLD = "DejaVuSans-Bold.ttf"
FONT_REG = "DejaVuSans.ttf"


# -----------------------
# Helper: hex → rgb
def hex_to_rgb(hx):
    hx = hx.lstrip('#')
    return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))


# -----------------------
# 🎨 Hàm tạo banner theo variant
def create_banner_variant(test_id, product_name, style, variant_id,
                          bg_color, text_color, layout, price, discount,
                          original_price, image_url, description):

    background = Image.new("RGB", (1200, 628), color=hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(background)

    # Fonts
    font_head = ImageFont.truetype(FONT_BOLD, 64)
    font_sub = ImageFont.truetype(FONT_REG, 32)

    # Headline
    draw.text((50, 50), f"{product_name}", fill=text_color, font=font_head)

    # Giá + discount
    if discount:
        draw.text((50, 150), f"Now: ${price}  (-{discount}%)", fill=text_color, font=font_sub)
        draw.text((50, 200), f"Was: ${original_price}", fill=text_color, font=font_sub)

    # Description
    draw.text((50, 280), description, fill=text_color, font=font_sub)

    # CTA button
    button_w, button_h = 280, 70
    button_x, button_y = 50, 500
    draw.rounded_rectangle([button_x, button_y, button_x + button_w, button_y + button_h],
                           radius=15, fill="orange")
    draw.text((button_x + 60, button_y + 15), "Buy Now", fill="white", font=font_sub)

    # Nếu có image_url → tải ảnh sản phẩm
    if image_url:
        try:
            resp = requests.get(image_url)
            if resp.status_code == 200:
                prod_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                prod_img.thumbnail((400, 400))
                background.paste(prod_img, (700, 150), prod_img)
        except Exception as e:
            print("⚠️ Lỗi tải image_url:", e)

    return background


# -----------------------
# API: sinh banners từ list JSON
@app.route("/generate_banners", methods=["POST"])
def generate_banners():
    data = request.json  # Nhận mảng JSON (6 items)
    result = []

    for item in data:
        test_id = item.get("testId", "001")
        product_name = item.get("productName", "Product")
        style = item.get("style", "Minimal Professional")
        variant_id = item.get("variantId", "A1")

        bg_color = item.get("backgroundColor", "#FFFFFF")
        text_color = item.get("textColor", "#000000")
        layout = item.get("layoutStyle", "default")
        price = item.get("price", "")
        discount = item.get("discount", "")
        original_price = item.get("originalPrice", "")
        image_url = item.get("imageUrl", "")
        description = item.get("description", "")

        # Sinh ảnh
        img = create_banner_variant(
            test_id, product_name, style, variant_id,
            bg_color, text_color, layout, price, discount,
            original_price, image_url, description
        )

        # Convert → base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        result.append({
            "filename": f"{variant_id}.png",
            "variantId": variant_id,
            "product_name": product_name,
            "image": img_base64
        })

    return jsonify(result)

@app.route("/generate_banner_one", methods=["POST"])
def generate_banner_one():
    item = request.json  # chỉ 1 object

    test_id = item.get("testId", "001")
    product_name = item.get("productName", "Product")
    style = item.get("style", "Minimal Professional")
    variant_id = item.get("variantId", "A1")

    bg_color = item.get("backgroundColor", "#FFFFFF")
    text_color = item.get("textColor", "#000000")
    layout = item.get("layoutStyle", "default")
    price = item.get("price", "")
    discount = item.get("discount", "")
    original_price = item.get("originalPrice", "")
    image_url = item.get("imageUrl", "")
    description = item.get("description", "")

    img = create_banner_variant(
        test_id, product_name, style, variant_id,
        bg_color, text_color, layout, price, discount,
        original_price, image_url, description
    )

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return jsonify({
        "filename": f"{variant_id}.png",
        "variantId": variant_id,
        "product_name": product_name,
        "image": img_base64
    })


def upload_photo_to_facebook(image_base64_str, filename):
    """Upload 1 ảnh lên Facebook, trả về media_fbid"""
    
    # Nếu có tiền tố data URI, loại bỏ
    if isinstance(image_base64_str, str) and image_base64_str.startswith("data:image"):
        image_base64_str = image_base64_str.split(",")[1]

    # loại bỏ khoảng trắng, xuống dòng
    image_base64_str = "".join(image_base64_str.split())

    try:
        img_bytes = base64.b64decode(image_base64_str, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid Base64 for file {filename}: {e}")

    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "application/octet-stream"

    url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/photos"
    files = {
        "source": (filename, img_bytes, mime_type)
    }
    payload = {
        "access_token": ACCESS_TOKEN,
        "published": "false"
    }

    response = requests.post(url, data=payload, files=files)
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code} {response.text}")
    response.raise_for_status()
    return response.json()["id"]

def create_facebook_post(caption, media_fbids):
    """Tạo 1 bài post với nhiều ảnh"""
    url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/feed"
    attached_media = [{"media_fbid": fbid} for fbid in media_fbids]
    payload = {
        "access_token": ACCESS_TOKEN,
        "message": caption,
        "attached_media": json.dumps(attached_media)  # string JSON
    }
    response = requests.post(url, data=payload)  # dùng data, không json
    response.raise_for_status()
    return response.json()

@app.route("/post_facebook", methods=["POST"])
def post_facebook():
    data = request.get_json()
    posts = data.get("posts", [])
    if not posts:
        return jsonify({"error": "Missing posts"}), 400

    results = []

    for post in posts:
        caption = post.get("caption1") or post.get("caption2") or post.get("caption") # Adjusted key to match your JSON
        images = post.get("images", [])
        if not caption or not images:
            return jsonify({"error": "Each post must have caption and images"}), 400

        media_fbids = []
        for img in images:
            # Gửi trực tiếp Base64 string vào hàm
            media_fbid = upload_photo_to_facebook(img["binary"], img["filename"])
            media_fbids.append(media_fbid)

        post_response = create_facebook_post(caption, media_fbids)
        results.append(post_response)

    return jsonify(results)

if __name__ == "__main__": 
    os.makedirs("/tmp", exist_ok=True) 
    print("=" * 50) 
    print("🚀 AI Visual Creation Agent - Hybrid Mode") 
    print("=" * 50) 
    if HF_API_TOKEN: 
        print("✅ Hugging Face: ENABLED")
        print(" Set useAI=true in request to use AI backgrounds")
    else:
        print("⚠️ Hugging Face: DISABLED (no HF_API_TOKEN)")
        print(" Will use PIL fallback for all generations")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
    