from flask import Flask, request, jsonify
import requests
import base64
from io import BytesIO

app = Flask(__name__)

# Thay đổi các giá trị này
PAGE_ACCESS_TOKEN = "EAAZAmeBmEFmIBPvP059wFc6T15CTXvAcZBIZBXm9evzBMOXd1QYk57QGpnJJ5vGoSgmJpvnmI19YLzxZC1nxaHZBYFZCXA3KQZBj1CTLHP5ej6vdwiPiOKgaE48LIqktvrazJVqsm1QsDLYNxd8zKlnnGxexLZAMEIoO9wWUF55gxpOPZBws9fFX9yZBGIGzi9e1ZBrsxr0fDJWlokZAFQDuNlZAppa3U"  
PAGE_ID = "791285820738242"

# API đăng ảnh lên Facebook Page
@app.route("/api/postimage", methods=["POST"])
def post_image_to_facebook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Thiếu JSON body"}), 400

        # Lấy caption
        content = data.get("content", "")
        if not content:
            return jsonify({"success": False, "error": "Thiếu caption"}), 400

        # Lấy base64 image
        base64_image = data.get("image_base64")
        if not base64_image:
            return jsonify({"success": False, "error": "Thiếu dữ liệu ảnh base64"}), 400

        # Nếu base64 có prefix data:image/png;base64,... thì bỏ đi
        if base64_image.startswith("data:image"):
            base64_image = base64_image.split(",")[1]

        try:
            image_binary = base64.b64decode(base64_image)
        except Exception:
            return jsonify({"success": False, "error": "Ảnh base64 không hợp lệ"}), 400

        print(f"📝 Nội dung: {content[:100]}...")
        print(f"🖼️ Size ảnh: {len(image_binary)} bytes")

        # Gọi Facebook Graph API
        url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/photos"
        payload = {
            "message": content,
            "access_token": PAGE_ACCESS_TOKEN
        }
        files = {
            "source": ("image.png", image_binary, "image/png")
        }

        response = requests.post(url, data=payload, files=files)

        if response.status_code == 200:
            result = response.json()
            post_id = result.get("post_id", result.get("id"))
            return jsonify({
                "success": True,
                "post_id": post_id,
                "message": "Đăng ảnh thành công!",
                "data": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": response.json()
            }), response.status_code

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# API test kết nối
@app.route("/api/test", methods=["GET"])
def test_connection():
    try:
        url = f"https://graph.facebook.com/v21.0/{PAGE_ID}"
        params = {"fields": "name", "access_token": PAGE_ACCESS_TOKEN}
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "success": True,
                "page_name": data.get("name"),
                "message": "Kết nối thành công!"
            })
        else:
            return jsonify({
                "success": False,
                "error": response.json()
            }), response.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

