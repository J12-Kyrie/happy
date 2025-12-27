import os
import time
import json
import urllib3
import random
import subprocess
import binascii  # 新增：用于解码 MiniMax 的 Hex 音频数据
import requests  # 确保导入 requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from openai import OpenAI
from volcenginesdkarkruntime import Ark
from PIL import Image

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ================= 配置与常量 =================
# ⚠️ Pinggy URL 必须保持最新
PINGGY_URL = "https://sugsi-39-144-46-197.a.free.pinggy.link".rstrip('/')

# API KEY 配置
VOLC_API_KEY = "d61f814f-8733-42bd-b1e3-8a07bc1e1791"
CHATFIRE_API_KEY = "sk-pSgixPnLcUr23Kubw8TU2AoDjpks0kNBb4U5nPsKquIwyUFV"
CHATFIRE_BASE_URL = "https://api.chatfire.cn/v1"

# MiniMax 配置 (复刻声音)
# ⚠️ 请在此处填入你的 MiniMax API Key
MINIMAX_API_KEY = "sk-api-b6WXu31zaHk3Bo1ftFgBRwQUR1Y8mJxFtbnLGt0H56vFT-1_Gl9Bxn4t8AlDmIHSzXyCtW-p476ux3fCd1tgHOyi_sHnXQFDT27gxowmpXQyjaSqdNO95y4"  
MINIMAX_GROUP_ID = "2004506585677701929"
MINIMAX_VOICE_ID = "Kyrie_Happy_Voice_01"
MINIMAX_URL = "https://api.minimaxi.com/v1/t2a_v2"

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_PROMPT_PATH = '/Users/kyrie/Desktop/happy/python_app/system_content.txt'
WISHES_JSON_PATH = '/Users/kyrie/Desktop/happy/data/text.json'

# 静态文件目录
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 客户端初始化
ark_client = Ark(base_url="https://ark.cn-beijing.volces.com/api/v3", api_key=VOLC_API_KEY)
chatfire_client = OpenAI(api_key=CHATFIRE_API_KEY, base_url=CHATFIRE_BASE_URL)

@app.route('/')
def index():
    return render_template('index.html')

# ================== 核心：本地文件服务 ==================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ================== 辅助函数：本地图片压缩 ==================
def compress_image_local(input_path, max_size_kb=300):
    try:
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            quality = 90
            while quality > 10:
                img.save(input_path, "JPEG", quality=quality)
                if os.path.getsize(input_path) / 1024 <= max_size_kb:
                    break
                quality -= 10
        return True
    except Exception as e:
        print(f"压缩失败: {e}")
        return False

