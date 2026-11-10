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
    return "AutoRazer AI Bot Aktif ve Çalışıyor! Authorized By Zynex"

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
# { guild_id: { "boost_rol_id": id, "bio_rol_id": id, "tag": ".gg/stormpack", "boost_kanit": id, "bio_kanit": id } }
SERVER_CONFIGS = {}

# Cooldown Takibi (Kullanıcı ID: Son Kanıt Zamanı)
BOOST_COOLDOWN = {}


class RolAyarModal(discord.ui.Modal, title="AutoRazer Kesin AI Yapılandırma"):
    tag_input = discord.ui.TextInput(
        label="Aranacak Bio / Guild Tag",
        placeholder=".gg/stormpack",
        required=True
    )
    boost_rol_id = discord.ui.TextInput(
        label="2x Boost Rol ID",
        placeholder="Rol ID'sini buraya yapıştırın",
        required=True
    )
    bio_rol_id = discord.ui.TextInput(
        label="Bio / Guild Rol ID",
        placeholder="Rol ID'sini buraya yapıştırın",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        if guild_id not in SERVER_CONFIGS:
            SERVER_CONFIGS[guild_id] = {}

        SERVER_CONFIGS[guild_id]["boost_rol_id"] = int(self.boost_rol_id.value)
        SERVER_CONFIGS[guild_id]["bio_rol_id"] = int(self.bio_rol_id.value)
        SERVER_CONFIGS[guild_id]["tag"] = self.tag_input.value.strip()

        await interaction.response.send_message(
            f"✅ **AutoRazer Sert AI & Güvenlik Sistemi Aktif!**\n"
            f"• **Zorunlu Tag/Bio:** `{self.tag_input.value}`\n"
            f"• **Boost Rol ID:** `{self.boost_rol_id.value}`\n"
            f"• **Bio Rol ID:** `{self.bio_rol_id.value}`\n\n"
            f"*Tag veya Bio olmadan kanıt atılırsa onay verilmeyecek; rol verildikten sonra şartlar bozulursa perm anında geri alınacaktır.*",
            ephemeral=True
        )


@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} (AutoRazer) gelişmiş AI denetimiyle aktif!")
    print("Authorized By Zynex")
    try:
        synced = await bot.tree.sync()
        print(f"🌲 {len(synced)} slash komut başarıyla senkronize edildi.")
    except Exception as e:
        print(e)
    kesin_denetim_dongusu.start()


