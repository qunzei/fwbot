import os
import asyncio
from typing import Iterable, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# ====== CONFIG ======
KEEP_PINNED = True  # set False to also delete pinned in video-links

# Titles + thumbnails
SPECIAL_CLEAR_CHANNEL_IDS = {
    1332150195105955911,  # titles (set 1)
    1377507720889892914,  # titles (set 2)
    1332149681425350756,  # thumbnails (set 1)
    1377507782793629696,  # thumbnails (set 2)
}

# Video links for week 1 (channels 1–7)
WEEK1_VIDEO_LINK_CHANNELS = [
    1377480864170119188,
    1377480886626553957,
    1377480899989475338,
    1377480911230074901,
    1377480919778197644,
    1377480928603148359,
    1377480942678966324,
]

# Video links for week 2 (channels 1–7)
WEEK2_VIDEO_LINK_CHANNELS = [
    1377507911525470318,
    1377507925328920649,
    1377507936430985276,
    1377507948321964053,
    1377507960187654174,
    1377507973697638501,
    1377507989149454346,
]

WEEK_CHANNELS = {"1": set(WEEK1_VIDEO_LINK_CHANNELS), "2": set(WEEK2_VIDEO_LINK_CHANNELS)}
# =====================================

load_dotenv()
TOKEN = os.getenv("MTQxMTUxNTk2MzQ5MjUzNjM4MQ.G9hFY0.DtAB3IVvqkK_8SBNkwnoRPjdKvOsoSlkTNFg10")
if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN in .env")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- helpers ----------
async def strip_checkmark_from_channel_name(ch: discord.TextChannel):
    try:
        if "✅" in ch.name:
            new_name = ch.name.replace("✅", "").strip("-_ ").replace(" ", "-").lower()
            if new_name and new_name != ch.name:
                await ch.edit(name=new_name, reason="Remove checkmark")
    except (discord.Forbidden, discord.HTTPException):
        pass


async def add_checkmark_to_channel_name(ch: discord.TextChannel):
    try:
        if "✅" not in ch.name:
            base = ch.name.rstrip("-_ ")
            new_name = f"{base}-✅".replace(" ", "-").lower()
            if new_name != ch.name:
                await ch.edit(name=new_name, reason="Add checkmark")
    except (discord.Forbidden, discord.HTTPException):
        pass


async def purge_channel(ch: discord.TextChannel, keep_pinned: bool):
    def _filter(msg: discord.Message) -> bool:
        return False if (keep_pinned and msg.pinned) else True

    try:
        await ch.purge(limit=None, check=_filter, bulk=True, reason="Weekly reset")
    except (discord.Forbidden, discord.HTTPException):
        pass

    try:
        async for msg in ch.history(limit=None, oldest_first=False):
            if keep_pinned and msg.pinned:
                continue
            try:
                await msg.delete()
                await asyncio.sleep(0.25)
            except discord.HTTPException:
                continue
    except discord.Forbidden:
        return


async def resolve_channels(guild: discord.Guild, ids: Iterable[int]) -> list[discord.TextChannel]:
    out: list[discord.TextChannel] = []
    for cid in ids:
        ch = guild.get_channel(cid)
        if isinstance(ch, discord.TextChannel):
            out.append(ch)
    return out


async def reset_specific(guild: discord.Guild, which: Optional[str]):
    # Clear titles/thumbnails
    for ch in await resolve_channels(guild, SPECIAL_CLEAR_CHANNEL_IDS):
        await purge_channel(ch, keep_pinned=False)

    # Which week to clear
    if which in ("1", "2"):
        to_clear_ids = set(WEEK_CHANNELS[which])
    else:
        to_clear_ids = set().union(*WEEK_CHANNELS.values())

    # Purge + strip ✅
    for ch in await resolve_channels(guild, to_clear_ids):
        await strip_checkmark_from_channel_name(ch)
        await purge_channel(ch, keep_pinned=KEEP_PINNED)


# ---------- slash commands ----------
@bot.tree.command(name="reset", description="Reset week 1, 2, or all (clears titles/thumbnails + video-links, removes ✅).")
@app_commands.describe(week="Choose 1, 2, or all")
@app_commands.choices(week=[
    app_commands.Choice(name="1", value="1"),
    app_commands.Choice(name="2", value="2"),
    app_commands.Choice(name="all", value="all"),
])
@app_commands.checks.has_permissions(manage_guild=True)
async def reset_week(interaction: discord.Interaction, week: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True, thinking=True)
    which = None if week.value == "all" else week.value
    await reset_specific(interaction.guild, which)
    await interaction.followup.send(f"✅ Reset complete for week: {week.value}.", ephemeral=True)


@bot.tree.command(name="strip_checks_here", description="Remove ✅ from this channel only.")
@app_commands.checks.has_permissions(manage_channels=True)
async def strip_checks_here(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if isinstance(interaction.channel, discord.TextChannel):
        await strip_checkmark_from_channel_name(interaction.channel)
        await interaction.followup.send("✅ Removed checkmark from this channel.", ephemeral=True)
    else:
        await interaction.followup.send("Not a text channel.", ephemeral=True)


@bot.tree.command(name="done", description="Add a ✅ to this channel only.")
@app_commands.checks.has_permissions(manage_channels=True)
async def mark_done_here(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if isinstance(interaction.channel, discord.TextChannel):
        await add_checkmark_to_channel_name(interaction.channel)
        await interaction.followup.send("✅ Added checkmark to this channel.", ephemeral=True)
    else:
        await interaction.followup.send("Not a text channel.", ephemeral=True)


# ---------- ready ----------
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Command sync failed:", e)
    print(f"Logged in as {bot.user} ({bot.user.id})")


if __name__ == "__main__":
    bot.run(TOKEN)
