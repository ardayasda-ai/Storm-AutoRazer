import discord
from discord.ext import commands, tasks
import datetime
from flask import Flask
from threading import Thread
import os

# --- RENDER KEEPALIVE FLASK SUNUCUSU ---
app = Flask('')

@app.route('/')
def home():
    return "AutoRazer Bot Aktif ve Çalışıyor! Authorized By Zynex"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- BOT AYARLARI ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Rol ve Kanal ID Depolama Sözlüğü
SERVER_CONFIGS = {}

# Cooldown Takibi (Kullanıcı ID: Son Kanıt Zamanı)
BOOST_COOLDOWN = {}

# Aktif Takip Listeleri
ACTIVE_BOOSTERS = set()
ACTIVE_BIO_USERS = set()

class KanitOnayButonlari(discord.ui.View):
    def __init__(self, user_id: int, kanit_turu: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.kanit_turu = kanit_turu

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.green, custom_id="storm_onayla")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bu işlemi yapmak için yetkin yok!", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.user_id)

        if member:
            if self.kanit_turu == "boost":
                role = discord.utils.get(guild.roles, name="2x Boosted")
                if role:
                    await member.add_roles(role)
                    ACTIVE_BOOSTERS.add(self.user_id)
            elif self.kanit_turu == "bio":
                role = discord.utils.get(guild.roles, name="Guild / Bio Member")
                if role:
                    await member.add_roles(role)
                    ACTIVE_BIO_USERS.add(self.user_id)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="🚀 Durum", value=f"✅ Onaylayan Yetkili: {interaction.user.mention}", inline=False)
        
        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Kanıt başarıyla onaylandı ve rolü verildi!", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.red, custom_id="storm_reddet")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bu işlemi yapmak için yetkin yok!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="🛑 Durum", value=f"❌ Reddeden Yetkili: {interaction.user.mention}", inline=False)
        
        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("🛑 Kanıt reddedildi.", ephemeral=True)


@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} (AutoRazer) aktif ve çalışmaya hazır!")
    print("Authorized By Zynex")
    try:
        synced = await bot.tree.sync()
        print(f"🌲 {len(synced)} slash komut başarıyla senkronize edildi.")
    except Exception as e:
        print(e)
    durum_kontrol_dongusu.start()


