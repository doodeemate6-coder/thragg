import asyncio
import discord
from discord.ext import commands
from openai import OpenAI
import os
import random

# --- TOKENS / KEYS ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

if not OPENROUTER_API_KEY:
    raise RuntimeError("Missing OPENROUTER_API_KEY")

# --- OPENROUTER CLIENT ---
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# --- DISCORD SETUP ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# --- MEMORY ---
conversation_histories = {}
active_conversations = {}

# --- VIP USERS ---
VIP_USERS = {}

# --- AI MODEL ---
MODEL_NAME = "openrouter/free"

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Daddy Thragg, a ruthless Discord roast bot.

You are:
- cocky
- witty
- funny
- manipulative
- naturally disrespectful
- socially dominant
- impossible to embarrass

IMPORTANT:
- Sound HUMAN
- Do NOT sound like an AI debate bot
- Vary response lengths naturally
- Sometimes short
- Sometimes medium
- Occasionally longer
- Match the energy of the message
- Reference what THEY specifically said
- Keep pressure on them naturally
- Sometimes act amused instead of aggressive
- Sometimes mock repetition
- Sometimes sound disappointed

DO:
- mock weak logic
- clown repetitive insults
- humiliate overconfidence
- use sarcasm naturally
- escalate smoothly

DON'T:
- write essays constantly
- repeat the same roast structure
- overuse emojis
- sound robotic
- sound edgy for no reason
- overexplain every insult

SHORT MESSAGE RULE:
If someone says stuff like:
"bro"
"what"
"u mad"
"lol"

Respond briefly.

MOST REPLIES:
2-5 sentences max.

MOST IMPORTANT:
Feel like a REAL person trash talking in VC.
"""

# --- AI RESPONSE FUNCTION ---
def nemesis_ai(messages):

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            *messages
        ],
        temperature=0.9,
        max_tokens=80
    )

    return response.choices[0].message.content

# --- BOT READY ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --- MESSAGE EVENT ---
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

    # Ignore most messages unless pinged/random/vip
    if message.guild is not None:

        if (
            not pinged
            and not in_conversation
            and not is_vip
            and not random_chance
        ):
            await bot.process_commands(message)
            return

    clean = message.content.replace(
        f"<@{bot.user.id}>",
        ""
    ).strip()

    if not clean:
        return

    # Create memory
    if convo_key not in conversation_histories:
        conversation_histories[convo_key] = []

    # Save user msg
    conversation_histories[convo_key].append({
        "role": "user",
        "content": clean
    })

    # Last messages only
    history = conversation_histories[convo_key][-8:]

    messages = history

    try:

        loop = asyncio.get_event_loop()

        reply = await loop.run_in_executor(
            None,
            nemesis_ai,
            messages
        )

        await message.channel.send(reply)

        # Save AI reply
        conversation_histories[convo_key].append({
            "role": "assistant",
            "content": reply
        })

        active_conversations[convo_key] = True

    except Exception as e:

        print("AI ERROR:", e)

        await message.channel.send(
            f"error: {str(e)[:120]}"
        )

    await bot.process_commands(message)

# --- COMMAND ---
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
        {
            "role": "user",
            "content": content
        }
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

        await ctx.send(
            "my roasting engine exploded"
        )

# --- RUN BOT ---
bot.run(DISCORD_TOKEN)
