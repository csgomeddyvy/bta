import os
import discord
from discord.ext import commands
import google.generativeai as genai
import requests
import io
import time
import base64
from keep_alive import keep_alive

# --- CẤU HÌNH ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN")  # Hugging Face Token

# Cấu hình Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Danh sách model Hugging Face chất lượng cao
HF_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",  # Model cực tốt
    "runwayml/stable-diffusion-v1-5",            # Model ổn định
    "black-forest-labs/FLUX.1-schnell",          # Model nhanh, chất lượng
]

def optimize_prompt_with_gemini(prompt):
    """Tối ưu hóa prompt với Gemini để có chất lượng ảnh tốt nhất"""
    try:
        response = model.generate_content(
            f"""Bạn là chuyên gia tạo prompt AI art. Hãy chuyển đổi ý tưởng sau thành prompt tiếng Anh chất lượng cao cho AI vẽ tranh.
            
YÊU CẦU:
- Dịch sang tiếng Anh
- Thêm mô tả chi tiết về: phong cách nghệ thuật, ánh sáng, composition, màu sắc
- Độ dài 50-100 từ
- Bao gồm từ khóa chất lượng như: "masterpiece", "best quality", "detailed", "4K"
- Chỉ trả về prompt cuối cùng, không thêm giải thích

Ý tưởng: {prompt}"""
        )
        return response.text.strip()
    except Exception as e:
        print(f"Lỗi tối ưu prompt: {e}")
        return prompt  # Fallback về prompt gốc

def draw_with_huggingface(prompt, model_name=HF_MODELS[0]):
    """Tạo ảnh chất lượng cao với Hugging Face API"""
    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Parameters cho chất lượng cao nhất
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 30,  # Tăng steps để chi tiết hơn
            "guidance_scale": 7.5,      # Cân bằng sáng tạo và tuân thủ prompt
            "negative_prompt": "blurry, low quality, worst quality, bad anatomy, watermark, signature, text, error",
        },
        "options": {
            "wait_for_model": True,     # Đợi model nếu đang load
            "use_cache": True
        }
    }
    
    print(f"🔄 Đang tạo ảnh với model: {model_name}")
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.content
    elif response.status_code == 503:
        # Model đang loading, thử lại sau
        print("Model đang loading, thử lại sau 10s...")
        time.sleep(10)
        return draw_with_huggingface(prompt, model_name)
    else:
        print(f"Lỗi API: {response.status_code} - {response.text}")
        return None

def draw_with_flux(prompt):
    """Fallback với FLUX model chất lượng cao"""
    try:
        # Mã hóa prompt để URL an toàn
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?" \
                   f"model=flux&width=1024&height=1024&nologo=true&enhance=true"
        
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"Lỗi FLUX: {e}")
    
    return None

@bot.event
async def on_ready():
    print(f'🎨 Bot {bot.user} đã sẵn sàng - Chế độ Chất Lượng Cao!')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="!ve + ý tưởng | HD Art"
    ))

@bot.command(name="ve")
async def draw_image(ctx, *, prompt: str):
    """Lệnh vẽ tranh chất lượng cao"""
    
    if not prompt:
        await ctx.send("❌ Vui lòng cung cấp mô tả để vẽ tranh!\nVí dụ: `!ve một chú mèo đang ngồi trên mây`")
        return
    
    # Thông báo đang xử lý
    msg = await ctx.send(f"🎨 **AI Artist** đang sáng tạo: '{prompt}'...\n⏳ Chất lượng cao có thể mất 15-30 giây...")

    try:
        # BƯỚC 1: Tối ưu hóa prompt với Gemini
        await msg.edit(content=f"🎨 **AI Artist** đang tối ưu hóa ý tưởng...")
        optimized_prompt = optimize_prompt_with_gemini(prompt)
        
        print(f"📝 Prompt gốc: {prompt}")
        print(f"🚀 Prompt tối ưu: {optimized_prompt}")

        # BƯỚC 2: Tạo ảnh với Hugging Face (chất lượng cao)
        image_data = None
        
        if HF_TOKEN:
            await msg.edit(content=f"🎨 **AI Artist** đang vẽ với công nghệ cao cấp...")
            
            # Thử lần lượt các model chất lượng cao
            for model_name in HF_MODELS:
                image_data = draw_with_huggingface(optimized_prompt, model_name)
                if image_data:
                    print(f"✅ Thành công với model: {model_name}")
                    break
                else:
                    print(f"❌ Thất bại với model: {model_name}, thử model tiếp theo...")
                    time.sleep(2)

        # BƯỚC 3: Fallback với FLUX nếu Hugging Face thất bại
        if not image_data:
            await msg.edit(content=f"🎨 **AI Artist** đang vẽ với công nghệ tiên tiến...")
            image_data = draw_with_flux(optimized_prompt)

        # BƯỚC 4: Gửi kết quả
        if image_data:
            # Kiểm tra kích thước file
            if len(image_data) > 25 * 1024 * 1024:  # Discord limit 25MB
                await msg.edit(content="❌ Ảnh quá lớn để gửi qua Discord")
                return
            
            with io.BytesIO(image_data) as file:
                await ctx.send(
                    content=f"✨ **Tác phẩm nghệ thuật của bạn!**\n"
                           f"📝 **Ý tưởng:** {prompt}\n"
                           f"🎨 **Prompt chuyên nghiệp:** `{optimized_prompt}`",
                    file=discord.File(file, filename="masterpiece.png")
                )
            await msg.delete()
            
        else:
            await msg.edit(content="❌ Không thể tạo ảnh lúc này. Vui lòng thử lại sau hoặc thay đổi mô tả.")

    except Exception as e:
        await msg.edit(content=f"❌ Có lỗi xảy ra: {str(e)}")
        print(f"Lỗi chi tiết: {e}")

@bot.command(name="models")
async def show_models(ctx):
    """Hiển thị các model có sẵn"""
    models_list = "\n".join([f"• {model}" for model in HF_MODELS])
    await ctx.send(f"🤖 **Các model AI có sẵn:**\n{models_list}")

# Giữ bot sống
keep_alive()

# Chạy bot
if DISCORD_TOKEN and GEMINI_API_KEY:
    bot.run(DISCORD_TOKEN)
else:
    print("Lỗi: Thiếu Token hoặc API Key trong Environment Variables")
