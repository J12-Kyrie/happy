import os
import time
import requests
import json
import subprocess
import urllib3
from flask import Flask, request, jsonify, render_template, send_from_directory
from openai import OpenAI
from volcenginesdkarkruntime import Ark
# 引入图像处理库
from PIL import Image

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ================= 配置区域 =================
# ⚠️ 请务必确保这是你最新的 Pinggy 地址 (https开头)
PINGGY_URL = "https://iqvzl-2409-8d1e-6910-338-901e-4c8-23c6-bd3c.a.free.pinggy.link"

VOLC_API_KEY = "d61f814f-8733-42bd-b1e3-8a07bc1e1791"
# 初始化方舟客户端
ark_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=VOLC_API_KEY
)

CHATFIRE_API_KEY = "sk-pSgixPnLcUr23Kubw8TU2AoDjpks0kNBb4U5nPsKquIwyUFV" 
CHATFIRE_BASE_URL = "https://api.chatfire.cn/v1"
chatfire_client = OpenAI(api_key=CHATFIRE_API_KEY, base_url=CHATFIRE_BASE_URL)

PORT = 5001 
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    response = send_from_directory(UPLOAD_FOLDER, filename)
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

# ================== 核心功能：图片智能压缩 ==================
def compress_image(input_path, output_path, max_size_kb=300):
    """
    将图片压缩到指定大小（默认300KB以下），并统一转为JPEG。
    这能极大提高跨国传输的成功率。
    """
    try:
        with Image.open(input_path) as img:
            # 1. 转换模式，去除透明通道 (JPEG不支持透明)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 2. 限制最大分辨率 (例如最大宽/高 1024px)
            img.thumbnail((1024, 1024))
            
            # 3. 循环降低质量直到满足大小
            quality = 85
            while quality > 10:
                img.save(output_path, "JPEG", quality=quality)
                if os.path.getsize(output_path) / 1024 <= max_size_kb:
                    break
                quality -= 10
            
        print(f"📉 图片已压缩: {os.path.getsize(input_path)//1024}KB -> {os.path.getsize(output_path)//1024}KB")
        return True
    except Exception as e:
        print(f"⚠️ 图片压缩失败: {e}")
        return False

# ================== 核心功能：极速图床上传 ==================
def upload_to_bridge_host(file_path):
    """
    尝试上传到 vim-cn，超时时间极短(3s)，失败立即跳过，绝不拖慢网站。
    """
    print(f"🚀 尝试极速上传图床...")
    try:
        with open(file_path, 'rb') as f:
            # verify=False 解决 SSLEOFError
            # timeout=3 解决网站卡顿
            response = requests.post(
                'https://img.vim-cn.com/', 
                files={'name': f}, 
                verify=False, 
                timeout=3 
            )
            if response.status_code == 200:
                url = response.text.strip().replace('http://', 'https://')
                print(f"✅ 图床秒传成功: {url}")
                return url
    except Exception as e:
        print(f"⚠️ 图床跳过 (不影响流程): {e}")
    return None

