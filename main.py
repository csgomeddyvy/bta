import os
import discord
from discord.ext import commands
import google.generativeai as genai
import requests
import io
from keep_alive import keep_alive

# --- CẤU HÌNH ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Cấu hình Gemini
# SỬA ĐỔI: Giữ Gemini 3 Pro Preview để TẠO PROMPT chất lượng cao
# LƯU Ý: Model này có thể yêu cầu BẬT THANH TOÁN (BILLING) để có quota cho việc tạo prompt.
genai.configure(api_key=GEMINI_API_KEY)
generation_model = genai.GenerativeModel('gemini-3-pro-preview') 

# Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã sẵn sàng (G3P Prompt & Pollinations Image)!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!ve + ý tưởng (G3P Prompt)"))

@bot.command(name="ve")
async def draw_image(ctx, *, prompt: str):
    """Lệnh vẽ: !ve mô tả"""
    
    # Thông báo đang xử lý
    msg = await ctx.send(f"🚀 **Gemini 3 Pro** đang lên ý tưởng và **Pollinations AI** đang vẽ: '{prompt}'... (Đợi xíu nhé)")

    try:
        # BƯỚC 1: Dùng Gemini 3 Pro để tạo prompt tiếng Anh xịn
        response_text_prompt = generation_model.generate_content(
            f"Hãy đóng vai một chuyên gia tạo prompt cho AI (như Midjourney/Flux). "
            f"Hãy dịch ý tưởng sau sang tiếng Anh và viết lại thành một prompt chi tiết, nghệ thuật, "
            f"tả ánh sáng, phong cách, **luôn thêm các từ khóa chất lượng như 'ultra quality, highly detailed, cinematic lighting, 8K resolution'** vào cuối prompt. "
            f"Chỉ trả về duy nhất đoạn text prompt tiếng Anh, không thêm lời dẫn. "
            f"Nội dung: {prompt}"
        )
        
        english_prompt = response_text_prompt.text.strip()
        print(f"Prompt gốc: {prompt}")
        print(f"Prompt Gemini 3 Pro tạo: {english_prompt}")

        # BƯỚC 2: Gửi Prompt sang Pollinations AI để tạo ảnh (Text-to-Image FREE)
        # Sử dụng Pollinations AI (Flux) như bản gốc
        image_url = f"https://image.pollinations.ai/prompt/{english_prompt}?model=flux&width=1024&height=1024&nologo=true"
        
        # Tải ảnh về
        image_response = requests.get(image_url)
        
        if image_response.status_code == 200:
            image_data = image_response.content
            
            # Gửi ảnh lên Discord
            with io.BytesIO(image_data) as file:
                # ĐÃ SỬA ĐỔI: Chỉ gửi ảnh và thông báo, loại bỏ hiển thị prompt
                await ctx.send(
                    content=f"✨ Tranh của bạn đây! (Prompt được tối ưu bởi Gemini 3 Pro)",
                    file=discord.File(file, filename="art_gen.png")
                )
            await msg.delete() # Xóa tin nhắn chờ
        else:
            await msg.edit(content="❌ Lỗi khi gọi server vẽ tranh (Pollinations AI). Vui lòng thử lại.")

    except Exception as e:
        # ĐÃ SỬA: Bắt Exception chung và kiểm tra lỗi ResourceExhausted/Billing
        if "ResourceExhausted" in str(e) or "PERMISSION_DENIED" in str(e):
             await msg.edit(content=f"❌ **Lỗi Quota (Billing): Vui lòng kiểm tra thanh toán.**\n"
                                   f"Model Gemini 3 Pro (Preview) không có quota miễn phí cho việc tạo prompt. Vui lòng bật billing, hoặc thay thế bằng 'gemini-2.5-flash'. "
                                   f"Chi tiết lỗi: `{str(e)}`")
        else:
            await msg.edit(content=f"❌ Có lỗi xảy ra: {str(e)}")
        print(e)

# Giữ bot sống
keep_alive()

# Chạy bot
if DISCORD_TOKEN and GEMINI_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Thiếu Token hoặc API Key trong Environment Variables")
