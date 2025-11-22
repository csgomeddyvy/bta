import os
import discord
from discord.ext import commands
import google.generativeai as genai
import requests
import io
from keep_alive import keep_alive
import time

# --- CẤU HÌNH ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLIPDROP_API_KEY = os.environ.get("CLIPDROP_API_KEY")

# Cấu hình Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def upscale_with_clipdrop(image_data):
    """Sử dụng Clipdrop API để upscale ảnh lên 4K"""
    try:
        print("🔄 Đang upscale với Clipdrop...")
        
        # Clipdrop Upscale API
        url = "https://clipdrop-api.co/upscale/v1"
        
        files = {
            'image_file': ('image.png', image_data, 'image/png')
        }
        
        headers = {
            'x-api-key': CLIPDROP_API_KEY
        }
        
        response = requests.post(url, files=files, headers=headers, timeout=60)
        
        if response.status_code == 200:
            print("✅ Clipdrop upscale thành công - 4K")
            return response.content
        else:
            print(f"❌ Clipdrop lỗi: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi Clipdrop: {e}")
        return None

def upscale_with_clipdrop_sr(image_data):
    """Sử dụng Clipdrop Super Resolution nếu upscale thông thường không hoạt động"""
    try:
        print("🔄 Thử Clipdrop Super Resolution...")
        
        url = "https://clipdrop-api.co/image-upscaling/v1/upscale"
        
        files = {
            'image': ('image.png', image_data, 'image/png')
        }
        
        headers = {
            'x-api-key': CLIPDROP_API_KEY
        }
        
        # Thêm parameters cho chất lượng cao
        data = {
            'width': 4096,
            'height': 4096
        }
        
        response = requests.post(url, files=files, headers=headers, data=data, timeout=60)
        
        if response.status_code == 200:
            print("✅ Clipdrop Super Resolution thành công - 4K")
            return response.content
        else:
            print(f"❌ Clipdrop SR lỗi: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi Clipdrop SR: {e}")
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
            f"Hãy đóng vai một chuyên gia tạo prompt cho AI (như Midjourney/Flux). "
            f"Hãy dịch ý tưởng sau sang tiếng Anh và viết lại thành một prompt chi tiết, nghệ thuật, "
            f"tả ánh sáng, phong cách. Chỉ trả về duy nhất đoạn text prompt tiếng Anh, không thêm lời dẫn. "
            f"Nội dung: {prompt}"
        )
        
        english_prompt = response.text.strip()
        print(f"Prompt gốc: {prompt}")
        print(f"Prompt Gemini viết: {english_prompt}")

        # BƯỚC 2: Tạo ảnh gốc với Pollinations
        image_url = f"https://image.pollinations.ai/prompt/{english_prompt}?model=flux&width=1024&height=1024&nologo=true"
        
        image_response = requests.get(image_url)
        
        if image_response.status_code == 200:
            original_image_data = image_response.content
            
            # BƯỚC 3: UPSCALE với Clipdrop
            await msg.edit(content="🔄 Đang upscale ảnh lên 4K với Clipdrop...")
            
            # Thử upscale thông thường trước
            upscaled_data = upscale_with_clipdrop(original_image_data)
            
            # Nếu không thành công, thử Super Resolution
            if upscaled_data is None:
                await msg.edit(content="🔄 Đang thử Super Resolution...")
                upscaled_data = upscale_with_clipdrop_sr(original_image_data)
            
            # Xác định dữ liệu ảnh cuối cùng
            if upscaled_data is not None:
                final_image_data = upscaled_data
                quality_info = "4K"
                filename = "art_4k.png"
            else:
                final_image_data = original_image_data
                quality_info = "1024px"
                filename = "art.png"
                await ctx.send("⚠️ Upscale thất bại, sử dụng ảnh gốc")
            
            # Gửi ảnh lên Discord
            with io.BytesIO(final_image_data) as file:
                await ctx.send(
                    content=f"✨ **{quality_info}**",
                    file=discord.File(file, filename=filename)
                )
            await msg.delete()
            
        else:
            await msg.edit(content="❌ Lỗi khi tạo ảnh gốc.")

    except Exception as e:
        await msg.edit(content=f"❌ Có lỗi xảy ra: {str(e)}")
        print(f"Lỗi: {e}")

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
                    content=f"✨",
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
if DISCORD_TOKEN and GEMINI_API_KEY and CLIPDROP_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Thiếu Token hoặc API Key trong Environment Variables")
    print(f"Discord Token: {'Có' if DISCORD_TOKEN else 'THIẾU'}")
    print(f"Gemini Key: {'Có' if GEMINI_API_KEY else 'THIẾU'}")
    print(f"Clipdrop Key: {'Có' if CLIPDROP_API_KEY else 'THIẾU'}")
