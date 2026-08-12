import os
import json
import urllib.request
import urllib.parse
import urllib.error

# ---------------------------------------------------------
# CONFIGURATION DES SALONS DISCORD
# ---------------------------------------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
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

def discord_request(url, method="GET", data=None):
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "DiscordBot (https://github.com, 1.0)",
        "Content-Type": "application/json"
    }
    encoded_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, headers=headers, method=method, data=encoded_data)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                return True
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Erreur HTTP {e.code}: {e.read().decode('utf-8')}")
        return None

def main():
    if not TOKEN:
        print("ERREUR : Secret DISCORD_TOKEN manquant.")
        return

    print(f"1. Récupération des messages du salon {SOURCE_CHANNEL_ID}...")
    messages = discord_request(f"https://discord.com/api/v10/channels/{SOURCE_CHANNEL_ID}/messages?limit=20")

    if messages is None:
        print("ERREUR : Impossible de lire le salon source. Vérifiez l'ID et les permissions du bot.")
        return

    print(f"   --> {len(messages)} message(s) récupéré(s). Analyse en cours...")

    # Récupérer l'ID du bot pour éviter qu'il traite ses propres messages
    user_info = discord_request("https://discord.com/api/v10/users/@me")
    bot_id = user_info.get("id") if user_info else None

    for msg in messages:
        msg_id = msg.get("id")
        author_id = msg.get("author", {}).get("id")

        if author_id == bot_id:
            continue

        # Vérifier si le message a déjà la réaction ✅
        reactions = msg.get("reactions", [])
        already_processed = any(r.get("emoji", {}).get("name") == "✅" and r.get("me") for r in reactions)

        if already_processed:
            print(f"Message {msg_id} déjà traité (✅ présent).")
            continue

        # Extraction du texte (message direct + message transféré via message_snapshots)
        content = msg.get("content", "")
        snapshots = msg.get("message_snapshots", [])
        
        if snapshots:
            snap_msg = snapshots[0].get("message", {})
            snap_content = snap_msg.get("content", "")
            if snap_content:
                content += " " + snap_content

        content_lower = content.lower()
        print(f"\n--- Traitement du message ID {msg_id} ---")
        print(f"Contenu analysé : '{content}'")

        # Extraction des images (directes, embeds et transferts)
        image_urls = []

        # 1. Images du message principal
        for att in msg.get("attachments", []):
            if att.get("content_type", "").startswith("image/"):
                image_urls.append(att.get("url"))

        for emb in msg.get("embeds", []):
            if "image" in emb:
                image_urls.append(emb["image"]["url"])
            elif "thumbnail" in emb:
                image_urls.append(emb["thumbnail"]["url"])

        # 2. Images issues des transferts (snapshots)
        for snap in snapshots:
            snap_msg = snap.get("message", {})
            for att in snap_msg.get("attachments", []):
                if att.get("content_type", "").startswith("image/"):
                    image_urls.append(att.get("url"))
            for emb in snap_msg.get("embeds", []):
                if "image" in emb:
                    image_urls.append(emb["image"]["url"])
                elif "thumbnail" in emb:
                    image_urls.append(emb["thumbnail"]["url"])

        # Suppression des doublons d'URLs éventuels
        image_urls = list(set(image_urls))

        # Recherche du mot-clé
        target_channel_id = None
        for channel_id, keywords in KEYWORD_MAPPING.items():
            if any(kw in content_lower for kw in keywords):
                target_channel_id = channel_id
                print(f"Mot-clé détecté pour le salon {channel_id}")
                break

        # Action : Poster le contenu dans le salon cible si trouvé
        if target_channel_id:
            caption = f"📷 New post !"
            if image_urls:
                caption += "\n" + "\n".join(image_urls)

            send_res = discord_request(
                f"https://discord.com/api/v10/channels/{target_channel_id}/messages",
                method="POST",
                data={"content": caption}
            )
            if send_res:
                print(f"--> Transféré avec succès vers le salon {target_channel_id}")
            else:
                print(f"--> Échec du transfert vers {target_channel_id}")
        else:
            print("Aucun mot-clé correspondant dans ce message.")

        # Ajouter la réaction ✅ (encodage URL pour l'emoji)
        emoji_encoded = urllib.parse.quote("✅")
        discord_request(
            f"https://discord.com/api/v10/channels/{SOURCE_CHANNEL_ID}/messages/{msg_id}/reactions/{emoji_encoded}/@me",
            method="PUT"
        )
        print("--> Réaction ✅ ajoutée.")

    print("\nTraitement terminé avec succès.")

if __name__ == "__main__":
    main()
