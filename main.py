import discord
from discord.ext import commands
import random
import re
import datetime

try:
    import pymorphy3
    MORPH = pymorphy3.MorphAnalyzer()
    HAS_MORPH = True
except ImportError:
    MORPH = None
    HAS_MORPH = False
    print("[!] pymorphy3 не установлен — работа без морфологии")


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ============================================================
# ВОПРОСИТЕЛЬНЫЕ СЛОВА
# ============================================================

QUESTION_WORDS = {
    "где":     {"tail": "в {channel}", "subject_pos": None},
    "куда":    {"tail": "в {channel}", "subject_pos": None},
    "откуда":  {"tail": "из {channel}", "subject_pos": None},
    "когда":   {"tail": "{time}",       "subject_pos": None},
    "почему":  {"tail": "потому что",   "subject_pos": None},
    "зачем":   {"tail": "просто так",   "subject_pos": None},
    "как":     {"tail": "никак",        "subject_pos": None},
    "сколько": {"tail": "42",           "subject_pos": None},
    "кто":     {"tail": "",             "subject_pos": "start"},
    "кого":    {"tail": "",             "subject_pos": "end"},
    "кому":    {"tail": "",             "subject_pos": "end"},
    "кем":     {"tail": "",             "subject_pos": "end"},
    "что":     {"tail": "",             "subject_pos": None},
    "чего":    {"tail": "",             "subject_pos": None},
    "чему":    {"tail": "",             "subject_pos": None},
    "чем":     {"tail": "",             "subject_pos": None},
    "чей":     {"tail": "",             "subject_pos": "end"},
    "чья":     {"tail": "",             "subject_pos": "end"},
    "чьё":     {"tail": "",             "subject_pos": "end"},
    "чье":     {"tail": "",             "subject_pos": "end"},
    "чьи":     {"tail": "",             "subject_pos": "end"},
}

TIMES = [
    "только что", "минуту назад", "час назад", "вчера", "позавчера",
    "утром", "днём", "вечером", "ночью",
    "на прошлой неделе", "в прошлом месяце",
    "давно", "недавно", "сейчас", "прямо сейчас", "сегодня",
]

INTRO_WORDS = {"а", "и", "ну", "да", "э", "ой", "вот", "так", "же"}

AUTHOR_SUBJECT = {"я", "мы"}
AUTHOR_OBJECT = {
    "меня", "мне", "мной", "мною",
    "нас", "нам", "нами",
}

BOT_PRONOUNS = {
    "ты", "тебя", "тебе", "тобой", "тобою",
    "вы", "вас", "вам", "вами",
}

DROP_PRONOUNS = {
    "он", "она", "оно", "они",
    "его", "её", "ее", "их",
    "ему", "ей", "им",
    "себя", "себе",
}

POSSESSIVE_MY = {
    "мой", "моя", "моё", "мое", "мои", "мою",
    "моего", "моей", "моих", "моему", "моим", "моими", "моём", "моем",
    "наш", "наша", "наше", "наши", "нашу",
    "нашего", "нашей", "наших", "нашему", "нашим", "нашими", "нашем",
}

POSSESSIVE_YOUR = {
    "твой", "твоя", "твоё", "твое", "твои", "твою",
    "твоего", "твоей", "твоих", "твоему", "твоим", "твоими", "твоём", "твоем",
    "ваш", "ваша", "ваше", "ваши", "вашу",
    "вашего", "вашей", "ваших", "вашему", "вашим", "вашими", "вашем",
}

MENTION_RE = re.compile(r"<@!?(\d+)>")


# ============================================================
# МОД-КОМАНДЫ
# ============================================================

MOD_COMMANDS = {
    "кик":    {"user_perm": "kick_members",     "bot_perm": "kick_members"},
    "бан":    {"user_perm": "ban_members",      "bot_perm": "ban_members"},
    "разбан": {"user_perm": "ban_members",      "bot_perm": "ban_members"},
    "мут":    {"user_perm": "moderate_members", "bot_perm": "moderate_members"},
    "анмут":  {"user_perm": "moderate_members", "bot_perm": "moderate_members"},
    "размут": {"user_perm": "moderate_members", "bot_perm": "moderate_members"},
    "варн":   {"user_perm": "manage_messages",  "bot_perm": "manage_messages"},
}

