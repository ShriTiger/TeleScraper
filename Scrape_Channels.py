import re
import random
import asyncio
import csv
from telethon import TelegramClient, errors
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.network.connection.tcpfull import ConnectionTcpFull
import os

# ---------------- CONFIG ----------------
api_id = ""
api_hash = ''
phone_number = ''

# How many messages to scrape per channel
# Set to None for ALL messages
MESSAGES_TO_SCRAPE = 100


def extract_username(url):
    match = re.search(r't\.me/([a-zA-Z0-9_]+)', url)
    if match:
        return match.group(1)
    return None

def load_channels(file_path="channels.txt"):
    if not os.path.exists(file_path):
        print(f"[ERROR] {file_path} not found!")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        channels = [line.strip() for line in f if line.strip()]
    print(f"[DEBUG] Loaded {len(channels)} channels from {file_path}")
    return channels


client = TelegramClient(
    'my_session',
    api_id,
    api_hash,
    connection=ConnectionTcpFull,
    connection_retries=10
)


async def scrape_channel(username, limit=None):
    try:
        print(f"[DEBUG] Scraping channel: {username} ...")
        entity = await client.get_entity(username)
        messages = []
        async for message in client.iter_messages(entity, limit=limit):
            messages.append({
                "id": message.id,
                "date": message.date.isoformat() if message.date else None,
                "sender_id": message.sender_id,
                "text": message.message
            })
        print(f"[SUCCESS] Scraped {len(messages)} messages from {username}")
        return messages
    except Exception as e:
        print(f"[ERROR] Failed to scrape {username}: {e}")
        return []


async def main():
    print("[DEBUG] Connecting to Telegram...")

   
    channels = load_channels()
    if not channels:
        print("[ERROR] No channels to scrape. Exiting.")
        return

    
    for attempt in range(1, 6):
        try:
            await client.start(phone=phone_number)
            print("[DEBUG] Connected and authorized successfully!")
            break
        except Exception as e:
            print(f"[WARN] Connection attempt {attempt} failed: {e}")
            await asyncio.sleep(5)
    else:
        print("[ERROR] Could not connect to Telegram after multiple attempts.")
        return

    for channel_url in channels:
        username = extract_username(channel_url)
        if not username:
            print(f"[DEBUG] Invalid URL format: {channel_url}")
            continue

       
        try:
            await client(JoinChannelRequest(username))
            print(f"[SUCCESS] Joined {channel_url}")
        except errors.UserAlreadyParticipantError:
            print(f"[INFO] Already joined {channel_url}")
        except Exception as e:
            print(f"[ERROR] Failed to join {channel_url}: {e}")

        
        messages = await scrape_channel(username, limit=MESSAGES_TO_SCRAPE)

        
        if messages:
            csv_filename = f"{username}_messages.csv"
            with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["id", "date", "sender_id", "message"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for msg in messages:
                    writer.writerow({
                        "id": msg["id"],
                        "date": msg["date"],
                        "sender_id": msg["sender_id"],
                        "message": msg["text"]
                    })
            print(f"[DEBUG] Saved messages to {csv_filename}")

        
        delay = random.randint(10, 30)
        print(f"[DEBUG] Waiting {delay} seconds before next channel...")
        await asyncio.sleep(delay)

    print("[DEBUG] Done! Disconnecting...")
    await client.disconnect()
    print("[DEBUG] Client disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
