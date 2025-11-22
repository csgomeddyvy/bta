import os
import discord
from discord.ext import commands
import google.generativeai as genai
import requests
import io
import base64
from keep_alive import keep_alive
import time

# --- CẤU HÌNH ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Cấu hình Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def upscale_with_deepai(image_data):
    """Sử dụng DeepAI Super Resolution API miễn phí"""
    try:
        # DeepAI Super Resolution API (miễn phí với key quickstart)
        headers = {'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'}
        files = {'image': image_data}
        
        response = requests.post(
            "https://api.deepai.org/api/torch-srgan",
            files=files,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'output_url' in result:
                img_response = requests.get(result['output_url'])
                if img_response.status_code == 200:
                    print("✅ DeepAI Super Resolution thành công!")
                    return img_response.content
    except Exception as e:
        print(f"Lỗi DeepAI: {e}")
    return None

def upscale_with_bigjpeg(image_data):
    """Sử dụng BigJPEG API miễn phí"""
    try:
        # BigJPEG API (miễn phí 20 ảnh/tháng)
        api_url = "https://api.bigjpg.com/api/task/"
        
        response = requests.post(api_url, json={
            "style": "art",
            "noise": "3",
            "x2": "2",
            "input": base64.b64encode(image_data).decode()
        }, headers={"Content-Type": "application/json"}, timeout=30)
        
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data.get("tid")
            
            if task_id:
                for i in range(20):  # Chờ tối đa 20 lần (khoảng 40 giây)
                    time.sleep(2)
                    status_response = requests.get(f"{api_url}{task_id}", timeout=10)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get("status") == "success":
                            image_url = status_data.get("url")
                            if image_url:
                                img_response = requests.get(image_url, timeout=30)
                                if img_response.status_code == 200:
                                    print("✅ BigJPEG thành công!")
                                    return img_response.content
    except Exception as e:
        print(f"Lỗi BigJPEG: {e}")
    return None

def upscale_with_waifu2x(image_data):
    """Sử dụng waifu2x API miễn phí"""
    try:
        files = {'file': ('image.png', image_data, 'image/png')}
        data = {'style': 'art', 'noise': '2', 'scale': '2'}
        
        response = requests.post(
            'https://api.waifu2x.net/upload',
            files=files,
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'url' in result:
                img_response = requests.get(result['url'])
                if img_response.status_code == 200:
                    print("✅ waifu2x thành công!")
                    return img_response.content
    except Exception as e:
        print(f"Lỗi waifu2x: {e}")
    return None

def smart_upscale(image_data):
    """Logic upscale thông minh"""
    print("🔄 Bắt đầu upscale ảnh...")
    
    # Thử DeepAI đầu tiên
    print("🔹 Thử DeepAI Super Resolution...")
    result = upscale_with_deepai(image_data)
    if result:
        return result
    
    # Thử waifu2x
    print("🔹 Thử waifu2x API...")
    result = upscale_with_waifu2x(image_data)
    if result:
        return result
    
    # Thử BigJPEG
    print("🔹 Thử BigJPEG API...")
    result = upscale_with_bigjpeg(image_data)
    if result:
        return result
    
    print("❌ Tất cả dịch vụ upscale đều thất bại")
    return None

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã sẵn sàng!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!ve + ý tưởng"))

@bot.command(name="ve")
async def draw_image(ctx, *, prompt: str):
    """Lệnh vẽ: !ve mô tả"""
    
    msg = await ctx.send(f"🎨 **AI** đang sáng tạo: '{prompt}'...")

    try:
        # Viết prompt với Gemini
        response = model.generate_content(
            f"Hãy đóng vai một chuyên gia tạo prompt cho AI. "
            f"Dịch ý tưởng sau sang tiếng Anh và viết lại thành prompt chi tiết, nghệ thuật. "
            f"Chỉ trả về prompt tiếng Anh, không thêm gì khác. "
            f"Nội dung: {prompt}"
        )
        
        english_prompt = response.text.strip()
        print(f"Prompt: {english_prompt}")

        # Tạo ảnh gốc
        image_url = f"https://image.pollinations.ai/prompt/{english_prompt}?model=flux&width=1024&height=1024&nologo=true"
        image_response = requests.get(image_url)
        
        if image_response.status_code == 200:
            original_image = image_response.content
            
            # UPSCALE
            await msg.edit(content="🔄 Đang upscale ảnh lên chất lượng cao...")
            
            upscaled_image = smart_upscale(original_image)
            
            # Gửi ảnh kết quả
            final_image = upscaled_image if upscaled_image else original_image
            quality_note = " (Đã upscale HD)" if upscaled_image else " (Chất lượng gốc)"
            
            with io.BytesIO(final_image) as file:
                await ctx.send(
                    content=f"✨{quality_note}",
                    file=discord.File(file, filename="art.png")
                )
            await msg.delete()
            
        else:
            await msg.edit(content="❌ Lỗi khi tạo ảnh. Vui lòng thử lại.")

    except Exception as e:
        await msg.edit(content=f"❌ Có lỗi xảy ra: {str(e)}")
        print(f"Lỗi: {e}")

@bot.command(name="test")
async def test_command(ctx):
    """Lệnh test bot"""
    await ctx.send("🤖 Bot đang hoạt động bình thường!")

# Giữ bot sống
keep_alive()

# Chạy bot
if DISCORD_TOKEN and GEMINI_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Thiếu Token hoặc API Key")
