import os
import discord
from discord.ext import commands
import google.generativeai as genai
import requests
import io
import replicate
from keep_alive import keep_alive
import time

# --- CẤU HÌNH ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")  # Thêm này vào environment variables

# Cấu hình Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def upscale_with_replicate(image_data):
    """Sử dụng Replicate API với Real-ESRGAN - AI upscale chất lượng cao"""
    try:
        # Replicate có model Real-ESRGAN miễn phí (5 credits miễn phí khi đăng ký)
        output = replicate.run(
            "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
            input={
                "image": io.BytesIO(image_data),
                "scale": 4,  # Upscale 4x lên 4K
                "face_enhance": True
            }
        )
        return output
    except Exception as e:
        print(f"Lỗi Replicate: {e}")
        return None

def upscale_with_waifu2x(image_data):
    """Sử dụng waifu2x API miễn phí - rất tốt cho ảnh nghệ thuật"""
    try:
        # Waifu2x API miễn phí
        files = {'file': ('image.png', image_data, 'image/png')}
        data = {
            'style': 'art',
            'noise': '2',
            'scale': '4'  # 4x upscale
        }
        
        response = requests.post(
            'https://api.waifu2x.net/upload',
            files=files,
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'url' in result:
                # Tải ảnh đã upscale
                img_response = requests.get(result['url'])
                if img_response.status_code == 200:
                    return img_response.content
    except Exception as e:
        print(f"Lỗi waifu2x: {e}")
    return None

def upscale_with_cupscale(image_data):
    """Sử dụng Cupscale API - dịch vụ upscale miễn phí tốt"""
    try:
        # Cupscale API
        files = {'file': ('image.png', image_data, 'image/png')}
        response = requests.post(
            'https://api.cupscale.com/upscale',
            files=files,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"Lỗi cupscale: {e}")
    return None

def smart_upscale(image_data):
    """Logic upscale thông minh - thử lần lượt các dịch vụ"""
    print("🔄 Bắt đầu upscale ảnh...")
    
    # Thử Replicate đầu tiên (chất lượng tốt nhất)
    if REPLICATE_API_TOKEN:
        print("🔹 Thử Replicate API...")
        result = upscale_with_replicate(image_data)
        if result:
            print("✅ Replicate thành công!")
            return result
    
    # Thử waifu2x
    print("🔹 Thử waifu2x API...")
    result = upscale_with_waifu2x(image_data)
    if result:
        print("✅ waifu2x thành công!")
        return result
    
    # Thử cupscale
    print("🔹 Thử Cupscale API...")
    result = upscale_with_cupscale(image_data)
    if result:
        print("✅ Cupscale thành công!")
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
    
    # Thông báo đang xử lý
    msg = await ctx.send(f"🎨 **AI** đang sáng tạo: '{prompt}'...")

    try:
        # BƯỚC 1: Dùng Gemini để viết Prompt tiếng Anh
        response = model.generate_content(
            f"Hãy đóng vai một chuyên gia tạo prompt cho AI. "
            f"Dịch ý tưởng sau sang tiếng Anh và viết lại thành prompt chi tiết, nghệ thuật. "
            f"Chỉ trả về prompt tiếng Anh, không thêm gì khác. "
            f"Nội dung: {prompt}"
        )
        
        english_prompt = response.text.strip()
        print(f"Prompt: {english_prompt}")

        # BƯỚC 2: Tạo ảnh gốc
        image_url = f"https://image.pollinations.ai/prompt/{english_prompt}?model=flux&width=1024&height=1024&nologo=true"
        image_response = requests.get(image_url)
        
        if image_response.status_code == 200:
            original_image = image_response.content
            
            # BƯỚC 3: UPSCALE chất lượng cao
            await msg.edit(content="🔄 Đang upscale ảnh lên chất lượng cao...")
            
            upscaled_image = smart_upscale(original_image)
            
            # Gửi ảnh kết quả
            final_image = upscaled_image if upscaled_image else original_image
            quality_note = " (4K Ultra HD)" if upscaled_image else " (Chất lượng gốc)"
            
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

@bot.command(name="test_upscale")
async def test_upscale(ctx):
    """Lệnh test upscale với ảnh mẫu"""
    msg = await ctx.send("🔄 Đang test upscale...")
    
    # Tải ảnh test
    test_url = "https://image.pollinations.ai/prompt/a%20beautiful%20landscape%20with%20mountains%20and%20lake?model=flux&width=512&height=512"
    response = requests.get(test_url)
    
    if response.status_code == 200:
        await msg.edit(content="🔄 Đang upscale ảnh test...")
        upscaled = smart_upscale(response.content)
        
        if upscaled:
            with io.BytesIO(upscaled) as file:
                await ctx.send(
                    content="✅ Test upscale thành công! (4K)",
                    file=discord.File(file, filename="test_4k.png")
                )
        else:
            await ctx.send("❌ Test upscale thất bại")
        
        await msg.delete()

# Giữ bot sống
keep_alive()

# Chạy bot
if DISCORD_TOKEN and GEMINI_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Thiếu Token hoặc API Key")
