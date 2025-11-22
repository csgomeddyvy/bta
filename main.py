import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types
import io
from keep_alive import keep_alive

# --- CẤU HÌNH ---
# Bot sẽ tự lấy key từ hệ thống của Render
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Kết nối với Google AI
client = genai.Client(api_key=GEMINI_API_KEY)

# Cài đặt Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot đã online: {bot.user}')
    # Đổi trạng thái bot
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="bạn gõ !ve"))

@bot.command(name="ve")
async def draw_image(ctx, *, prompt: str):
    """Lệnh vẽ tranh: !ve mô tả của bạn"""
    
    # Bước 1: Thông báo đang vẽ
    msg = await ctx.send(f"🎨 **Imagen 3** đang khởi động để vẽ: '{prompt}'...\n*(Đợi khoảng 10-20 giây nhé)*")

    try:
        # Bước 2: "Dịch" prompt sang tiếng Anh bằng Gemini Flash cho chuẩn
        # Imagen 3 hiểu tiếng Anh tốt nhất
        refine_prompt = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=f"Translate the following prompt to English and optimize it for an AI image generator (artistic, high quality). Just give me the prompt text: {prompt}"
        )
        english_prompt = refine_prompt.text.strip()
        print(f"Prompt gốc: {prompt} -> Prompt AI: {english_prompt}")

        # Bước 3: Gửi lệnh cho Imagen 3 tạo ảnh
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=english_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1", # Bạn có thể đổi thành "16:9" nếu muốn ảnh ngang
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                person_generation="ALLOW_ADULT",
            )
        )

        # Bước 4: Lấy ảnh về và gửi lên Discord
        for generated_image in response.generated_images:
            image_bytes = generated_image.image.image_bytes
            
            with io.BytesIO(image_bytes) as file:
                await ctx.send(
                    content=f"✨ Tranh của bạn xong rồi! (Prompt gốc: *{prompt}*)",
                    file=discord.File(file, filename="imagen3_art.png")
                )
        
        # Xóa tin nhắn chờ
        await msg.delete()

    except Exception as e:
        error_message = str(e)
        print(f"Lỗi: {error_message}")
        
        if "403" in error_message:
            text_error = "🚫 **Lỗi Quyền Truy Cập:** Tài khoản Google AI của bạn chưa được cấp quyền dùng Imagen 3 (thường yêu cầu liên kết thanh toán/Billing). Hãy kiểm tra lại Google Cloud Console."
        elif "429" in error_message:
            text_error = "⏳ **Quá tải:** Bot đang vẽ quá nhiều, hãy thử lại sau 1 phút."
        else:
            text_error = f"❌ Có lỗi xảy ra: {error_message}"
            
        await msg.edit(content=text_error)

# Giữ bot sống
keep_alive()

# Chạy bot
if DISCORD_TOKEN and GEMINI_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Chưa có Token hoặc API Key")