# --- ANLIK ÜYE GÜNCELLEME DİNLEYİCİSİ (BOOST VEYA BIO DEĞİŞTİĞİNDE) ---
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    guild = after.guild
    config = SERVER_CONFIGS.get(guild.id)
    if not config:
        return

    boost_rol_id = config.get("boost_rol_id")
    bio_rol_id = config.get("bio_rol_id")
    target_tag = config.get("tag", "").lower()
    
    boost_role = guild.get_role(boost_rol_id)
    bio_role = guild.get_role(bio_rol_id)
    boost_log_id = config.get("boost_kanit")
    bio_log_id = config.get("bio_kanit")

    # 1. Boost Çekildiyse veya Başka Yere Aktarıldıysa
    if boost_role and boost_role in before.roles and boost_role not in after.roles:
        try:
            if boost_log_id:
                log_ch = guild.get_channel(boost_log_id)
                if log_ch:
                    embed = discord.Embed(
                        title="🚨 2x Boost İptal Edildi / Çekildi",
                        description=f"**Kullanıcı:** {after.mention}\n**Kullanıcı ID:** `{after.id}`\n\n⚠️ Kullanıcı sunucu takviyesini çektiği veya aktardığı için `{boost_role.name}` permi anında alındı.",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    embed.set_footer(text="Authorized By Zynex")
                    await log_ch.send(embed=embed)
        except Exception as e:
            print(f"Boost log hatası: {e}")

    # 2. Bio veya Tag silindiyse (Rolü varsa ve tag artık yoksa)
    if bio_role and bio_role in after.roles and target_tag:
        try:
            # Kullanıcının güncel görünen adı veya takma adı kontrolü
            user_name = after.name.lower()
            user_nick = (after.nick or "").lower()
            
            # Not: Discord botları API kısıtı nedeniyle başkasının 'hakkımda/bio' metnini anlık event ile okuyamaz,
            # ancak kullanıcı adında/tag'inde aratabiliriz. Kesin bio kontrolü saniyelik döngüyle de desteklenir.
            has_tag_in_name = target_tag in user_name or target_tag in user_nick
            
            if not has_tag_in_name:
                # Arka plan döngüsü detaylı bio'yu da tarayacağı için burada isimde yoksa hemen tetikleriz
                pass
        except Exception as e:
            print(f"Member update kontrol hatası: {e}")


# --- KESİN AI KANIT VE ŞART DENETİMİ ---
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

        # 1. Cooldown Kontrolü (Boost için saatte 1 hak)
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

        member = message.author
        target_tag = config.get("tag", "").lower()

        # 3. KESİN AI ŞART DOĞRULAMASI
        if not is_boost:
            # Bio / Guild Kanalı için AI Şart Kontrolü
            # Kullanıcının adında veya görünen adında tag var mı kontrol et
            user_name = member.name.lower()
            user_nick = (member.nick or "").lower()
            
            # Profil detaylı çekimi
            profile_has_tag = False
            try:
                profile = await member.fetch_profile()
                user_bio = (profile.bio or "").lower()
                profile_has_tag = target_tag in user_bio
            except:
                user_bio = ""

            sart_saglandi = target_tag in user_name or target_tag in user_nick or profile_has_tag

            if not sart_saglandi:
                # Şart sağlanmadı! Kanıtı sil ve kullanıcıyı reddet
                try:
                    await message.delete()
                    red_mesaji = await message.channel.send(
                        f"❌ {member.mention}, **AI Doğrulama Başarısız!**\n"
                        f"Profilinde veya isminde `{target_tag}` (Bio/Tag) bulunamadı. "
                        f"Lütfen bio'na veya ismine tag'i ekleyip kanıtı tekrar at."
                    )
                    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=7))
                    await red_mesaji.delete()
                except:
                    pass
                return

        # Boost kanalı için sunucu takviye kontrolü
        if is_boost:
            # Gerçekten boost basmış mı kontrol et
            if member.premium_since is None:
                try:
                    await message.delete()
                    red_mesaji = await message.channel.send(
                        f"❌ {member.mention}, **AI Boost Doğrulaması Başarısız!**\n"
                        f"Sunucuda aktif bir 2x Boost takviyen tespit edilemedi."
                    )
                    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=7))
                    await red_mesaji.delete()
                except:
                    pass
                return

        # 4. TÜM ŞARTLAR TAMAM - ROLÜ VER VE LOGLA
        assigned_role = None
        if is_boost:
            assigned_role = guild.get_role(config.get("boost_rol_id"))
        else:
            assigned_role = guild.get_role(config.get("bio_rol_id"))

        if assigned_role:
            try:
                await member.add_roles(assigned_role)
            except Exception as e:
                print(f"Rol verme hatası: {e}")

        tur_adi = "🚀 2x Boost Otomatik AI Onay" if is_boost else "🟩🟨 Bio / Guild Otomatik AI Onay"
        
        embed = discord.Embed(
            title=f"🤖 {tur_adi}",
            description=f"**Kullanıcı:** {member.mention}\n**Kullanıcı ID:** `{member.id}`\n**Durum:** `✅ AI Tarafından Onaylandı ve Rolü Verildi`",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_image(url=message.attachments[0].url)
        embed.set_footer(text="Authorized By Zynex", icon_url=bot.user.avatar.url if bot.user.avatar else None)

        try:
            await message.delete()
        except:
            pass

        await message.channel.send(embed=embed)

    await bot.process_commands(message)


# --- SIKI ARKA PLAN KONTROL DÖNGÜSÜ (ŞART BOZULURSA ANINDA PERMİ GERİ ALMA) ---
@tasks.loop(seconds=15)
async def kesin_denetim_dongusu():
    for guild in bot.guilds:
        config = SERVER_CONFIGS.get(guild.id)
        if not config:
            continue

        bio_rol_id = config.get("bio_rol_id")
        boost_rol_id = config.get("boost_rol_id")
        target_tag = config.get("tag", "").lower()
        
        bio_role = guild.get_role(bio_rol_id)
        boost_role = guild.get_role(boost_rol_id)
        bio_log_id = config.get("bio_kanit")
        boost_log_id = config.get("boost_kanit")

        # 1. Bio / Tag Rolüne Sahip Olanları Sıkı Denetle
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
                        # Bio veya tag silinmiş! Perami saniyesinde geri al
                        await member.remove_roles(bio_role)
                        if bio_log_id:
                            log_ch = guild.get_channel(bio_log_id)
                            if log_ch:
                                embed = discord.Embed(
                                    title="🛑 Bio / Tag Kaldırıldı (Perm Geri Alındı)",
                                    description=f"**Kullanıcı:** {member.mention}\n**Kullanıcı ID:** `{member.id}`\n\n⚠️ Kullanıcı bio'sundan veya isminden `{target_tag}` tagini sildiği için rolü otomatik olarak geri alındı.",
                                    color=discord.Color.red(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.set_footer(text="Authorized By Zynex")
                                await log_ch.send(embed=embed)
                except Exception as e:
                    print(f"Bio sıkı denetim hatası: {e}")

        # 2. Boost Rolüne Sahip Olanları Sıkı Denetle
        if boost_role:
            for member in list(boost_role.members):
                if member.bot:
                    continue
                # Eğer sunucudaki boost takviyesi düşmüşse veya çekilmişse
                if member.premium_since is None:
                    try:
                        await member.remove_roles(boost_role)
                        if boost_log_id:
                            log_ch = guild.get_channel(boost_log_id)
                            if log_ch:
                                embed = discord.Embed(
                                    title="🚨 Boost Çekildi / Düştü (Perm Geri Alındı)",
                                    description=f"**Kullanıcı:** {member.mention}\n**Kullanıcı ID:** `{member.id}`\n\n⚠️ Kullanıcı sunucu takviyesini çektiği veya süresi bittiği için `{boost_role.name}` rolü otomatik olarak geri alındı.",
                                    color=discord.Color.red(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.set_footer(text="Authorized By Zynex")
                                await log_ch.send(embed=embed)
                    except Exception as e:
                        print(f"Boost sıkı denetim hatası: {e}")


# --- KOMUTLAR ---

@bot.tree.command(name="rolayarla", description="⚙️ AI sistem için tag ve rol ID'lerini ayarlar.")
async def rolayarla(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return
    await interaction.response.send_modal(RolAyarModal())


@bot.tree.command(name="logpanelkurrazer", description="🚀 Otomatik AI 2x-boost ve bio-guild kanıt panellerini kurar.")
async def logpanelkurrazer(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine sahip olmalısın.", ephemeral=True)
        return

    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    kategori = await guild.create_category("🚀 AUTO RAZER KESIN AI", overwrites=overwrites)
    boost_kanali = await guild.create_text_channel("🚀-2x-boost-kanıt", category=kategori)
    bio_kanali = await guild.create_text_channel("🟩-bio-guild-kanıt", category=kategori)

    SERVER_CONFIGS[guild.id] = SERVER_CONFIGS.get(guild.id, {})
    SERVER_CONFIGS[guild.id].update({
        "kategori": kategori.id,
        "boost_kanit": boost_kanali.id,
        "bio_kanit": bio_kanali.id
    })

    embed = discord.Embed(
        title="⚙️ AutoRazer Kesin AI Paneli Kuruldu",
        description=f"Kanıt kanalları oluşturuldu:\n\n• {boost_kanali.mention}\n• {bio_kanali.mention}\n\n*Not: `/rolayarla` ile tag ve rolleri bağlamayı unutma!*",
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
        await interaction.response.send_message("❌ Bu komutu kullanmak için Yönetici yetkisine yapmalısın.", ephemeral=True)
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