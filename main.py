import asyncio
import discord
from discord.ext import commands
from groq import Groq
import os
import random

# =========================
# TOKENS / API KEYS
# =========================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY")

# =========================
# GROQ CLIENT
# =========================

client = Groq(
    api_key=GROQ_API_KEY
)

# =========================
# DISCORD SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# MEMORY
# =========================

conversation_histories = {}
active_conversations = {}

VIP_USERS = {}

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
You are Daddy Thragg, a ruthless Discord roast bot.

You are:
- cocky
- witty
- naturally funny
- manipulative
- dismissive
- socially dominant
- impossible to embarrass

IMPORTANT:
- Sound HUMAN
- Never sound like an AI assistant
- Never sound formal
- Vary response lengths naturally
- Sometimes short
- Sometimes medium
- Occasionally longer
- Match the user's energy
- Reference what THEY actually said
- Keep pressure on them naturally
- Occasionally sound amused instead of aggressive
- Occasionally act disappointed by weak insults
- Avoid repetitive roast structures

DO:
- mock weak logic
- clown repetitive insults
- humiliate overconfidence
- use sarcasm naturally
- escalate smoothly

DON'T:
- write giant essays constantly
- repeat the same insult style
- overuse emojis
- sound robotic
- sound edgy for no reason
- explain every insult

SHORT MESSAGE RULE:
If someone sends:
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

# =========================
# AI FUNCTION
# =========================

def nemesis_ai(messages):

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            *messages
        ],
        temperature=0.9,
        max_tokens=100
    )

    return response.choices[0].message.content

# =========================
# READY EVENT
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# =========================
# MESSAGE EVENT
# =========================

@bot.event
async def on_message(message):

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

    # Save user message
    conversation_histories[convo_key].append({
        "role": "user",
        "content": clean
    })

    # Keep recent history only
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
            "my roasting engine exploded"
        )

    await bot.process_commands(message)

# =========================
# !nemesis COMMAND
# =========================

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

# =========================
# RUN BOT
# =========================

bot.run(DISCORD_TOKEN)
