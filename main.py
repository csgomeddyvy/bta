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
# SỬA ĐỔI: Sử dụng model Gemini 3.0 Pro Preview
# LƯU Ý QUAN TRỌNG: Model này yêu cầu BẬT THANH TOÁN (BILLING) và có thể yêu cầu quyền truy cập đặc biệt.
genai.configure(api_key=GEMINI_API_KEY)
generation_model = genai.GenerativeModel('gemini-3-pro-preview') # SỬA ĐỔI: Dùng cho việc tạo prompt và tạo ảnh

# Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} đã sẵn sàng (Đang sử dụng Gemini 3 Pro Preview & Imagen 3 - Yêu cầu Billing)!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!ve + ý tưởng (G3P Mode)"))

@bot.command(name="ve")
async def draw_image(ctx, *, prompt: str):
    """Lệnh vẽ: !ve mô tả (sử dụng Gemini 3 Pro và Imagen 3)"""
    
    # Thông báo đang xử lý
    msg = await ctx.send(f"🚀 **Gemini 3 Pro** đang lên ý tưởng và tạo ảnh: '{prompt}'... (Đợi xíu nhé)")

    try:
        # BƯỚC 1: Dùng Gemini 3 Pro để tạo prompt tiếng Anh xịn cho việc tạo ảnh
        response_text_prompt = generation_model.generate_content(
            f"Hãy đóng vai một chuyên gia tạo prompt cho AI (như Midjourney/DALL-E/Imagen). "
            f"Hãy dịch ý tưởng sau sang tiếng Anh và viết lại thành một prompt chi tiết, nghệ thuật, "
            f"tả ánh sáng, phong cách, **luôn thêm các từ khóa chất lượng như 'ultra quality, highly detailed, cinematic lighting, 8K, photorealistic'** vào cuối prompt. "
            f"Chỉ trả về duy nhất đoạn text prompt tiếng Anh, không thêm lời dẫn. "
            f"Nội dung: {prompt}"
        )
        
        english_prompt = response_text_prompt.text.strip()
        print(f"Prompt gốc: {prompt}")
        print(f"Prompt Gemini 3 Pro tạo: {english_prompt}")

        # BƯỚC 2: Sử dụng Gemini 3 Pro (kết hợp Imagen 3) để tạo ảnh trực tiếp
        
        image_response = await generation_model.generate_content_async([
            english_prompt,
            genai.types.GenerationConfig(
                temperature=0.7, 
                max_output_tokens=2048, 
                response_mime_type="image/jpeg" 
            )
        ])

        # Trích xuất dữ liệu ảnh từ phản hồi đa phương thức của Gemini
        image_data = None
        if image_response and image_response.candidates:
            for part in image_response.candidates[0].content.parts:
                if part.is_image():
                    # Lấy dữ liệu nhị phân của ảnh
                    image_data = part.image.data 
                    break 
        
        if image_data:
            with io.BytesIO(image_data) as file:
                await ctx.send(
                    content=f"✨ Tranh của bạn đây! (Được tạo bởi Gemini 3 Pro & Imagen 3)",
                    file=discord.File(file, filename="gemini_art.png")
                )
            await msg.delete() # Xóa tin nhắn chờ
        else:
            await msg.edit(content="❌ Không thể tạo ảnh với prompt này hoặc không nhận được dữ liệu ảnh từ Gemini 3 Pro. Vui lòng thử lại.")

    except genai.types.core.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "PERMISSION_DENIED" in str(e):
            await msg.edit(content=f"❌ **Lỗi: Vui lòng kiểm tra Billing và quyền truy cập API của bạn.**\n"
                                   f"Để sử dụng Gemini 3 Pro (Preview) và Imagen 3, bạn cần bật thanh toán trên Google AI Studio/Cloud và đảm bảo API Key có đủ quyền. "
                                   f"Chi tiết lỗi: `{str(e)}`")
        else:
            await msg.edit(content=f"❌ Có lỗi xảy ra với Gemini API: {str(e)}")
        print(e)
    except Exception as e:
        await msg.edit(content=f"❌ Có lỗi xảy ra: {str(e)}")
        print(e)

# Giữ bot sống
keep_alive()

# Chạy bot
if DISCORD_TOKEN and GEMINI_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Thiếu Token hoặc API Key trong Environment Variables")
