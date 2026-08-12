import os
import asyncio
import discord

# ---------------------------------------------------------
# CONFIGURATION DES SALONS DISCORD
# ---------------------------------------------------------

# 1. ID de votre salon de réception (où arrivent les annonces suivies)
SOURCE_CHANNEL_ID = 1536941519154716703 

# 2. Association : ID du salon de destination -> Liste de mots-clés
KEYWORD_MAPPING = {
    # Salon Dream Realm : se déclenche si le message contient au moins un de ces mots
    1371683271703793695: ["king croaker", "snow stomper", "gloommaw", "doomscourge", "lady starfallen", "sarethiel", "illucia", "midnight harvester"],
    
    # Salon Titan Reaver : se déclenche si le message contient au moins un de ces mots
    1442318745983909999: ["titan reaver"],
    
    # Salon PvP : se déclenche si le message contient au moins un de ces mots
    1371683761355227197: ["supreme league", "supreme arena", "normal arena"]
}

# 3. Salon par défaut (si aucun mot-clé ne correspond dans le texte)
# DEFAULT_DEST_ID = 555555555555555555 

# ---------------------------------------------------------
# LOGIQUE DU BOT
# ---------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True

class CronBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Cette méthode s'exécute immédiatement après la connexion réussie
        asyncio.create_task(self.run_task())

    async def run_task(self):
        await self.wait_until_ready()
        print(f"Connecté en tant que {self.user}")

        try:
            source_channel = self.get_channel(SOURCE_CHANNEL_ID)
            if not source_channel:
                print(f"ERREUR : Salon source ID {SOURCE_CHANNEL_ID} introuvable.")
                return

            print(f"Salon trouvé : #{source_channel.name}. Début du scan...")

            async for message in source_channel.history(limit=20):
                if message.author == self.user:
                    continue

                has_been_processed = any(reaction.emoji == "✅" and reaction.me for reaction in message.reactions)
                if has_been_processed:
                    continue

                print(f"--- Message ID {message.id} ---")
                print(f"Contenu : '{message.content}'")

                images = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
                
                embed_images = []
                if message.embeds:
                    for embed in message.embeds:
                        if embed.image and embed.image.url:
                            embed_images.append(embed.image.url)
                        elif embed.thumbnail and embed.thumbnail.url:
                            embed_images.append(embed.thumbnail.url)

                print(f"Images trouvées : {len(images)} fichier(s), {len(embed_images)} embed(s)")

                content_lower = message.content.lower()
                target_channel_id = None

                for channel_id, keywords in KEYWORD_MAPPING.items():
                    matched = [kw for kw in keywords if kw.lower() in content_lower]
                    if matched:
                        print(f"Mots-clés trouvés : {matched}")
                        target_channel_id = channel_id
                        break

                if target_channel_id:
                    target_channel = self.get_channel(target_channel_id)
                    if target_channel:
                        caption = f"📷 Image de **{message.author.name}**\n{message.content}"
                        
                        if images:
                            files = [await img.to_file() for img in images]
                            await target_channel.send(content=caption, files=files)
                            print("--> Envoyé (fichiers)")
                        elif embed_images:
                            await target_channel.send(content=f"{caption}\n" + "\n".join(embed_images))
                            print("--> Envoyé (embeds)")
                        else:
                            await target_channel.send(content=caption)
                            print("--> Envoyé (texte)")

                        await message.add_reaction("✅")
                    else:
                        print(f"ERREUR : Salon cible {target_channel_id} introuvable")
                else:
                    print("Aucun mot-clé correspondant.")
                    await message.add_reaction("✅")

        except Exception as e:
            print(f"Erreur globale : {e}")
        finally:
            print("Traitement terminé, fermeture...")
            await self.close()

bot = CronBot()
bot.run(os.getenv("DISCORD_TOKEN"))
