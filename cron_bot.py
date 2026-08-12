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

async def process_messages():
    await client.login(os.getenv("DISCORD_TOKEN"))
    
    # Lancement de la connexion en tâche de fond
    asyncio.create_task(client.connect())
    await client.wait_until_ready()
    
    print(f" Connecté avec succès en tant que {client.user}")

    try:
        source_channel = client.get_channel(SOURCE_CHANNEL_ID)
        if not source_channel:
            print(f" ERREUR : Le salon ID {SOURCE_CHANNEL_ID} n'a pas été trouvé. Vérifiez l'ID et les accès du bot.")
            return

        print(f" Salon trouvé : #{source_channel.name}. Début de l'analyse...")

        async for message in source_channel.history(limit=20):
            if message.author == client.user:
                continue

            has_been_processed = any(reaction.emoji == "✅" and reaction.me for reaction in message.reactions)
            if has_been_processed:
                continue

            print(f"\n--- Analyse du message ID {message.id} ---")
            print(f"Auteur : {message.author.name}")
            print(f"Contenu : '{message.content}'")

            # Récupération des pièces jointes
            images = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
            
            # Récupération des embeds
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
                    print(f" Mot(s)-clé(s) trouvé(s) : {matched_keywords}")
                    target_channel_id = channel_id
                    break

            if target_channel_id:
                target_channel = client.get_channel(target_channel_id)
                if target_channel:
                    caption = f"📷 Image issue de l'annonce de **{message.author.name}**\n{message.content}"
                    
                    try:
                        if images:
                            files = [await img.to_file() for img in images]
                            await target_channel.send(content=caption, files=files)
                            print(" --> Envoyé dans le salon avec succès !")
                        elif embed_images:
                            urls = "\n".join(embed_images)
                            await target_channel.send(content=f"{caption}\n{urls}")
                            print(" --> Envoyé (embeds) dans le salon avec succès !")
                        else:
                            await target_channel.send(content=caption)
                            print(" --> Texte envoyé sans image.")

                        await message.add_reaction("✅")
                    except Exception as e:
                        print(f" Erreur lors de l'envoi dans le salon {target_channel_id} : {e}")
                else:
                    print(f" ERREUR : Impossible de trouver le salon cible ID {target_channel_id}")
            else:
                print(" Aucun mot-clé correspondant.")
                await message.add_reaction("✅")

    except Exception as err:
        print(f" Erreur pendant le traitement : {err}")
    finally:
        print(" Traitement terminé. Fermeture de la connexion...")
        await client.close()

if __name__ == "__main__":
    asyncio.run(process_messages())