TIME_UNITS = {
    "сек": 1, "секунд": 1, "секунды": 1, "секунду": 1,
    "мин": 60, "минут": 60, "минуты": 60, "минуту": 60,
    "час": 3600, "часа": 3600, "часов": 3600,
    "день": 86400, "дня": 86400, "дней": 86400, "суток": 86400,
}

DEFAULT_REASON = "нарушение правил сервера"


# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def clean_word(w: str) -> str:
    """
    Обрезает слово на первом знаке препинания.
    'меня?е' → 'меня'
    'трахал?' → 'трахал'
    'меня' → 'меня'
    """
    result = []
    for ch in w:
        if ch.isalpha() or ch.isdigit() or ch == "-":
            result.append(ch)
        else:
            break  # стоп на первом не-буквенном символе
    return "".join(result).lower()


async def get_random_member(guild, exclude=None, also_exclude=None):
    if not guild.chunked:
        try:
            async for _ in guild.fetch_members(limit=None):
                pass
        except (discord.HTTPException, discord.Forbidden) as e:
            print(f"[!] Не удалось догрузить участников {guild.name}: {e}")

    members = [
        m for m in guild.members
        if not m.bot
        and m != exclude
        and (also_exclude is None or m.mention != also_exclude)
    ]
    return random.choice(members) if members else None


def get_random_channel(guild, exclude=None):
    channels = [
        c for c in guild.text_channels
        if c != exclude and c.permissions_for(guild.me).send_messages
    ]
    return random.choice(channels) if channels else None


def normalize_word(word: str) -> str:
    if not HAS_MORPH or not word:
        return word
    clean = re.sub(r"[^\w\-]", "", word)
    if not clean:
        return word
    parsed = MORPH.parse(clean)
    if not parsed:
        return word
    return parsed[0].normal_form


def has_perm(member: discord.Member, perm_name: str) -> bool:
    perms = member.guild_permissions
    if perms.administrator:
        return True
    return getattr(perms, perm_name, False)


def bot_has_perm(guild: discord.Guild, perm_name: str) -> bool:
    perms = guild.me.guild_permissions
    if perms.administrator:
        return True
    return getattr(perms, perm_name, False)


