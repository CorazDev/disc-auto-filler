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
client = discord.Client(intents=intents)

async def run_processing():
    await client.wait_until_ready()
    print(f"Connecté en tant que {client.user}")
    
    source_channel = client.get_channel(SOURCE_CHANNEL_ID)
    
    if source_channel:
        async for message in source_channel.history(limit=20):
            # Éviter de traiter les messages du bot
            if message.author == client.user:
                continue

            # Éviter de traiter un message déjà validé (✅)
            has_been_processed = any(reaction.emoji == "✅" and reaction.me for reaction in message.reactions)
            if has_been_processed:
                continue

            # Récupérer les images
            images = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
            
            embed_images = []
            if not images and message.embeds:
                for embed in message.embeds:
                    if embed.image:
                        embed_images.append(embed.image.url)

            if images or embed_images:
                content_lower = message.content.lower()
                target_channel_id = None

                for channel_id, keywords in KEYWORD_MAPPING.items():
                    if any(keyword in content_lower for keyword in keywords):
                        target_channel_id = channel_id
                        break

                if target_channel_id:
                    target_channel = client.get_channel(target_channel_id)
                    if target_channel:
                        caption = f"📷 Image issue de l'annonce de **{message.author.name}**\n{message.content}"
                        
                        if images:
                            files = [await img.to_file() for img in images]
                            await target_channel.send(content=caption, files=files)
                        elif embed_images:
                            await target_channel.send(content=f"{caption}\n" + "\n".join(embed_images))
                        
                        try:
                            await message.add_reaction("✅")
                        except Exception as e:
                            print(f"Impossible d'ajouter la réaction : {e}")

                else:
                    try:
                        await message.add_reaction("✅")
                    except Exception as e:
                        print(f"Impossible d'ajouter la réaction : {e}")

    await client.close()

async def main():
    async with client:
        # Lance la tâche de traitement et la connexion en parallèle
        asyncio.create_task(run_processing())
        await client.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
