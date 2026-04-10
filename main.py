import discord
from discord.ext import commands
import yt_dlp
import requests
import os
import asyncio
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURATION
# ==========================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CURR_API_KEY = os.getenv('CURRENCY_API_KEY')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# Music Data Structure
queues = {} 

YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# ==========================================
# 2. CORE MUSIC LOGIC
# ==========================================

def check_queue(ctx):
    """Automatically plays the next song in the queue."""
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        next_url = queues[guild_id].pop(0)
        bot.loop.create_task(play_song(ctx, next_url))
    else:
        print(f"Queue empty for {ctx.guild.name}")

async def play_song(ctx, url):
    """Handles stream extraction and playback."""
    try:
        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['url']
                source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
                
                ctx.voice_client.play(source, after=lambda e: check_queue(ctx))
                
            await ctx.send(f"🎶 Now playing: **{info['title']}**")
    except Exception as e:
        print(f"Playback Error: {e}")
        await ctx.send("❌ Error: Could not play the song.")

# ==========================================
# 3. COMMANDS
# ==========================================

@bot.command(name="play")
async def play(ctx, url):
    """Plays a song or adds it to the queue."""
    guild_id = ctx.guild.id
    
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.send("❌ You must be in a voice channel!")

    if guild_id not in queues:
        queues[guild_id] = []

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queues[guild_id].append(url)
        await ctx.send("📝 Added to queue.")
    else:
        await play_song(ctx, url)

@bot.command(name="skip")
async def skip(ctx):
    """Skips the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop() 
        await ctx.send("⏭️ Skipped!")
    else:
        await ctx.send("❌ Nothing is playing.")

@bot.command(name="pause")
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused.")

@bot.command(name="resume")
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed.")

@bot.command(name="stop")
async def stop(ctx):
    """Clears queue and leaves channel."""
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Disconnected.")

@bot.command(name="rate")
async def rate(ctx):
    """Shows live exchange rates for 1 PLN."""
    url = f"https://v6.exchangerate-api.com/v6/{CURR_API_KEY}/latest/PLN"
    try:
        data = requests.get(url).json()
        usd = data['conversion_rates']['USD']
        try_rate = data['conversion_rates']['TRY']
        embed = discord.Embed(title="🇵🇱 PLN Exchange Rates", color=discord.Color.blue())
        embed.add_field(name="USD", value=f"${usd:.4f}", inline=True)
        embed.add_field(name="TRY", value=f"₺{try_rate:.4f}", inline=True)
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ Currency service unavailable.")

# ==========================================
# 4. STARTUP
# ==========================================
@bot.event
async def on_ready():
    print(f'--- {bot.user.name} IS ONLINE ---')

if __name__ == "__main__":
    bot.run(TOKEN)