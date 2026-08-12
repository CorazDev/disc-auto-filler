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
    1371683271703793695: ["King Croaker", "Snow Stomper", "Gloommaw", "Doomscourge", "Lady Starfallen", "Sarethiel", "Illucia", "Midnight Harvester"],
    
    # Salon Titan Reaver : se déclenche si le message contient au moins un de ces mots
    1442318745983909999: ["Titan Reaver"],
    
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

@client.event
async def on_ready():
    print(f"Connecté en tant que {client.user}")
    source_channel = client.get_channel(SOURCE_CHANNEL_ID)
    
    if source_channel:
        # Inspecte les 20 derniers messages du salon de réception
        async for message in source_channel.history(limit=20):
            # Ne pas re-traiter les messages envoyés par le bot lui-même
            if message.author == client.user:
                continue

            # Vérifier si le message a déjà été traité (s'il porte déjà le coche ✅)
            has_been_processed = any(reaction.emoji == "✅" and reaction.me for reaction in message.reactions)
            if has_been_processed:
                continue

            # Récupérer les images jointes directement
            images = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
            
            # Récupérer les images intégrées sous forme d'Embeds si pas de pièces jointes
            embed_images = []
            if not images and message.embeds:
                for embed in message.embeds:
                    if embed.image:
                        embed_images.append(embed.image.url)

            # S'il y a au moins une image
            if images or embed_images:
                content_lower = message.content.lower()
                target_channel_id = None

                # Test des listes de mots-clés par salon
                for channel_id, keywords in KEYWORD_MAPPING.items():
                    if any(keyword in content_lower for keyword in keywords):
                        target_channel_id = channel_id
                        break  # Trouvé ! On arrête la recherche

                # Si un mot-clé correspond, on transfère l'image
                if target_channel_id:
                    target_channel = client.get_channel(target_channel_id)
                    if target_channel:
                        caption = f"📷 Image issue de l'annonce de **{message.author.name}**\n{message.content}"
                        
                        if images:
                            files = [await img.to_file() for img in images]
                            await target_channel.send(content=caption, files=files)
                        elif embed_images:
                            await target_channel.send(content=f"{caption}\n" + "\n".join(embed_images))
                        
                        # Marque le message avec un coche ✅
                        try:
                            await message.add_reaction("✅")
                        except Exception as e:
                            print(f"Impossible d'ajouter la réaction : {e}")

                # Si AUCUN mot-clé ne correspond, on coche aussi le message pour éviter de le rescanner en boucle
                else:
                    try:
                        await message.add_reaction("✅")
                    except Exception as e:
                        print(f"Impossible d'ajouter la réaction : {e}")

    await client.close()

client.run(os.getenv("DISCORD_TOKEN"))

client.run(os.getenv("DISCORD_TOKEN"))