def parse_duration(text: str):
    text = text.lower().strip()
    m = re.match(r"(\d+)\s*([а-яё]+)", text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit in TIME_UNITS:
        return n * TIME_UNITS[unit]
    return None


def fmt_duration(seconds: int) -> str:
    mins = seconds // 60
    if mins < 60:
        return f"{mins} мин"
    if mins < 1440:
        return f"{mins // 60} ч {mins % 60} мин"
    return f"{mins // 1440} д"


# ============================================================
# МОД-КОМАНДЫ
# ============================================================

async def handle_mod_command(content: str, message: discord.Message):
    content_lower = content.lower().strip()

    for cmd in sorted(MOD_COMMANDS.keys(), key=len, reverse=True):
        if not content_lower.startswith(cmd):
            continue

        user_perm = MOD_COMMANDS[cmd]["user_perm"]
        if not has_perm(message.author, user_perm):
            return (f"{message.author.mention} не дорос. Эта команда только для админов 👮", False)

        bot_perm = MOD_COMMANDS[cmd]["bot_perm"]
        if not bot_has_perm(message.guild, bot_perm):
            return (f"{message.author.mention} у меня нет прав на `{cmd}`. "
                    f"Выдай мне `{bot_perm}` и подними роль выше цели.", False)

        rest = content[len(cmd):].strip()

        if cmd == "разбан":
            id_match = re.search(r"\d{15,}", rest)
            if not id_match:
                return (f"{message.author.mention} укажи ID: "
                        f"`@{bot.user.display_name} разбан 123456789012345678 [причина]`", False)
            user_id = int(id_match.group())
            reason = MENTION_RE.sub("", rest).replace(str(user_id), "").strip() or DEFAULT_REASON
            try:
                await message.guild.unban(discord.Object(id=user_id), reason=reason)
                return (f"🔓 <@{user_id}> разбанен. Причина: {reason}", True)
            except discord.NotFound:
                return (f"{message.author.mention} такой юзер не в бане.", False)
            except discord.Forbidden:
                return (f"{message.author.mention} нет прав на разбан.", False)

        target = None
        for m in message.mentions:
            if m.id != bot.user.id:
                target = m
                break

        if target is None:
            return (f"{message.author.mention} укажи цель: "
                    f"`@{bot.user.display_name} {cmd} @юзер [причина]`", False)

        reason = MENTION_RE.sub("", rest).strip()
        reason = re.sub(r"\s+", " ", reason).strip() or DEFAULT_REASON

        if cmd in ("кик", "бан", "мут", "анмут", "размут"):
            if target.top_role >= message.guild.me.top_role:
                return (f"{message.author.mention} не могу тронуть {target.mention}: "
                        f"его роль выше или равна моей.", False)
            if target.top_role >= message.author.top_role and target != message.author:
                return (f"{message.author.mention} не могу тронуть {target.mention}: "
                        f"его роль выше или равна твоей.", False)

        try:
            if cmd == "кик":
                await target.kick(reason=reason)
                return (f"👢 {target.mention} кикнут. Причина: {reason}", True)

            elif cmd == "бан":
                await target.ban(reason=reason, delete_message_days=1)
                return (f"🔨 {target.mention} забанен. Причина: {reason}", True)

            elif cmd == "мут":
                cleaned = MENTION_RE.sub("", rest).strip()
                dur_match = re.search(
                    r"(\d+)\s*(сек|секунд|секунды|секунду|мин|минут|минуты|минуту|"
                    r"час|часа|часов|день|дня|дней|суток)",
                    cleaned, re.IGNORECASE
                )
                duration_sec = 600
                if dur_match:
                    parsed_dur = parse_duration(dur_match.group(0))
                    if parsed_dur:
                        duration_sec = parsed_dur
                        cleaned = cleaned.replace(dur_match.group(0), "").strip()
                        reason = cleaned or DEFAULT_REASON

                duration_sec = min(duration_sec, 28 * 86400)
                until = discord.utils.utcnow() + datetime.timedelta(seconds=duration_sec)
                await target.timeout(until, reason=reason)
                return (f"🤐 {target.mention} в муте на {fmt_duration(duration_sec)}. "
                        f"Причина: {reason}", True)

            elif cmd in ("анмут", "размут"):
                await target.timeout(None, reason=reason)
                return (f"🔊 {target.mention} размучен.", True)

            elif cmd == "варн":
                return (f"⚠️ {target.mention} получил предупреждение. Причина: {reason}", True)

        except discord.Forbidden:
            return (f"{message.author.mention} нет прав для `{cmd}` над {target.mention}.", False)
        except discord.HTTPException as e:
            return (f"{message.author.mention} ошибка Discord: {e}", False)

    return (None, False)


# ============================================================
# РАЗБОР ВОПРОСА
# ============================================================

async def parse_message(content: str, message: discord.Message):
    mentioned_other = [m for m in message.mentions if m.id != bot.user.id]

    raw = content
    raw = raw.replace(f"<@{bot.user.id}>", " ")
    raw = raw.replace(f"<@!{bot.user.id}>", " ")
    raw = MENTION_RE.sub(" ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    words = raw.split()
    if not words:
        return None

    qword = None
    qword_index = -1

    for i, w in enumerate(words[:4]):
        clean = clean_word(w)
        if clean in INTRO_WORDS:
            continue
        if clean in QUESTION_WORDS:
            qword = clean
            qword_index = i
            break
        else:
            break

    if qword is None:
        return None

    words = words[qword_index + 1:]

    cleaned_words = []
    pending_marker = None
    has_author_subject = False
    has_author_object = False

    for w in words:
        w_lower = clean_word(w)
        if not w_lower:
            continue

        if pending_marker:
            cleaned_words.append(w_lower)
            cleaned_words.append(pending_marker)
            pending_marker = None
            continue

        if w_lower in AUTHOR_SUBJECT:
            has_author_subject = True
            continue
        if w_lower in AUTHOR_OBJECT:
            has_author_object = True
            continue
        if w_lower in BOT_PRONOUNS:
            continue
        if w_lower in DROP_PRONOUNS:
            continue
        if w_lower in POSSESSIVE_MY:
            pending_marker = "__MY__"
            continue
        if w_lower in POSSESSIVE_YOUR:
            pending_marker = "__BOT__"
            continue

        w_norm = normalize_word(w_lower)

        if w_norm in AUTHOR_OBJECT:
            has_author_object = True
            continue
        if w_norm in AUTHOR_SUBJECT:
            has_author_subject = True
            continue

        if w_norm in BOT_PRONOUNS:
            continue
        if w_norm in DROP_PRONOUNS:
            continue
        if w_norm in POSSESSIVE_MY:
            pending_marker = "__MY__"
            continue
        if w_norm in POSSESSIVE_YOUR:
            pending_marker = "__BOT__"
            continue

        cleaned_words.append(w_lower)

    if pending_marker:
        cleaned_words.append(pending_marker)

    subject_pos = QUESTION_WORDS[qword].get("subject_pos")

    start_mention = None
    end_mention = None

    if subject_pos == "start":
        if has_author_subject:
            start_mention = message.author.mention
        elif mentioned_other:
            start_mention = mentioned_other[0].mention
        else:
            target = await get_random_member(message.guild, exclude=message.author)
            start_mention = target.mention if target else message.author.mention

        if has_author_object:
            end_mention = message.author.mention

    elif subject_pos == "end":
        if has_author_subject:
            start_mention = message.author.mention
        elif mentioned_other:
            start_mention = mentioned_other[0].mention
        else:
            start_mention = message.author.mention

    else:
        if has_author_subject:
            start_mention = message.author.mention
            if mentioned_other:
                end_mention = mentioned_other[0].mention
        elif mentioned_other:
            start_mention = mentioned_other[0].mention
        else:
            start_mention = message.author.mention

    return {
        "qword": qword,
        "words": cleaned_words,
        "start_mention": start_mention,
        "end_mention": end_mention,
        "subject_pos": subject_pos,
    }


async def build_response(parsed, message):
    guild = message.guild

    random_channel = get_random_channel(guild, exclude=message.channel)
    channel_mention = random_channel.mention if random_channel else message.channel.mention

    words_out = []
    for w in parsed["words"]:
        if w == "__MY__":
            words_out.append(message.author.mention)
        elif w == "__BOT__":
            words_out.append(bot.user.mention)
        else:
            words_out.append(w)

    phrase = " ".join(words_out)

    tail_template = QUESTION_WORDS[parsed["qword"]]["tail"]
    if "{channel}" in tail_template:
        tail = tail_template.format(channel=channel_mention)
    elif "{time}" in tail_template:
        tail = random.choice(TIMES)
    else:
        tail = tail_template

    parts = [parsed["start_mention"]]
    if phrase:
        parts.append(phrase)
    if tail:
        parts.append(tail)

    if parsed["end_mention"]:
        parts.append(parsed["end_mention"])
    elif parsed["subject_pos"] == "end":
        end_target = await get_random_member(
            guild,
            exclude=message.author,
            also_exclude=parsed["start_mention"],
        )
        if end_target:
            parts.append(end_target.mention)

    return " ".join(parts)


# ============================================================
# СОБЫТИЯ
# ============================================================

@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен!")
    print(f"Морфология: {'включена' if HAS_MORPH else 'выключена (нет pymorphy3)'}")
    for guild in bot.guilds:
        try:
            async for _ in guild.fetch_members(limit=None):
                pass
            print(f"Загружено {len(guild.members)} участников для {guild.name}")
        except Exception as e:
            print(f"Не удалось загрузить участников {guild.name}: {e}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    bot_pinged = (
        f"<@{bot.user.id}>" in message.content
        or f"<@!{bot.user.id}>" in message.content
    )

    if bot_pinged:
        content = message.content
        content = content.replace(f"<@{bot.user.id}>", "")
        content = content.replace(f"<@!{bot.user.id}>", "")
        content = re.sub(r"\s+", " ", content).strip()

        if not content:
            await message.reply(
                f"{message.author.mention}, ты что-то хотел?",
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=True
                )
            )
            return

        mod_response, _ = await handle_mod_command(content, message)
        if mod_response:
            await message.reply(
                mod_response,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=True
                )
            )
            return

        parsed = await parse_message(content, message)
        if not parsed:
            return  # не распознали — молчим
        if not parsed["words"] and not parsed["start_mention"]:
            return

        response = await build_response(parsed, message)

        await message.reply(
            response,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=True
            )
        )

    await bot.process_commands(message)

bot.run("MTU1MTE5ODU0MzgxNjE3MTU1MA.GNTCwr.nPfl__TMl4RGhxuPpSQtr41552OrAKS4iYtRPU")