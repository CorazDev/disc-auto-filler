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

def download_file(url):
    """Télécharge un fichier (image) depuis Discord."""
    req = urllib.request.Request(url, headers={"User-Agent": "DiscordBot (https://github.com, 1.0)"})
    try:
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(f"Impossible de télécharger l'image {url} : {e}")
        return None

def send_message_with_files(channel_id, content, image_urls):
    """Envoie un message avec de vrais fichiers joints (multipart/form-data)."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()

    # Télécharger les images
    files = []
    for idx, url in enumerate(image_urls):
        file_bytes = download_file(url)
        if file_bytes:
            filename = f"image_{idx}.jpg"
            files.append((filename, file_bytes))

    # Construire la charge utile JSON
    payload_json = {"content": content}
    if files:
        payload_json["attachments"] = [{"id": i, "filename": f[0]} for i, f in enumerate(files)]

    # 1. Ajouter le champ 'payload_json'
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend('Content-Disposition: form-data; name="payload_json"\r\n'.encode("utf-8"))
    body.extend('Content-Type: application/json\r\n\r\n'.encode("utf-8"))
    body.extend(json.dumps(payload_json).encode("utf-8"))
    body.extend(b"\r\n")

    # 2. Ajouter les fichiers images
    for i, (filename, file_bytes) in enumerate(files):
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="files[{i}]"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend('Content-Type: image/jpeg\r\n\r\n'.encode("utf-8"))
        body.extend(file_bytes)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "DiscordBot (https://github.com, 1.0)",
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }

    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        headers=headers,
        method="POST",
        data=bytes(body)
    )

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Erreur lors de l'envoi multipart {e.code}: {e.read().decode('utf-8')}")
        return None

def main():
    if not TOKEN:
        print("ERREUR : Secret DISCORD_TOKEN manquant.")
        return

    print(f"1. Récupération des messages du salon {SOURCE_CHANNEL_ID}...")
    messages = discord_request(f"https://discord.com/api/v10/channels/{SOURCE_CHANNEL_ID}/messages?limit=20")

    if messages is None:
        print("ERREUR : Impossible de lire le salon source.")
        return

    user_info = discord_request("https://discord.com/api/v10/users/@me")
    bot_id = user_info.get("id") if user_info else None

    for msg in messages:
        msg_id = msg.get("id")
        author_id = msg.get("author", {}).get("id")

        if author_id == bot_id:
            continue

        reactions = msg.get("reactions", [])
        already_processed = any(r.get("emoji", {}).get("name") == "✅" and r.get("me") for r in reactions)

        if already_processed:
            continue

        # Extraction du texte (message direct + message transféré via message_snapshots)
        content = msg.get("content", "")
        snapshots = msg.get("message_snapshots", [])
        
        if snapshots:
            snap_msg = snapshots[0].get("message", {})
            snap_content = snap_msg.get("content", "")
            if snap_content:
                content = (content + "\n" + snap_content).strip()

        content_lower = content.lower()

        # Extraction des images (pièces jointes réelles uniquement pour éviter le doublon d'aperçu)
        image_urls = []

        # 1. Pièces jointes du message direct
        for att in msg.get("attachments", []):
            if att.get("content_type", "").startswith("image/"):
                image_urls.append(att.get("url"))

        # 2. Pièces jointes des messages transférés (snapshots)
        for snap in snapshots:
            snap_msg = snap.get("message", {})
            for att in snap_msg.get("attachments", []):
                if att.get("content_type", "").startswith("image/"):
                    image_urls.append(att.get("url"))

        image_urls = list(set(image_urls))

        # Recherche du mot-clé et stockage du mot qui a matché
        target_channel_id = None
        matched_keyword = None

        for channel_id, keywords in KEYWORD_MAPPING.items():
            for kw in keywords:
                if kw in content_lower:
                    target_channel_id = channel_id
                    matched_keyword = kw
                    break
            if target_channel_id:
                break

        # Action de reposting
        if target_channel_id:
            author_name = msg.get('author', {}).get('username')
            
            # Formatage avec le mot-clé en grand et en gras au début
            caption = f"# **{matched_keyword.upper()}**\n{content}"

            send_res = send_message_with_files(target_channel_id, caption, image_urls)
            if send_res:
                print(f"--> Posté avec succès dans le salon {target_channel_id}")
            else:
                print(f"--> Échec du transfert vers {target_channel_id}")
        else:
            print("Aucun mot-clé correspondant.")

        # Marquer comme traité avec ✅
        emoji_encoded = urllib.parse.quote("✅")
        discord_request(
            f"https://discord.com/api/v10/channels/{SOURCE_CHANNEL_ID}/messages/{msg_id}/reactions/{emoji_encoded}/@me",
            method="PUT"
        )

if __name__ == "__main__":
    main()