# ================= 任务 1: 视频生成 =================
@app.route('/generate_video', methods=['POST'])
def generate_video():
    if 'image' not in request.files:
        return jsonify({"error": "没有上传图片"}), 400
    
    file = request.files['image']
    # 保存原图
    original_filename = f"src_{int(time.time())}_{file.filename}"
    original_path = os.path.join(UPLOAD_FOLDER, original_filename)
    file.save(original_path)

    # 1. 【关键步骤】生成压缩版图片
    # 只有压缩后的图片才适合在不稳定网络下传输
    compressed_filename = f"min_{original_filename}.jpg"
    compressed_path = os.path.join(UPLOAD_FOLDER, compressed_filename)
    
    if compress_image(original_path, compressed_path):
        target_path = compressed_path
        target_filename = compressed_filename
    else:
        target_path = original_path
        target_filename = original_filename

    # 2. 尝试图床中转 (优先使用)
    final_image_url = upload_to_bridge_host(target_path)
    
    # 3. 如果图床失败，回退到 Pinggy (但这次我们用的是压缩图，成功率极高！)
    if not final_image_url:
        public_url = PINGGY_URL.rstrip('/')
        final_image_url = f"{public_url}/uploads/{target_filename}"
        
    print(f"🌍 最终提交给 API 的图片地址: {final_image_url}")

    prompt_text = "基于参考图片生成视频，场景转换为温暖的北欧圣诞氛围。一位快乐、传统的圣诞老人带着魔法光环笑着步入画面，神奇地将红白圣诞帽戴在每个人的头上。雪花轻柔飘落，电影质感，高清晰度，暖色调。 --duration 5 --camerafixed false --watermark false"

    try:
        create_result = ark_client.content_generation.tasks.create(
            model="doubao-seedance-1-5-pro-251215",
            content=[
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": final_image_url}}
            ]
        )
        print(f"🚀 任务创建成功: {create_result.id}")
        return jsonify({"id": create_result.id, "status": "QUEUED"})

    except Exception as e:
        print(f"❌ 视频任务提交失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/check_video_status', methods=['GET'])
def check_video_status():
    task_id = request.args.get('task_id')
    try:
        get_result = ark_client.content_generation.tasks.get(task_id=task_id)
        status = get_result.status
        
        if status == "succeeded":
            if hasattr(get_result, 'content') and get_result.content:
                video_url = get_result.content.video_url
                return jsonify({
                    "status": "SUCCEEDED", 
                    "result": {"video_url": video_url}
                })
            else:
                return jsonify({"status": "FAILED", "error": "Result content missing"})
        elif status == "failed":
            err = get_result.error if hasattr(get_result, 'error') else "Unknown Error"
            return jsonify({"status": "FAILED", "error": str(err)})
        else:
            return jsonify({"status": status.upper()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= 任务 2: 语音处理 =================
def convert_webm_to_mp3(input_path, output_path):
    try:
        # 增加 -loglevel error 减少日志垃圾
        command = ['ffmpeg', '-y', '-i', input_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', '-loglevel', 'error', output_path]
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except:
        return False

@app.route('/process_audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio"}), 400

    audio_file = request.files['audio']
    timestamp = int(time.time())
    original_path = os.path.join(UPLOAD_FOLDER, f"rec_{timestamp}.webm")
    mp3_path = os.path.join(UPLOAD_FOLDER, f"rec_{timestamp}.mp3")
    audio_file.save(original_path)

    final_path = mp3_path if convert_webm_to_mp3(original_path, mp3_path) else original_path

    try:
        with open(final_path, "rb") as f:
            transcript = chatfire_client.audio.transcriptions.create(model="whisper-1", file=f)
        user_text = transcript.text
        print(f"🗣️ 用户说: {user_text}")
        
        completion = chatfire_client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": "你是圣诞老人，请用温暖、幽默的中文回复，不要太长。"},
                {"role": "user", "content": user_text}
            ]
        )
        ai_text = completion.choices[0].message.content
        print(f"🎅 AI回复: {ai_text}")

        try:
            speech_response = chatfire_client.audio.speech.create(
                model="tts-1", 
                voice="alloy", 
                input=ai_text
            )
            audio_content = speech_response.content
            
            if len(audio_content) < 1024:
                try:
                    error_text = audio_content.decode('utf-8')
                    print(f"❌ TTS 接口返回了非音频数据: {error_text}")
                    return jsonify({"error": f"TTS服务异常: {error_text}"}), 500
                except: pass

            tts_save_path = os.path.join(UPLOAD_FOLDER, f"reply_{timestamp}.mp3")
            with open(tts_save_path, "wb") as f:
                f.write(audio_content)
            
            return audio_content, 200, {'Content-Type': 'audio/mpeg'}

        except Exception as e:
            print(f"❌ TTS 生成步骤失败: {e}")
            return jsonify({"error": f"TTS生成失败: {str(e)}"}), 500

    except Exception as e:
        print(f"❌ 语音处理链错误: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"🚀 服务已启动 | Pinggy: {PINGGY_URL}")
    app.run(debug=True, port=PORT, threaded=True)