# ================== 业务接口 1: 获取愿望 ==================
@app.route('/get_new_year_wishes')
def get_new_year_wishes():
    default_wishes = ["Happy New Year 2026!", "万事如意", "岁岁平安"]
    try:
        if os.path.exists(WISHES_JSON_PATH):
            with open(WISHES_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                wishes = [item.get('text') for item in data if isinstance(item, dict) and 'text' in item]
                if wishes:
                    random.shuffle(wishes)
                    return jsonify(wishes)
    except Exception as e:
        print(f"读取愿望失败: {e}")
    return jsonify(default_wishes)

# ================== 业务接口 2: 视频生成 ==================
@app.route('/generate_video', methods=['POST'])
def generate_video():
    if 'image' not in request.files: 
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['image']
    ts = int(time.time())
    filename = f"gen_{ts}.jpg"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    file.save(file_path)
    print(f"图片已保存至: {file_path}")

    compress_image_local(file_path)
    img_url = f"{PINGGY_URL}/uploads/{filename}"
    print(f"生成图片公网链接: {img_url}")

    prompt = (
        "The family continues walking as a giant, translucent clock of light appears in the sky, counting down. "
        "At the stroke of midnight, a magnificent explosion of multi-colored fireworks fills the frame. "
        "Epic scale, slow-motion celebration, cinematic fireworks. "
        "--duration 12 --camerafixed false --watermark false"
    )

    try:
        res = ark_client.content_generation.tasks.create(
            model="doubao-seedance-1-5-pro-251215",
            content=[{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": img_url}}]
        )
        return jsonify({"id": res.id, "status": "QUEUED"})
    except Exception as e:
        print(f"Volcengine API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/check_video_status', methods=['GET'])
def check_video_status():
    task_id = request.args.get('task_id')
    if not task_id: return jsonify({"error": "No task_id"}), 400
    try:
        res = ark_client.content_generation.tasks.get(task_id=task_id)
        if res.status == "succeeded":
            return jsonify({"status": "SUCCEEDED", "result": {"video_url": res.content.video_url}})
        elif res.status == "failed":
            err_msg = getattr(res, 'error', 'Unknown Error')
            print(f"Video Task Failed: {err_msg}")
            return jsonify({"status": "FAILED", "error": str(err_msg)})
        return jsonify({"status": res.status.upper()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================== 业务接口 3: 语音对话 (MiniMax 复刻声音版) ==================
@app.route('/process_audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files: 
        return jsonify({"error": "No audio"}), 400
    
    ts = int(time.time())
    webm_path = os.path.join(UPLOAD_FOLDER, f"rec_{ts}.webm")
    mp3_path = os.path.join(UPLOAD_FOLDER, f"rec_{ts}.mp3")

    # 1. 保存原始录音
    request.files['audio'].save(webm_path)
    print(f"原始录音已保存: {webm_path}")

    # 2. 格式转换 (WebM -> MP3)
    try:
        cmd = ['ffmpeg', '-y', '-i', webm_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', '-loglevel', 'error', mp3_path]
        subprocess.run(cmd, check=True)
        final_audio_path = mp3_path
        print(f"转码成功: {mp3_path}")
    except Exception as e:
        print(f"FFmpeg 转码失败: {e}")
        final_audio_path = webm_path

    try:
        # 3. STT: 语音转文字 (Whisper)
        with open(final_audio_path, "rb") as audio_file:
            user_text = chatfire_client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            ).text
        print(f"识别到的文字: {user_text}")
        
        # 4. Chat: 生成回复 (GPT)
        sys_prompt = "You are Santa Claus. Keep it short and warm."
        if os.path.exists(SYSTEM_PROMPT_PATH):
            with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f: 
                sys_prompt = f.read()

        completion = chatfire_client.chat.completions.create(
            model="gpt-5.1-chat-latest",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        ai_text = completion.choices[0].message.content
        print(f"AI回复: {ai_text}")

        # 5. TTS: 文字转语音 (使用 MiniMax 复刻声音)
        print("正在调用 MiniMax 生成复刻语音...")
        
        payload = {
            "model": "speech-02-turbo",
            "text": ai_text,
            "stream": False,
            "voice_setting": {
                "voice_id": MINIMAX_VOICE_ID,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0
            },
            "audio_setting": {
                "sample_rate": 32000,
                "format": "mp3",
                "channel": 1
            }
        }
        
        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json",
            "x-group-id": MINIMAX_GROUP_ID
        }

        response = requests.post(MINIMAX_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "audio" in data["data"]:
                # 将 Hex 编码转为二进制
                audio_binary = binascii.unhexlify(data["data"]["audio"])
                # 直接返回二进制流，无需保存到本地，前端可直接播放
                return audio_binary, 200, {'Content-Type': 'audio/mpeg'}
            else:
                print(f"MiniMax 响应异常: {data}")
                return jsonify({"error": "MiniMax response missing audio data"}), 500
        else:
            print(f"MiniMax API 错误: {response.status_code} - {response.text}")
            return jsonify({"error": f"MiniMax API failed: {response.text}"}), 500

    except Exception as e:
        print(f"Audio Logic Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001, threaded=True)