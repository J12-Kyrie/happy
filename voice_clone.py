import requests
import json
import os
import binascii  # 移到顶部

# ================= 配置区域 =================
API_KEY = "sk-api-b6WXu31zaHk3Bo1ftFgBRwQUR1Y8mJxFtbnLGt0H56vFT-1_Gl9Bxn4t8AlDmIHSzXyCtW-p476ux3fCd1tgHOyi_sHnXQFDT27gxowmpXQyjaSqdNO95y4"
GROUP_ID = "2004506585677701929"  
BASE_URL = "https://api.minimaxi.com/v1"

# 本地文件路径 (建议使用绝对路径或确保文件在当前目录)
LOCAL_FILE_PATH = "/Users/kyrie/Desktop/happy/data/12.m4a"
# 自定义音色ID
CUSTOM_VOICE_ID = "Kyrie_Happy_Voice_01"

# 修复 1: 在 Header 中加入 Group ID (很多 MiniMax 接口需要)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "x-group-id": GROUP_ID  # 关键修复：添加 Group ID 到 Header
}

def run_voice_clone_pipeline():
    # -------------------------------------------------
    # Step 1: 上传音频文件
    # -------------------------------------------------
    print(f"1. 正在上传文件: {LOCAL_FILE_PATH} ...")
    upload_url = f"{BASE_URL}/files/upload"
    
    file_id = None
    
    if not os.path.exists(LOCAL_FILE_PATH):
        print(f"❌ 错误：找不到文件 {LOCAL_FILE_PATH}")
        return

    try:
        with open(LOCAL_FILE_PATH, "rb") as f:
            files = {"file": f}
            data = {"purpose": "voice_clone"}
            # requests 会自动处理 multipart/form-data 的 Content-Type
            resp = requests.post(upload_url, headers=headers, files=files, data=data)
            
        resp_json = resp.json()
        if resp.status_code == 200 and "file" in resp_json:
            file_id = resp_json["file"]["file_id"]
            print(f"✅ 上传成功，File ID: {file_id}")
        else:
            print(f"❌ 上传失败: {resp.text}")
            return # 上传失败则无法继续

    except Exception as e:
        print(f"❌ 上传过程发生异常: {e}")
        return

    # -------------------------------------------------
    # Step 2: 注册复刻音色
    # -------------------------------------------------
    print(f"2. 正在注册音色 ID: {CUSTOM_VOICE_ID} ...")
    clone_url = f"{BASE_URL}/voice_clone"
    
    payload = {
        "file_id": file_id,
        "voice_id": CUSTOM_VOICE_ID
    }
    
    # 克隆和合成接口需要 JSON 类型
    json_headers = headers.copy()
    json_headers["Content-Type"] = "application/json"
    
    resp = requests.post(clone_url, headers=json_headers, json=payload)
    
    if resp.status_code == 200:
        print(f"✅ 音色注册成功")
    elif "repeat" in resp.text or "exist" in resp.text:
        # 优化逻辑：如果是因为 ID 已存在，这不算完全失败，可以继续尝试合成
        print(f"⚠️ 音色 ID 已存在，尝试直接使用该 ID 进行合成...")
    else:
        print(f"❌ 注册音色失败: {resp.text}")
        # 如果注册严重失败，可能无法合成，但我们还是尝试一下或者直接返回
        # return 

    # -------------------------------------------------
    # Step 3: 使用复刻音色生成语音 (T2A)
    # -------------------------------------------------
    print("3. 正在生成测试语音 ...")
    t2a_url = f"{BASE_URL}/t2a_v2"
    
    t2a_payload = {
        "model": "speech-02-turbo", 
        "text": "你好，这是我通过 MiniMax 复刻的声音。圣诞快乐，新年快乐！",
        "stream": False,
        "voice_setting": {
            "voice_id": CUSTOM_VOICE_ID,
            "speed": 1.0,
            "vol": 1.0
        },
        "audio_setting": {
            "sample_rate": 32000,
            "format": "mp3",
            "channel": 1
        }
    }
    
    try:
        resp = requests.post(t2a_url, headers=json_headers, json=t2a_payload)
        
        if resp.status_code == 200:
            output_data = resp.json()
            if "data" in output_data and "audio" in output_data["data"]:
                audio_hex = output_data["data"]["audio"]
                output_filename = "output_clone.mp3"
                with open(output_filename, "wb") as f:
                    f.write(binascii.unhexlify(audio_hex))
                print(f"✅ 合成成功！音频已保存为 {output_filename}")
            else:
                print(f"⚠️ 响应数据格式异常: {output_data}")
        else:
            print(f"❌ 合成失败 (Status {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"❌ 合成过程发生异常: {e}")

if __name__ == "__main__":
    run_voice_clone_pipeline()