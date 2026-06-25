#!/usr/bin/python3
"""
mc_status_bot.py – Discord bot for Minecraft server status updates.

Changes vs previous version:
- aiohttp replaces blocking requests (non-blocking in async context)
- Structured logging replaces print()
- Permission-error jail system (count → threshold → notify admin → disable guild)
- /unlink no longer crashes when embed_message_id is missing or -1
- Fixed identity comparison (is not → !=) on channel names
- config_save() called once per loop cycle instead of per guild
- `enabled` key always initialised in link_server_to_guild()
- Bare except clauses replaced with typed exception handling
"""

import json
import logging
import asyncio
import aiohttp

from discord import Intents, Client, app_commands, Embed, errors as discord_errors, Interaction
from datetime import datetime
import emoji


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────────

JAIL_PERM_ERROR_THRESHOLD = 5   # consecutive Forbidden errors before jailing
MCSRVSTAT_API = "https://api.mcsrvstat.us/3/%s"


# ── Discord setup ─────────────────────────────────────────────────────────────

_intents = Intents.default()
__client = Client(intents=_intents)
__tree = app_commands.CommandTree(
    __client,
    allowed_contexts=app_commands.AppCommandContext(
        guild=True, dm_channel=False, private_channel=False
    )
)
__colors = {
    "online": 0x00FF00,
    "offline": 0xFF0000,
}


# ── Config helpers ────────────────────────────────────────────────────────────

def config_load() -> dict:
    with open("config.json", "r", encoding="utf-8") as f:
        return json.loads(f.read())


