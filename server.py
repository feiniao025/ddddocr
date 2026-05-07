from io import BytesIO
import cv2
import numpy as np
import requests
from PIL import Image
from flask import Flask, request, jsonify
import ddddocr
import logging
import re
import base64

app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ==========================
# 修复：小写 DdddOcr
# ==========================
ocr = ddddocr.DdddOcr()
det = ddddocr.DdddOcr(det=True)

def get_image_bytes(image_data):
    if isinstance(image_data, bytes):
        return image_data
    elif image_data.startswith('http'):
        response = requests.get(image_data, timeout=10, verify=False)
        response.raise_for_status()
        return response.content
    elif isinstance(image_data, str):
        return base64.b64decode(image_data)
    else:
        raise ValueError("不支持的图片格式")

def image_to_base64(image, format='PNG'):
    buffered = BytesIO()
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

@app.route('/capcode', methods=['POST'])
def capcode():
    try:
        data = request.json
        sliding = data['slidingImage']
        back = data['backImage']
        simple_target = data.get('simpleTarget', True)
        
        s_bytes = get_image_bytes(sliding)
        b_bytes = get_image_bytes(back)
        res = ocr.slide_match(s_bytes, b_bytes, simple_target=simple_target)
        return jsonify(result=res['target'][0])
    
    except Exception as e:
        return jsonify(error=f"处理失败: {str(e)}"), 500

@app.route('/slideComparison', methods=['POST'])
def slideComparison():
    try:
        data = request.json
        sliding = data['slidingImage']
        back = data['backImage']
        
        s_bytes = get_image_bytes(sliding)
        b_bytes = get_image_bytes(back)
        res = ocr.slide_comparison(s_bytes, b_bytes)
        return jsonify(result=res['target'][0])
    
    except Exception as e:
        return jsonify(error=f"处理失败: {str(e)}"), 500

@app.route('/classification', methods=['POST'])
def classification():
    try:
        data = request.json
        img_bytes = get_image_bytes(data['image'])
        return jsonify(result=ocr.classification(img_bytes))
    except Exception as e:
        return jsonify(error=f"处理失败: {str(e)}"), 500

@app.route('/detection', methods=['POST'])
def detection():
    try:
        data = request.json
        img_bytes = get_image_bytes(data['image'])
        return jsonify(result=det.detection(img_bytes))
    except Exception as e:
        return jsonify(error=f"处理失败: {str(e)}"), 500

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        img_bytes = get_image_bytes(data['image'])
        expr = ocr.classification(img_bytes)
        expr = re.sub('=.*$', '', expr)
        # 修复：正则加 r 前缀
        expr = re.sub(r'[^0-9+\-*/()]', '', expr)
        
        return jsonify(result=round(eval(expr), 2))
    except:
        return jsonify(error="计算失败"), 500

@app.route('/crop', methods=['POST'])
def crop():
    try:
        data = request.json
        url = data['image']
        y = int(data['y_coordinate'])
        
        img = Image.open(BytesIO(requests.get(url, timeout=10).content))
        part1 = img.crop((0, 0, img.width, y))
        part2 = img.crop((0, y*2, img.width, img.height))
        
        return jsonify(
            slidingImage=image_to_base64(part1),
            backImage=image_to_base64(part2)
        )
    except Exception as e:
        return jsonify(error=f"裁剪失败: {str(e)}"), 500

@app.route('/select', methods=['POST'])
def select():
    try:
        data = request.json
        img_bytes = get_image_bytes(data['image'])
        arr = np.frombuffer(img_bytes, np.uint8)
        im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        bboxes = det.detection(img_bytes)
        
        result = []
        for box in bboxes:
            x1, y1, x2, y2 = map(int, box)
            crop = im[y1:y2, x1:x2]
            _, buf = cv2.imencode('.png', crop)
            b64 = base64.b64encode(buf).decode()
            text = ocr.classification(b64)
            result.append({text: box})
        
        return jsonify(result)
    except Exception as e:
        return jsonify(error=f"点选识别失败: {str(e)}"), 500

@app.route('/')
def index():
    return '{"status": "ok", "msg": "ddddocr API 运行正常"}'

if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=7777,
        threaded=True,
        debug=False
    )
