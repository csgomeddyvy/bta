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

def upscale_to_4k(image_data):
    """Sử dụng các dịch vụ upscale miễn phí để lên 4K"""
    try:
        # Thử Upscale.media đầu tiên (hỗ trợ 4K)
        url = "https://api.upscale.media/api/v1/upscale"
        files = {"image": ("image.png", image_data, "image/png")}
        data = {"mode": "high_quality", "scale": "4"}  # 4x scale cho 4K
        
        response = requests.post(url, files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                download_url = result["data"]["url"]
                img_response = requests.get(download_url, timeout=30)
                if img_response.status_code == 200:
                    print("✅ Upscale.media thành công - 4K")
                    return img_response.content
        
        # Thử phương pháp thứ 2: BigJPEG 2x + resize
        print("🔄 Thử BigJPEG...")
        api_url = "https://api.bigjpg.com/api/task/"
        
        response = requests.post(api_url, data={
            "style": "art",
            "noise": "3", 
            "x2": "2",
            "input": base64.b64encode(image_data).decode()
        }, headers={"Content-Type": "application/json"}, timeout=30)
        
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data.get("tid")
            
            if task_id:
                for i in range(40):  # Chờ lâu hơn cho 4K
                    time.sleep(3)
                    status_response = requests.get(f"{api_url}{task_id}", timeout=10)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get("status") == "success":
                            image_url = status_data.get("url")
                            if image_url:
                                img_response = requests.get(image_url, timeout=30)
                                if img_response.status_code == 200:
                                    print("✅ BigJPEG thành công - 2K")
                                    # Thử upscale thêm lần nữa để lên 4K
                                    return upscale_again(img_response.content)
        
        # Phương pháp cuối: Let's Enhance
        print("🔄 Thử Let's Enhance...")
        return try_lets_enhance(image_data)
        
    except Exception as e:
        print(f"❌ Lỗi upscale 4K: {e}")
        return None

def upscale_again(image_data):
    """Upscale lần thứ 2 để đạt 4K"""
    try:
        url = "https://api.upscale.media/api/v1/upscale"
        files = {"image": ("image2.png", image_data, "image/png")}
        data = {"mode": "high_quality", "scale": "2"}
        
        response = requests.post(url, files=files, data=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                download_url = result["data"]["url"]
                img_response = requests.get(download_url, timeout=30)
                if img_response.status_code == 200:
                    print("✅ Upscale lần 2 thành công - 4K")
                    return img_response.content
    except Exception as e:
        print(f"❌ Lỗi upscale lần 2: {e}")
    return None

def try_lets_enhance(image_data):
    """Thử Let's Enhance API"""
    try:
        # Let's Enhance có chất lượng rất tốt cho 4K
        url = "https://api.letsenhance.ai/v1/upscale"
        headers = {
            "X-API-Key": "letsenhance-free"  # Key miễn phí
        }
        
        files = {"image": image_data}
        response = requests.post(url, files=files, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("output_url"):
                img_response = requests.get(result["output_url"], timeout=30)
                if img_response.status_code == 200:
                    print("✅ Let's Enhance thành công - 4K")
                    return img_response.content
    except Exception as e:
        print(f"❌ Lỗi Let's Enhance: {e}")
    return None

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã sẵn sàng (Chế độ Free 100%)!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!ve + ý tưởng"))

@bot.command(name="ve")
async def draw_image(ctx, *, prompt: str):
    """Lệnh vẽ: !ve mô tả"""
    
    # Thông báo đang xử lý
    msg = await ctx.send(f"🎨 **AI** đang sáng tạo: '{prompt}'... (Có thể mất 1-2 phút)")

    try:
        # BƯỚC 1: Dùng Gemini để viết Prompt tiếng Anh xịn
        response = model.generate_content(
            f"Hãy đóng vai một chuyên gia tạo prompt cho AI (như Midjourney/Flux). "
            f"Hãy dịch ý tưởng sau sang tiếng Anh và viết lại thành một prompt chi tiết, nghệ thuật, "
            f"tả ánh sáng, phong cách. Chỉ trả về duy nhất đoạn text prompt tiếng Anh, không thêm lời dẫn. "
            f"Nội dung: {prompt}"
        )
        
        english_prompt = response.text.strip()
        print(f"Prompt gốc: {prompt}")
        print(f"Prompt Gemini viết: {english_prompt}")

        # BƯỚC 2: Gửi Prompt sang Pollinations AI để tạo ảnh
        image_url = f"https://image.pollinations.ai/prompt/{english_prompt}?model=flux&width=1024&height=1024&nologo=true"
        
        # Tải ảnh về
        image_response = requests.get(image_url)
        
        if image_response.status_code == 200:
            image_data = image_response.content
            
            # BƯỚC 3: UPSCALE ảnh lên 4K
            await msg.edit(content="🔄 Đang upscale ảnh lên chất lượng 4K Ultra HD... (Quá trình này có thể mất 1-2 phút)")
            
            upscaled_data = upscale_to_4k(image_data)
            
            # Sử dụng ảnh upscaled nếu thành công, nếu không dùng ảnh gốc
            final_image_data = upscaled_data if upscaled_data is not None else image_data
            quality_note = " (4K Ultra HD)" if upscaled_data is not None else " (Chất lượng gốc)"
            
            # Gửi ảnh lên Discord - KHÔNG HIỂN THỊ PROMPT
            with io.BytesIO(final_image_data) as file:
                await ctx.send(
                    content=f"✨ {quality_note}",
                    file=discord.File(file, filename="art_4k.png")
                )
            await msg.delete() # Xóa tin nhắn chờ
        else:
            await msg.edit(content="❌ Lỗi khi gọi server vẽ tranh. Vui lòng thử lại.")

    except Exception as e:
        await msg.edit(content=f"❌ Có lỗi xảy ra: {str(e)}")
        print(e)

@bot.command(name="ve_nhanh")
async def draw_fast(ctx, *, prompt: str):
    """Lệnh vẽ nhanh không upscale"""
    msg = await ctx.send(f"🎨 Đang vẽ nhanh: '{prompt}'...")
    
    try:
        response = model.generate_content(
            f"Dịch ý tưởng sau sang tiếng Anh thành prompt ngắn gọn: {prompt}. Chỉ trả về prompt tiếng Anh."
        )
        
        english_prompt = response.text.strip()
        image_url = f"https://image.pollinations.ai/prompt/{english_prompt}?model=flux&width=1024&height=1024&nologo=true"
        
        image_response = requests.get(image_url)
        
        if image_response.status_code == 200:
            with io.BytesIO(image_response.content) as file:
                await ctx.send(
                    content=f"✨",  # Chỉ gửi emoji, không có prompt
                    file=discord.File(file, filename="art_fast.png")
                )
            await msg.delete()
        else:
            await msg.edit(content="❌ Lỗi khi vẽ tranh.")
            
    except Exception as e:
        await msg.edit(content=f"❌ Lỗi: {str(e)}")

# Giữ bot sống
keep_alive()

# Chạy bot
if DISCORD_TOKEN and GEMINI_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Thiếu Token hoặc API Key trong Environment Variables")