def config_save(data: dict) -> None:
    with open("config.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent="  "))


__config = config_load()


# ── Jail helpers ──────────────────────────────────────────────────────────────

def _get_server_config(guild_id: int) -> dict | None:
    """Return the config entry for a guild, or None."""
    for s in __config["guilds"]:
        if s["guild_id"] == guild_id:
            return s
    return None


def _record_perm_error(server: dict) -> None:
    """Increment the permission-error counter for this guild config entry."""
    server.setdefault("perm_errors", 0)
    server["perm_errors"] += 1
    log.warning(
        "Permission error #%d in guild %d.",
        server["perm_errors"], server["guild_id"]
    )


async def _check_jail_threshold(server: dict) -> None:
    """
    If the error counter has reached the threshold, jail the guild and
    attempt to notify the admin via the three fallback strategies from
    cog_voice.py:
      1. DM the configured admin user
      2. Post in the last known update channel
      3. Rename the bot to ADMIN_NEEDED
    """
    count = server.get("perm_errors", 0)
    if count < JAIL_PERM_ERROR_THRESHOLD:
        return

    server["jailed"] = True
    log.error(
        "Guild %d jailed after %d permission errors.", server["guild_id"], count
    )

    jail_msg = (
        f"⚠️ **[MC Status Bot]** Le bot a rencontré **{count} erreurs de permissions** "
        f"sur le serveur Discord `{server['guild_id']}` et s'est mis en pause automatiquement.\n\n"
        f"Vérifiez les permissions du bot, puis utilisez `/unjail` pour le réactiver."
    )

    guild = __client.get_guild(server["guild_id"])
    if guild is None:
        return

    # 1. DM the admin user
    admin_uid = server.get("admin_user_id")
    if admin_uid:
        try:
            admin_user = await __client.fetch_user(admin_uid)
            await admin_user.send(jail_msg)
            log.info("Sent jail DM to admin user %d for guild %d.", admin_uid, guild.id)
            return
        except (discord_errors.Forbidden, discord_errors.HTTPException, discord_errors.NotFound):
            log.warning("Could not DM admin user %d for guild %d.", admin_uid, guild.id)

    # 2. Post in the last known update channel
    channel_id = server["channel_update"].get("channel_id")
    if channel_id:
        ch = __client.get_channel(channel_id)
        if ch:
            try:
                await ch.send(jail_msg)
                log.info("Sent jail notice to channel %d in guild %d.", channel_id, guild.id)
                return
            except (discord_errors.Forbidden, discord_errors.HTTPException):
                log.warning(
                    "Could not send jail notice to channel %d in guild %d.", channel_id, guild.id
                )

    # 3. Rename bot to ADMIN_NEEDED
    try:
        me = guild.me
        if me and me.nick != "ADMIN_NEEDED":
            await me.edit(nick="ADMIN_NEEDED")
            log.info("Renamed bot to ADMIN_NEEDED in guild %d.", guild.id)
    except (discord_errors.Forbidden, discord_errors.HTTPException):
        log.warning("Could not rename bot in guild %d.", guild.id)


# ── HTTP session ──────────────────────────────────────────────────────────────

_http_session: aiohttp.ClientSession | None = None


async def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session


# ── Discord events ────────────────────────────────────────────────────────────

@__client.event
async def on_ready():
    log.info("Bot logged in as %s.", __client.user)
    await __tree.sync()
    await start_bot()


async def start_bot():
    async with aiohttp.ClientSession() as session:
        while True:
            dirty = False
            for server in __config["guilds"]:
                if not server.get("enabled", False):
                    continue
                if server.get("jailed", False):
                    log.info("Skipping jailed guild %d.", server["guild_id"])
                    continue
                changed = await mc_server_status(server, session)
                if changed:
                    dirty = True
            if dirty:
                config_save(__config)
            log.info("Sleeping for %d s.", __config["sleep_time"])
            await asyncio.sleep(__config["sleep_time"])
            log.info("Wait complete.")


# ── Status update ─────────────────────────────────────────────────────────────

async def mc_server_status(server: dict, session: aiohttp.ClientSession) -> bool:
    """
    Fetch the MC server status and update the Discord embed.
    Returns True if config was modified (embed_message_id updated).
    """
    url = MCSRVSTAT_API % server["server_address"]
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                log.error(
                    "API error for %s (guild %d): HTTP %d",
                    server["server_address"], server["guild_id"], resp.status
                )
                return False
            req_json = await resp.json()
    except aiohttp.ClientError as e:
        log.error("HTTP request failed for %s: %s", server["server_address"], e)
        return False

    log.info("API response received for %s.", server["server_address"])
    dirty = False

    # ── IP update embed ───────────────────────────────────────────────────────
    if server["ip_update"]["enabled"]:
        dirty |= await _update_embed_ip(server, req_json)

    # ── Status embed ──────────────────────────────────────────────────────────
    dirty |= await _update_embed_status(server, req_json)

    return dirty


async def _send_or_edit_embed(
    server: dict,
    section: dict,
    embed: Embed,
    recreate: bool = False,
) -> bool:
    """
    Generic helper: send a new embed or edit the existing one.
    section is either server["channel_update"] or server["ip_update"].
    Returns True if the message id changed.
    """
    msg_id = section.get("embed_message_id", -1)
    channel = __client.get_channel(section["channel_id"])
    if channel is None:
        log.error("Channel %d not found for guild %d.", section["channel_id"], server["guild_id"])
        return False

    # No message yet → create
    if msg_id == -1:
        try:
            msg = await channel.send(embed=embed)
            section["embed_message_id"] = msg.id
            log.info("Created embed in channel %d.", channel.id)
            return True
        except discord_errors.Forbidden:
            log.error("Forbidden: cannot send to channel %d (guild %d).", channel.id, server["guild_id"])
            _record_perm_error(server)
            await _check_jail_threshold(server)
            return False
        except discord_errors.HTTPException as e:
            log.error("HTTPException sending to channel %d: %s", channel.id, e)
            return False

    # Existing message → edit or delete+recreate
    try:
        msg = await channel.fetch_message(msg_id)
        if recreate:
            await msg.delete()
            msg = await channel.send(embed=embed)
            section["embed_message_id"] = msg.id
            log.info("Recreated embed in channel %d.", channel.id)
            return True
        else:
            await msg.edit(embed=embed)
            log.info("Edited embed in channel %d.", channel.id)
            return False
    except discord_errors.NotFound:
        log.warning("Embed message %d not found in channel %d; will recreate.", msg_id, channel.id)
        section["embed_message_id"] = -1
        # Recurse once with no message id → will create
        return await _send_or_edit_embed(server, section, embed, recreate)
    except discord_errors.Forbidden:
        log.error("Forbidden: cannot edit/fetch in channel %d (guild %d).", channel.id, server["guild_id"])
        _record_perm_error(server)
        await _check_jail_threshold(server)
        return False
    except discord_errors.HTTPException as e:
        log.error("HTTPException editing channel %d: %s", channel.id, e)
        return False


async def _update_embed_ip(server: dict, req_json: dict) -> bool:
    embed = Embed(
        title=req_json["motd"]["clean"][0] if req_json["online"] and server["use_motd_as_name"] else server["default_name"],
        color=__colors["online"] if req_json["online"] else __colors["offline"],
    )
    embed.add_field(
        name="Actual IP",
        value="`%s:%s`" % (req_json["ip"], req_json["port"]) if req_json["online"] else "`-.-.-.-:-----`",
    )
    return await _send_or_edit_embed(
        server,
        server["ip_update"],
        embed,
        recreate=server["ip_update"].get("delete_and_recreate_message", False),
    )


async def _update_embed_status(server: dict, req_json: dict) -> bool:
    embed = Embed(
        title=req_json["motd"]["clean"][0] if req_json["online"] and server["use_motd_as_name"] else server["default_name"],
        color=__colors["online"] if req_json["online"] else __colors["offline"],
    )

    # Channel name update
    if server["channel_update"]["change_name"]:
        channel = __client.get_channel(server["channel_update"]["channel_id"])
        if channel:
            target_name = (
                server["channel_update"]["name_online"] if req_json["online"]
                else server["channel_update"]["name_offline"]
            )
            if channel.name != target_name:   # != instead of `is not`
                try:
                    await channel.edit(name=target_name)
                except discord_errors.Forbidden:
                    log.error(
                        "Forbidden: cannot rename channel %d (guild %d).", channel.id, server["guild_id"]
                    )
                    _record_perm_error(server)
                    await _check_jail_threshold(server)
                except discord_errors.HTTPException as e:
                    log.warning("HTTPException renaming channel %d: %s", channel.id, e)

    if not req_json["online"]:
        embed.add_field(
            name="State:",
            value="%s OFFLINE" % emoji.emojize("<:Skeleton_Skull_web:1379540672473989232>"),
            inline=False,
        )
        log.info("Server %s offline.", server["server_address"])
    else:
        server_data = {
            "State": "%s ONLINE" % emoji.emojize("<:mc_heart:1379541442996998154>"),
            "Motd": "%s %s" % (emoji.emojize("<:mc_note:1379541624107040848>"), req_json["motd"]["clean"][0]),
            "Version": "%s `%s`" % ("<:mc_grass:1379540907950477362>", req_json["version"]),
            "Heroes": "%s `%i / %i`" % (
                "<:mc_stevevillager:1379612567772856410>",
                req_json["players"]["online"],
                req_json["players"]["max"],
            ),
        }
        if server["channel_update"]["show_player_list"] and req_json["players"]["online"] > 0:
            if "list" in req_json["players"]:
                server_data["Heroes"] += "\n* <:steve_cool:1379540820683657368> %s" % (
                    "\n* <:steve_cool:1379540820683657368> ".join(
                        [p["name"] for p in req_json["players"]["list"]]
                    )
                )
        if server["channel_update"]["show_ip"]:
            server_data["Actual IP"] = "%s `%s`" % (
                emoji.emojize(":desktop:"), req_json["ip"]
            )
        for key, value in server_data.items():
            embed.add_field(name=key, value=value, inline=False)
        log.info("Server %s online.", server["server_address"])

    now_ts = int(datetime.now().timestamp())
    embed.add_field(
        name="Last update",
        value="%s <t:%s:f> (<t:%s:R>)" % (emoji.emojize(":arrows_counterclockwise:"), now_ts, now_ts),
    )

    return await _send_or_edit_embed(server, server["channel_update"], embed)


# ── link helper ───────────────────────────────────────────────────────────────

async def link_server_to_guild(
    discord_server: int,
    server_address: str,
    channel_update_id: int,
    change_channel_name: bool = False,
    channel_name_online: str = "🟩-online",
    channel_name_offline: str = "🟥-offline",
    show_player_list: bool = True,
    show_ip: bool = True,
    ip_update_channel: bool = False,
    ip_update_channel_id: int = -1,
    ip_recreate_message: bool = False,
    default_server_name: str = "",
    use_motd_as_default_server_name: bool = False,
    admin_user_id: int | None = None,
) -> str:
    new_entry = {
        "enabled": True,               # always initialised
        "jailed": False,
        "perm_errors": 0,
        "admin_user_id": admin_user_id,
        "default_name": default_server_name,
        "use_motd_as_name": use_motd_as_default_server_name,
        "guild_id": discord_server,
        "server_address": server_address,
        "channel_update": {
            "channel_id": channel_update_id,
            "change_name": change_channel_name,
            "name_online": channel_name_online,
            "name_offline": channel_name_offline,
            "show_player_list": show_player_list,
            "show_ip": show_ip,
            "embed_message_id": -1,
        },
        "ip_update": {
            "enabled": ip_update_channel,
            "channel_id": ip_update_channel_id,
            "delete_and_recreate_message": ip_recreate_message,
            "embed_message_id": -1,
        },
    }

    for present in __config["guilds"]:
        if discord_server == present["guild_id"]:
            # Merge: update each key, preserving existing embed_message_ids
            for k, v in new_entry.items():
                if isinstance(v, dict):
                    for j, w in v.items():
                        if j != "embed_message_id":   # don't reset an active message id
                            present[k][j] = w
                else:
                    present[k] = v
            present["enabled"] = True
            present["jailed"] = False
            present["perm_errors"] = 0
            config_save(__config)
            return "Updated and re-enabled!"

    __config["guilds"].append(new_entry)
    config_save(__config)
    return "Linked!"


# ── Slash commands ────────────────────────────────────────────────────────────

@__tree.command(name="unlink", description="Unlink this guild. Stop showing Minecraft server updates.")
@app_commands.rename(delete_embeds="delete_messages")
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
async def command_unlink(interaction: Interaction, delete_embeds: bool = True):
    found = False
    for server in __config["guilds"]:
        if server["guild_id"] != interaction.guild_id:
            continue

        server["enabled"] = False
        found = True

        if delete_embeds:
            await _delete_embed_if_exists(server, "channel_update")
            await _delete_embed_if_exists(server, "ip_update")

        break

    if found:
        config_save(__config)
        await interaction.response.send_message("Unlinked!", ephemeral=True)
    else:
        await interaction.response.send_message("Guild not found.", ephemeral=True)


async def _delete_embed_if_exists(server: dict, section_key: str) -> None:
    """
    Delete the embed message for a given section (channel_update or ip_update)
    only if a valid message id is stored. Silently skips missing messages.
    """
    section = server.get(section_key, {})
    msg_id = section.get("embed_message_id", -1)
    channel_id = section.get("channel_id", -1)

    if msg_id == -1 or channel_id == -1:
        return   # nothing to delete

    channel = __client.get_channel(channel_id)
    if channel is None:
        log.warning("Channel %d not found while trying to delete embed.", channel_id)
        section["embed_message_id"] = -1
        return

    try:
        msg = await channel.fetch_message(msg_id)
        await msg.delete()
        log.info("Deleted embed message %d in channel %d.", msg_id, channel_id)
    except discord_errors.NotFound:
        log.info("Embed message %d already gone.", msg_id)
    except discord_errors.Forbidden:
        log.warning("Forbidden: cannot delete message %d in channel %d.", msg_id, channel_id)
    finally:
        section["embed_message_id"] = -1


@__tree.command(name="unjail", description="Réactive le bot après résolution des problèmes de permissions.")
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
async def command_unjail(interaction: Interaction):
    server = _get_server_config(interaction.guild_id)
    if server is None:
        await interaction.response.send_message("Guild non configurée.", ephemeral=True)
        return

    if not server.get("jailed", False):
        await interaction.response.send_message("ℹ️ Le bot n'est pas en pause sur ce serveur.", ephemeral=True)
        return

    server["jailed"] = False
    server["perm_errors"] = 0

    # Reset ADMIN_NEEDED nickname if set
    guild = __client.get_guild(interaction.guild_id)
    if guild:
        try:
            me = guild.me
            if me and me.nick == "ADMIN_NEEDED":
                await me.edit(nick=None)
        except (discord_errors.Forbidden, discord_errors.HTTPException):
            pass

    config_save(__config)
    await interaction.response.send_message("✅ Bot réactivé. Compteur d'erreurs remis à zéro.", ephemeral=True)


@__tree.command(name="link", description="Link this guild to a Minecraft server")
@app_commands.guild_only()
@app_commands.rename(
    server_address="minecraft_server_address",
    change_channel_name="change_status_channel_name",
    channel_name_online="channel_name_when_online",
    channel_name_offline="channel_name_when_offline",
    show_player_list="show_online_players",
    show_ip="show_ip_in_status_channel",
    ip_update_channel="use_separate_channel_for_ip",
    default_server_name="server_name",
    use_motd_as_default_server_name="use_motd_as_server_name",
)
@app_commands.describe(
    server_address="Add port if not default (IP:port).",
    change_channel_name="[False]",
    channel_name_online="[🟩-online]",
    channel_name_offline="[🟥-offline]",
    show_player_list="[True]",
    show_ip="[True] Show IP in update channel.",
    ip_update_channel="Optional channel ID. Send IP in separate channel.",
    default_server_name="Leave blank if you want to use MOTD.",
    use_motd_as_default_server_name="[False]",
)
@app_commands.checks.has_permissions(administrator=True)
async def command_link_mc_server(
    interaction: Interaction,
    server_address: str,
    change_channel_name: bool = False,
    channel_name_online: str = "🟩-online",
    channel_name_offline: str = "🟥-offline",
    show_player_list: bool = True,
    show_ip: bool = True,
    ip_update_channel: str = "",
    default_server_name: str = "",
    use_motd_as_default_server_name: bool = False,
):
    answer = await link_server_to_guild(
        discord_server=interaction.guild_id,
        server_address=server_address,
        channel_update_id=interaction.channel_id,
        change_channel_name=change_channel_name,
        channel_name_online=channel_name_online.replace(" ", "-"),
        channel_name_offline=channel_name_offline.replace(" ", "-"),
        show_player_list=show_player_list,
        show_ip=show_ip,
        ip_update_channel=bool(ip_update_channel),
        ip_update_channel_id=-1 if not ip_update_channel else int(ip_update_channel),
        default_server_name=default_server_name,
        use_motd_as_default_server_name=use_motd_as_default_server_name,
        admin_user_id=interaction.user.id,   # record the linking admin for jail notifications
    )
    await interaction.response.send_message(answer, ephemeral=True)


# ── Entry point ───────────────────────────────────────────────────────────────

try:
    __client.run(__config["discord_bot_token"])
except KeyboardInterrupt:
    pass
except Exception as e:
    log.critical("Fatal error: %s", e)
    input("Press Enter to exit.")