# --- KANIT KANAL DİNLEYİCİSİ ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_name = message.channel.name.lower()

    if "2x-boost-kanıt" in channel_name or "bio-guild-kanıt" in channel_name:
        is_boost = "2x-boost-kanıt" in channel_name

        # 1. Cooldown Kontrolü (Boost kanıtı için saatte 1 hak)
        if is_boost:
            now = datetime.datetime.now().timestamp()
            last_time = BOOST_COOLDOWN.get(message.author.id, 0)
            if now - last_time < 3600:
                kalan_dakika = int((3600 - (now - last_time)) / 60)
                try:
                    await message.delete()
                    uyari = await message.channel.send(f"⏳ {message.author.mention}, saatte sadece 1 kez 2x boost kanıtı atabilirsin! Kalan süre: **{kalan_dakika} dakika**.")
                    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
                    await uyari.delete()
                except:
                    pass
                return
            BOOST_COOLDOWN[message.author.id] = now

        # 2. Görsel Zorunluluğu
        if not message.attachments:
            try:
                await message.delete()
                uyari = await message.channel.send(f"⚠️ {message.author.mention}, bu kanala yalnızca ekran görüntüsü (kanıt) atabilirsin!")
                await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
                await uyari.delete()
            except:
                pass
            return

        tur_adi = "🚀 2x Boost Kanıtı" if is_boost else "🟩🟨 Bio / Guild Kanıtı"
        
        embed = discord.Embed(
            title=f"📥 Yeni {tur_adi}",
            description=f"**Kullanıcı:** {message.author.mention}\n**Kullanıcı ID:** `{message.author.id}`\n**Gönderildiği Kanal:** {message.channel.mention}",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        embed.set_image(url=message.attachments[0].url)
        embed.set_footer(text="Authorized By Zynex", icon_url=bot.user.avatar.url if bot.user.avatar else None)

        try:
            await message.delete()
        except:
            pass

        kanit_turu_str = "boost" if is_boost else "bio"
        await message.channel.send(embed=embed, view=KanitOnayButonlari(message.author.id, kanit_turu_str))

    await bot.process_commands(message)


@tasks.loop(minutes=30)
async def durum_kontrol_dongusu():
    for guild in bot.guilds:
        pass


# --- KOMUTLAR ---

@bot.tree.command(name="logpanelkurrazer", description="🚀 2x-boost ve bio-guild kanıt log panellerini kurar.")
async def logpanelkurrazer(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return

    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    kategori = await guild.create_category("🚀 AUTO RAZER PANEL", overwrites=overwrites)
    boost_kanali = await guild.create_text_channel("🚀-2x-boost-kanıt", category=kategori)
    bio_kanali = await guild.create_text_channel("🟩-bio-guild-kanıt", category=kategori)

    SERVER_CONFIGS[guild.id] = {
        "kategori": kategori.id,
        "boost_kanit": boost_kanali.id,
        "bio_kanit": bio_kanali.id
    }

    embed = discord.Embed(
        title="⚙️ AutoRazer Log Paneli Kuruldu",
        description=f"Kanıt kanalları başarıyla oluşturuldu:\n\n• {boost_kanali.mention}\n• {bio_kanali.mention}",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Authorized By Zynex")

    await interaction.response.send_message(embed=embed, ephemeral=False)


@bot.tree.command(name="logpanelsıfırla", description="🗑️ Kurulan log kategorisini ve kanalları tamamen temizler.")
async def logpanelsıfırla(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return

    guild = interaction.guild
    config = SERVER_CONFIGS.get(guild.id)

    if not config:
        silinen = 0
        for channel in guild.channels:
            if "auto-razer" in channel.name.lower() or "kanıt" in channel.name.lower():
                try:
                    await channel.delete()
                    silinen += 1
                except:
                    pass
        await interaction.response.send_message(f"🗑️ Bulunan kanıt kanalları ve kategorileri temizlendi! (Silinen: {silinen})", ephemeral=True)
        return

    try:
        kategori = guild.get_channel(config["kategori"])
        if kategori:
            for ch in kategori.channels:
                await ch.delete()
            await kategori.delete()
        
        SERVER_CONFIGS.pop(guild.id, None)
        await interaction.response.send_message("🗑️ AutoRazer log paneli ve kanalları tamamen sıfırlandı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Sıfırlama sırasında hata oluştu: {e}", ephemeral=True)


@bot.tree.command(name="tümsvrolver", description="👥 Seçilen rolü sunucudaki tüm kullanıcılara toplu olarak verir.")
async def tümsvrolver(interaction: discord.Interaction, rol: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return

    await interaction.response.send_message(f"⏳ `{rol.name}` rolü tüm kullanıcılara dağıtılmaya başlandı...", ephemeral=True)
    
    basarili = 0
    for member in interaction.guild.members:
        try:
            if rol not in member.roles:
                await member.add_roles(rol)
                basarili += 1
        except:
            pass

    await interaction.followup.send(f"✅ İşlem tamamlandı! Toplam **{basarili}** kullanıcıya `{rol.name}` rolü verildi.", ephemeral=True)


@bot.tree.command(name="tümsvrolal", description="👥 Seçilen rolü sunucudaki herkesten toplu olarak alır.")
async def tümsvrolal(interaction: discord.Interaction, rol: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return

    await interaction.response.send_message(f"⏳ `{rol.name}` rolü herkesten alınmaya başlandı...", ephemeral=True)
    
    basarili = 0
    for member in interaction.guild.members:
        try:
            if rol in member.roles:
                await member.remove_roles(rol)
                basarili += 1
        except:
            pass

    await interaction.followup.send(f"✅ İşlem tamamlandı! Toplam **{basarili}** kullanıcından `{rol.name}` rolü alındı.", ephemeral=True)


@bot.tree.command(name="sesgirrazer", description="🔊 AutoRazer botunu seçilen ses kanalına sokar.")
async def sesgirrazer(interaction: discord.Interaction, kanal: discord.VoiceChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(kanal)
    else:
        await kanal.connect()

    await interaction.response.send_message(f"🔊 Başarıyla `{kanal.name}` ses kanalına katıldım!", ephemeral=True)


# --- RENDER ÇALIŞTIRMA ---
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ.get("DISCORD_TOKEN")
    
    if not TOKEN:
        print("❌ HATA: DISCORD_TOKEN bulunamadı! Render Environment Variables kısmını kontrol et.")
    else:
        bot.run(TOKEN)