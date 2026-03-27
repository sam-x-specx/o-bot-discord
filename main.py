import os
import threading
import django
from django.conf import settings
from django.http import HttpResponse
from django.urls import path
from dotenv import load_dotenv

load_dotenv()

# ─── Django Setup ─────────────────────────────────────────────────────────────
if not settings.configured:
    settings.configure(
        DEBUG=False,
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF=__name__,
        SECRET_KEY="render-keep-alive-secret-key",
    )

def index(request):
    return HttpResponse("✅ Bot is alive!")

def health(request):
    return HttpResponse("OK")

urlpatterns = [
    path("", index),
    path("health/", health),
]

django.setup()

# ─── Discord Bot ──────────────────────────────────────────────────────────────
import discord
from discord import app_commands
import requests as req

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY  = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
client  = discord.Client(intents=intents)
tree    = app_commands.CommandTree(client)


def ask_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user",   "content": prompt}
        ]
    }
    try:
        response = req.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Error: {str(e)}"


def split_message(text, max_length=2000):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot is online as {client.user}")


@tree.command(name="obot", description="Ask AI anything")
async def obot(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    reply = ask_groq(message)
    for part in split_message(reply):
        await interaction.followup.send(part)


# ─── Run Bot in Background Thread ─────────────────────────────────────────────
def run_bot():
    client.run(DISCORD_TOKEN)

threading.Thread(target=run_bot, daemon=True).start()

# ─── Expose Django WSGI for Gunicorn ──────────────────────────────────────────
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
