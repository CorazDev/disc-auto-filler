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

@client.event
async def on_ready():
    print(f"=== Connexion réussie : {client.user} ===")
    
    try:
        # Interroge directement l'API Discord au lieu d'utiliser le cache
        print(f"Recherche du salon source {SOURCE_CHANNEL_ID}...")
        source_channel = await client.fetch_channel(SOURCE_CHANNEL_ID)
        print(f"Salon source trouvé : #{source_channel.name}")

        async for message in source_channel.history(limit=20):
            if message.author == client.user:
                continue

            has_been_processed = any(reaction.emoji == "✅" and reaction.me for reaction in message.reactions)
            if has_been_processed:
                print(f"Message {message.id} déjà traité (✅ présent). Pas de retraitement.")
                continue

            print(f"\n--- Traitement du message ID {message.id} ---")
            print(f"Contenu du message : '{message.content}'")

            # Récupération des images
            images = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
            embed_images = []
            if message.embeds:
                for embed in message.embeds:
                    if embed.image and embed.image.url:
                        embed_images.append(embed.image.url)
                    elif embed.thumbnail and embed.thumbnail.url:
                        embed_images.append(embed.thumbnail.url)

            print(f"Images détectées : {len(images)} fichier(s), {len(embed_images)} embed(s)")

            content_lower = message.content.lower()
            target_channel_id = None

            for channel_id, keywords in KEYWORD_MAPPING.items():
                matched_keywords = [kw for kw in keywords if kw.lower() in content_lower]
                if matched_keywords:
                    print(f"Mot(s)-clé(s) détecté(s) : {matched_keywords}")
                    target_channel_id = channel_id
                    break

            if target_channel_id:
                try:
                    target_channel = await client.fetch_channel(target_channel_id)
                    caption = f"📷 New post ! **{message.author.name}**\n{message.content}"
                    
                    if images:
                        files = [await img.to_file() for img in images]
                        await target_channel.send(content=caption, files=files)
                        print(f"--> Succès : envoyé dans #{target_channel.name}")
                    elif embed_images:
                        urls = "\n".join(embed_images)
                        await target_channel.send(content=f"{caption}\n{urls}")
                        print(f"--> Succès (embed) : envoyé dans #{target_channel.name}")
                    else:
                        await target_channel.send(content=caption)
                        print(f"--> Succès (texte) : envoyé dans #{target_channel.name}")

                    await message.add_reaction("✅")
                except Exception as e:
                    print(f"Erreur lors de l'envoi vers le salon {target_channel_id} : {e}")
            else:
                print("Aucun mot-clé correspondant dans ce message.")
                await message.add_reaction("✅")

    except Exception as e:
        print(f"ERREUR MAJEURE : {e}")

    print("\nFin du traitement. Fermeture du bot.")
    await client.close()

client.run(os.getenv("DISCORD_TOKEN"))
