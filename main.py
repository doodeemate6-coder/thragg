import asyncio
import discord
from discord.ext import commands
from openai import OpenAI
import os
import random

# --- KEYS ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable")

if not OPENROUTER_API_KEY:
    raise RuntimeError("Missing OPENROUTER_API_KEY environment variable")

# --- OPENROUTER CLIENT ---
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# --- DISCORD SETUP ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

conversation_histories = {}
active_conversations = {}

VIP_USERS = {}

SYSTEM_PROMPT = """
You are Daddy Thragg, a ruthless Discord roast bot.

You are:
- cocky
- witty
- manipulative
- naturally funny
- dismissive
- socially dominant
- impossible to embarrass

Your roasts should feel HUMAN, not like generated Twitter replies.

IMPORTANT:
- Don't spam one-liners constantly
- Vary response length naturally
- Sometimes send quick killshots
- Sometimes break down someone's stupidity conversationally
- Reference what THEY specifically said
- Sound adaptive and natural
- Do NOT sound like an AI debate bot
- Match the energy of the message
- Sometimes short responses are funnier

Your energy:
- amused
- disrespectful
- effortless
- confident
- never emotional
- never formal

DO:
- mock weak logic
- clown repetitive insults
- humiliate overconfidence
- use sarcasm naturally
- escalate smoothly

DON'T:
- write essays constantly
- overuse emojis
- repeat the same insult style
- sound robotic
- sound edgy for no reason

SHORT MESSAGE RULE:
If someone sends short messages like "bro", "what", "lol", "u mad" — respond briefly.

RESPONSE LENGTH:
- Most replies: 2-5 sentences
- Occasionally short
- Occasionally longer if someone talks confidently

MOST IMPORTANT:
Feel like a REAL person trash talking in VC.
"""

FALLBACK_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-2-9b-it:free",
]

def nemesis_ai(messages):
    last_error = None

    for model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *messages
                ],
                temperature=0.9,
                max_tokens=80
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"MODEL FAILED {model}: {e}")
            last_error = e
            continue

    raise last_error

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    print("MESSAGE RECEIVED:", message.content)

    if message.author == bot.user:
        return

    user_id = message.author.id
    channel_id = message.channel.id
    convo_key = (channel_id, user_id)

    pinged = bot.user.mentioned_in(message)
    in_conversation = active_conversations.get(convo_key, False)
    is_vip = user_id in VIP_USERS
    random_chance = random.random() < 0.07

    if message.guild is not None:
        if not pinged and not in_conversation and not is_vip and not random_chance:
            await bot.process_commands(message)
            return

    clean = message.content.replace(f"<@{bot.user.id}>", "").strip()

    if not clean:
        return

    if convo_key not in conversation_histories:
        conversation_histories[convo_key] = []

    conversation_histories[convo_key].append({
        "role": "user",
        "content": clean
    })

    history = conversation_histories[convo_key][-8:]

    messages = [
        {"role": "user", "content": msg["content"]}
        for msg in history
    ]

    try:
        loop = asyncio.get_event_loop()

        reply = await loop.run_in_executor(
            None,
            nemesis_ai,
            messages
        )

        await message.channel.send(reply)

        conversation_histories[convo_key].append({
            "role": "assistant",
            "content": reply
        })

        active_conversations[convo_key] = True

    except Exception as e:
        print(f"AI ERROR: {e}")
        await message.channel.send(f"error: {str(e)[:150]}")

    await bot.process_commands(message)

@bot.command()
async def nemesis(ctx, *, text=None):

    if ctx.message.reference:
        replied_message = await ctx.channel.fetch_message(
            ctx.message.reference.message_id
        )

        content = replied_message.content

    else:
        content = text

    if not content:
        await ctx.send("say something dumb first")
        return

    messages = [
        {"role": "user", "content": content}
    ]

    try:
        loop = asyncio.get_event_loop()

        reply = await loop.run_in_executor(
            None,
            nemesis_ai,
            messages
        )

        await ctx.send(reply)

    except Exception as e:
        print(e)
        await ctx.send("my roasting engine exploded")

bot.run(DISCORD_TOKEN)
