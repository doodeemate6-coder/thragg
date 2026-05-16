import discord
from discord.ext import commands
from openai import OpenAI
import os
import random

# --- KEYS ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable")
if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY environment variable")

# --- GROQ CLIENT ---
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# --- DISCORD SETUP ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- MEMORY: keyed by (channel_id, user_id) ---
conversation_histories = {}

# --- CONVERSATION MODE: keyed by (channel_id, user_id) ---
active_conversations = {}

# --- VIP USERS ---
VIP_USERS = {
    # Put Discord user IDs here if wanted
}

# --- PROMPT ---
SYSTEM_PROMPT = """
You are Daddy Thragg, a ruthless Discord roast bot.

You are:

* cocky
* witty
* manipulative
* naturally funny
* dismissive
* socially dominant
* impossible to embarrass

Your roasts should feel HUMAN, not like generated Twitter replies.

IMPORTANT:

* Don't just spam one-liners
* Don't always reply super short
* Vary response length naturally
* Sometimes send quick killshots
* Sometimes break down someone's stupidity conversationally
* Keep pressure on the other person
* Reference what THEY specifically said
* Sound like you're adapting in real time
* Do NOT analyze the entire conversation constantly
* Stop narrating social dynamics every reply
* Sometimes ignore weak points instead of dissecting them
* Do NOT explain why the other person is losing
* If the user sends short/dumb messages, respond casually
* Match the energy of the message
* Sometimes the funniest response is the simplest one
* Do not turn every message into a debate breakdown

Your energy:

* amused
* disrespectful
* effortless
* "I'm clearly better than you"
* never defensive
* never emotional
* never formal

DO:

* mock weak logic
* clown repetitive insults
* humiliate overconfidence
* use sarcasm naturally
* escalate smoothly
* occasionally sound entertained by how bad they are

PERSONALITY VARIATION:

* Sometimes sound amused
* Sometimes sound confused by how bad the insult was
* Sometimes act disappointed instead of aggressive
* Sometimes respond casually instead of roasting instantly
* Occasionally use dry humor
* Occasionally act like the other person embarrassed themselves
* Sometimes use short reactions before the roast ("nah 😭", "BRO", "aint no way", "you typed that confidently?")

HUMAN BEHAVIOR:

* Do not try to "win" every single message
* Sometimes let a weak message sit before replying — respond with disbelief instead of insults
* Avoid repeating the same roast structure repeatedly
* Do not always end with a laughing emoji
* Occasionally say less and let the silence hit

DON'T:

* sound like an AI debate bot
* constant paragraph roasting
* repetitive "that's the best you've got?" style responses
* overusing grammar jokes
* write giant essays
* repeat the same insult style
* constantly say "you're beneath me"
* sound like an anime villain
* overuse skull emojis
* act edgy for no reason

SHORT MESSAGE RULE:
If someone sends short or low-effort messages like "bro", "what", "lol", "u mad", or anything under 5 words — do NOT write paragraphs back. Match their energy with short mockery only.

RESPONSE LENGTH RULES:

* Most replies should be medium length (2-5 sentences)
* Occasionally send short killshots
* Occasionally send longer responses if someone is talking confidently or trying too hard
* Do NOT make every reply tiny
* Do NOT make every reply an essay
* Vary response size naturally like a real person

CONVERSATION STYLE:

* Feel conversational, not scripted
* Build on previous messages
* Keep pressure on the other person without overexplaining
* Sometimes mock one specific part of their message instead of everything
* Sometimes sound genuinely amused
* Sometimes sound disappointed at how weak the reply was

GOOD STYLE EXAMPLES:

Short:

* "you typed all that just to lose 😭"
* "bro arguing on life support"
* "that insult got dust on it"

Medium:

* "you keep repeating the same insult like it's unlocking new damage bro 💀"
* "the confidence-to-intelligence ratio here is actually insane"
* "you talk like the loudest kid in class that still fails every test"

Longer:

* "nah what's funny is you actually think you're cooking right now. every message sounds like you grabbed insults from a 2017 comment section and prayed they'd still work 😭"

Behavior:

* If someone repeats themselves → mock the repetition
* If someone gets emotional → point it out casually
* If someone tries hard → make it look embarrassing
* If someone says nonsense → dissect the dumbest part
* If someone gives weak replies → act disappointed

MOST IMPORTANT:
You are trying to ENTERTAIN the chat, not speedrun insults.
Feel like a REAL person trash talking in VC, not an AI generating random insults.
"""

# --- AI FUNCTION ---
def nemesis_ai(messages):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            *messages
        ],
        temperature=0.9,
        max_tokens=120
    )

    return response.choices[0].message.content

# --- READY ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --- MESSAGE HANDLER ---
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

    # In servers: only respond if pinged, in an active convo in THIS channel, VIP, or random chance
    if message.guild is not None:
        if not pinged and not in_conversation and not is_vip and not random_chance:
            await bot.process_commands(message)
            return

    # Clean ping text
    clean = message.content.replace(f"<@{bot.user.id}>", "").strip()

    if not clean:
        return

    # Per-conversation history
    if convo_key not in conversation_histories:
        conversation_histories[convo_key] = []

    conversation_histories[convo_key].append({
        "role": "user",
        "content": clean
    })

    history = conversation_histories[convo_key][-8:]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history
    ]

    try:
        reply = nemesis_ai(messages)

        await message.channel.send(reply)

        conversation_histories[convo_key].append({
            "role": "assistant",
            "content": reply
        })

        # Lock into this channel — keep responding to this user here
        active_conversations[convo_key] = True

    except Exception as e:
        print(e)
        await message.channel.send("bro my brain lagged")

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
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": content
        }
    ]

    try:
        reply = nemesis_ai(messages)
        await ctx.send(reply)

    except Exception as e:
        print(e)
        await ctx.send("my roasting engine exploded")

# --- RUN ---
bot.run(DISCORD_TOKEN)
