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
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Sunucu Yapılandırma Deposu
# { guild_id: { "boost_rol_id": id, "bio_rol_id": id, "erisim_rol_id": id, "tag": ".gg/stormpack", "boost_kanit": id, "bio_kanit": id } }
SERVER_CONFIGS = {}

# Cooldown Takibi (Kullanıcı ID: Son Kanıt Zamanı)
BOOST_COOLDOWN = {}


class RolAyarModal(discord.ui.Modal, title="AutoRazer Güvenli Buton Yapılandırma"):
    tag_input = discord.ui.TextInput(
        label="Bio / Guild İçin Aranacak Tag",
        placeholder=".gg/stormpack",
        required=True,
        max_length=100
    )
    erisim_rol_id = discord.ui.TextInput(
        label="Yetkili Erişim Rol ID",
        placeholder="Sadece bu ID'ye sahip olanlar onaylayabilir",
        required=True,
        max_length=30
    )
    boost_rol_id = discord.ui.TextInput(
        label="2x Boost Rol ID",
        placeholder="Rol ID'sini buraya yapıştırın",
        required=True,
        max_length=30
    )
    bio_rol_id = discord.ui.TextInput(
        label="Bio / Guild Rol ID",
        placeholder="Rol ID'sini buraya yapıştırın",
        required=True,
        max_length=30
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id
        if guild_id not in SERVER_CONFIGS:
            SERVER_CONFIGS[guild_id] = {}

        try:
            SERVER_CONFIGS[guild_id]["erisim_rol_id"] = int(self.erisim_rol_id.value.strip())
            SERVER_CONFIGS[guild_id]["boost_rol_id"] = int(self.boost_rol_id.value.strip())
            SERVER_CONFIGS[guild_id]["bio_rol_id"] = int(self.bio_rol_id.value.strip())
            SERVER_CONFIGS[guild_id]["tag"] = self.tag_input.value.strip()

            await interaction.followup.send(
                f"✅ **AutoRazer Sistemi Başarıyla Yapılandırıldı!**\n"
                f"• **Tag Kriteri:** `{self.tag_input.value}`\n"
                f"• **Yetkili Erişim Rol ID:** `{self.erisim_rol_id.value}`\n"
                f"• **Boost Rol ID:** `{self.boost_rol_id.value}`\n"
                f"• **Bio/Guild Rol ID:** `{self.bio_rol_id.value}`\n\n"
                f"*Sistem hazır: Yetkili rolündekiler kanıtları butonla onaylayabilecek, şartlar bozulursa roller geri alınacaktır.*",
                ephemeral=True
            )
        except ValueError:
            await interaction.followup.send("❌ Hata: Rol ID alanlarına yalnızca sayısal ID değerleri girmelisin!", ephemeral=True)


# --- YETKİLİ ONAY/RED BUTONLARI ---
class KanitOnayButonlari(discord.ui.View):
    def __init__(self, user_id: int, kanit_turu: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.kanit_turu = kanit_turu # "boost" veya "bio"

    def yetkili_mi(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        
        guild_id = interaction.guild.id
        config = SERVER_CONFIGS.get(guild_id)
        if not config:
            return False
        
        erisim_rol_id = config.get("erisim_rol_id")
        for role in interaction.user.roles:
            if role.id == erisim_rol_id:
                return True
        return False

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.green, custom_id="storm_onayla_btn")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.yetkili_mi(interaction):
            await interaction.response.send_message("❌ Bu butonları kullanmak için yetkili erişim rolüne sahip olmalısın!", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.user_id)
        config = SERVER_CONFIGS.get(guild.id)

        if not config:
            await interaction.response.send_message("⚠️ Önce `/rolayarla` ile roller ayarlanmalıdır!", ephemeral=True)
            return

        assigned_role = None
        if self.kanit_turu == "boost":
            assigned_role = guild.get_role(config.get("boost_rol_id"))
        else:
            assigned_role = guild.get_role(config.get("bio_rol_id"))

        if member and assigned_role:
            try:
                await member.add_roles(assigned_role)
            except Exception as e:
                print(f"Rol verme hatası: {e}")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="🚀 Durum", value=f"✅ Onaylayan Yetkili: {interaction.user.mention}", inline=False)
        
        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"✅ Kanıt başarıyla onaylandı ve {member.mention if member else 'kullanıcıya'} rolü verildi!", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.red, custom_id="storm_reddet_btn")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.yetkili_mi(interaction):
            await interaction.response.send_message("❌ Bu butonları kullanmak için yetkili erişim rolüne sahip olmalısın!", ephemeral=True)
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
    print(f"🤖 {bot.user.name} (AutoRazer) butonlu sistemle aktif!")
    print("Authorized By Zynex")
    try:
        synced = await bot.tree.sync()
        print(f"🌲 {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"Komut senkronizasyon hatası: {e}")
    guvenlik_ve_durum_denetimi.start()


# --- KANIT KANAL DİNLEYİCİSİ ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_name = message.channel.name.lower()

    if "2x-boost-kanıt" in channel_name or "bio-guild-kanıt" in channel_name:
        is_boost = "2x-boost-kanıt" in channel_name
        guild = message.guild
        config = SERVER_CONFIGS.get(guild.id)

        if not config:
            try:
                await message.delete()
                uyari = await message.channel.send(f"⚠️ {message.author.mention}, sunucuda `/rolayarla` ile sistem yapılandırılmamış!")
                await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
                await uyari.delete()
            except:
                pass
            return

        # 1. Cooldown Kontrolü (Boost Kanıtı İçin Saatte 1 Hak)
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

        kanit_turu_str = "boost" if is_boost else "bio"

        try:
            await message.delete()
        except:
            pass

        await message.channel.send(embed=embed, view=KanitOnayButonlari(message.author.id, kanit_turu_str))

    await bot.process_commands(message)


# --- SIKI ARKA PLAN KONTROLÜ (ŞARTLAR BOZULURSA ROLÜ GERİ ALMA) ---
@tasks.loop(seconds=10)
async def guvenlik_ve_durum_denetimi():
    for guild in bot.guilds:
        config = SERVER_CONFIGS.get(guild.id)
        if not config:
            continue

        boost_rol_id = config.get("boost_rol_id")
        bio_rol_id = config.get("bio_rol_id")
        target_tag = config.get("tag", "").lower()
        
        boost_role = guild.get_role(boost_rol_id)
        bio_role = guild.get_role(bio_rol_id)
        boost_log_id = config.get("boost_kanit")
        bio_log_id = config.get("bio_kanit")

        # 1. Bio / Guild Rolüne Sahip Olanların Tag Kontrolü
        if bio_role and target_tag:
            for member in list(bio_role.members):
                if member.bot:
                    continue
                try:
                    profile = await member.fetch_profile()
                    user_bio = (profile.bio or "").lower()
                    user_name = member.name.lower()
                    user_nick = (member.nick or "").lower()
                    
                    has_tag = target_tag in user_bio or target_tag in user_name or target_tag in user_nick

                    if not has_tag:
                        await member.remove_roles(bio_role)
                        if bio_log_id:
                            log_ch = guild.get_channel(bio_log_id)
                            if log_ch:
                                embed = discord.Embed(
                                    title="🛑 Bio / Tag Kaldırıldı (Rol Geri Alındı)",
                                    description=f"**Kullanıcı:** {member.mention}\n**Kullanıcı ID:** `{member.id}`\n\n⚠️ Kullanıcı `{target_tag}` tagini kaldırdığı için rolü otomatik geri alındı.",
                                    color=discord.Color.red(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.set_footer(text="Authorized By Zynex")
                                await log_ch.send(embed=embed)
                except Exception as e:
                    pass

        # 2. Boost Rolüne Sahip Olanların Takviye Kontrolü
        if boost_role:
            for member in list(boost_role.members):
                if member.bot:
                    continue
                if member.premium_since is None:
                    try:
                        await member.remove_roles(boost_role)
                        if boost_log_id:
                            log_ch = guild.get_channel(boost_log_id)
                            if log_ch:
                                embed = discord.Embed(
                                    title="🚨 Boost İptal Edildi (Rol Geri Alındı)",
                                    description=f"**Kullanıcı:** {member.mention}\n**Kullanıcı ID:** `{member.id}`\n\n⚠️ Kullanıcının takviyesi bittiği için `{boost_role.name}` rolü otomatik geri alındı.",
                                    color=discord.Color.red(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.set_footer(text="Authorized By Zynex")
                                await log_ch.send(embed=embed)
                    except Exception as e:
                        pass


# --- SLASH KOMUTLARI ---

@bot.tree.command(name="rolayarla", description="⚙️ Sistem için yetkili rolü, tag ve rol ID'lerini ayarlar.")
async def rolayarla(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return
    await interaction.response.send_modal(RolAyarModal())


@bot.tree.command(name="logpanelkurrazer", description="🚀 Kanıt panellerini kurar.")
async def logpanelkurrazer(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return

    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    kategori = await guild.create_category("🚀 AUTO RAZER YETKİLİ PANEL", overwrites=overwrites)
    boost_kanali = await guild.create_text_channel("🚀-2x-boost-kanıt", category=kategori)
    bio_kanali = await guild.create_text_channel("🟩-bio-guild-kanıt", category=kategori)

    SERVER_CONFIGS[guild.id] = SERVER_CONFIGS.get(guild.id, {})
    SERVER_CONFIGS[guild.id].update({
        "kategori": kategori.id,
        "boost_kanit": boost_kanali.id,
        "bio_kanit": bio_kanali.id
    })

    embed = discord.Embed(
        title="⚙️ AutoRazer Yetkili Paneli Kuruldu",
        description=f"Kanıt kanalları oluşturuldu:\n\n• {boost_kanali.mention}\n• {bio_kanali.mention}\n\n*Not: `/rolayarla` komutu ile yetkili erişim rolünü ve rolleri bağlamayı unutma!*",
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
        await interaction.response.send_message(f"🗑️ Bulunan kanıt kanalları temizlendi! (Silinen: {silinen})", ephemeral=True)
        return

    try:
        kategori = guild.get_channel(config["kategori"])
        if kategori:
            for ch in kategori.channels:
                await ch.delete()
            await kategori.delete()
        
        SERVER_CONFIGS.pop(guild.id, None)
        await interaction.response.send_message("🗑️ AutoRazer log paneli tamamen sıfırlandı.", ephemeral=True)
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
        print("❌ HATA: DISCORD_TOKEN bulunamadı!")
    else:
        bot.run(TOKEN)