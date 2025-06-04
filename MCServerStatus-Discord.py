#!/usr/bin/python3

# uses mcsrvstat.us API
# possible alternative: mcstatus.io


import json, requests, emoji
from discord import Intents, Client, app_commands, Embed, errors as discord_errors, Interaction, Permissions
from datetime import datetime, timezone, timedelta, tzinfo
from asyncio import sleep


_intents = Intents.default()
__client = Client(intents=_intents)
__tree = app_commands.CommandTree(
    __client,
    allowed_contexts=app_commands.AppCommandContext(
        guild=True, dm_channel=False,
        private_channel=False
    )
)
__colors = {
    "online": 0x00ff00,
    "offline": 0xff0000
}


def config_load():
    with open("config.json", "r", encoding="utf-8") as _f:
        return json.loads(_f.read())

def config_save(data):
    with open("config.json", "w", encoding="utf-8") as _f:
        _f.write(json.dumps(data, indent='  '))


__config = config_load()


@__client.event
async def on_ready():
    print('Bot logged in as {0.user}.'.format(__client))
    await __tree.sync()
    await start_bot()


async def start_bot():
    while True:
        for _server in __config["guilds"]:
            if _server["enabled"]:
                await mc_server_status(_server)
        print("Sleeping for %i s" % __config["sleep_time"])
        await sleep(__config["sleep_time"])
        print("Wait complete.")


async def mc_server_status(server):
        _req = requests.get("https://api.mcsrvstat.us/3/%s" % server["server_address"])
        if _req.status_code != 200:
            print("Error contacting API for %s of Discord server %s : %s" % (server["server_address"], server["discord_server"], _req.status_code))
        else:
            _req_json = _req.json()
            print("Correctly contacted API for server %s" % server["server_address"])

            if server["ip_update"]["enabled"]:
                _embed = Embed(
                    title=_req_json["motd"]["clean"][0] if _req_json["online"] and server["use_motd_as_name"] else server["default_name"],
                    color=__colors["online"] if _req_json["online"] else __colors["offline"]
                )
                _embed.add_field(
                    name="Actual IP",
                    value="`%s:%s`" % (_req_json["ip"], _req_json["port"]) if _req_json["online"] else "`-.-.-.-:-----`"
                )
                if "embed_message_id" not in server["ip_update"] or server["ip_update"]["embed_message_id"] == -1:
                    try:
                        print("Creating and sending message.")
                        _channel = __client.get_channel(server["ip_update"]["channel_id"])
                        _embed_message = await _channel.send(embed=_embed)
                        server["ip_update"]["embed_message_id"] = _embed_message.id
                        print("Message created correctly.")
                    except:
                        print("Error: Could not send message embed to channel.")
                else:
                    try:
                        print("Getting old message with id %i" % server["ip_update"]["embed_message_id"])
                        _channel = __client.get_channel(server["ip_update"]["channel_id"])
                        _embed_message = await _channel.fetch_message(server["ip_update"]["embed_message_id"])
                        if server["ip_update"]["delete_and_recreate_message"]:
                            print("Deleting message.")
                            await _embed_message.delete()
                            print("Creating and sending message.")
                            _embed_message = await _channel.send(embed=_embed)
                            server["ip_update"]["embed_message_id"] = _embed_message.id
                            print("Message created correctly.")
                        else:
                            print("Editing the old message...")
                            await _embed_message.edit(embed=_embed)
                            print("Edited the old embed message correctly.")
                    except discord_errors.NotFound:
                        print("Could not find embed message to edit.")
                        server["ip_update"]["embed_message_id"] = -1
                    except discord_errors.Forbidden:
                        # You do not have the permissions required to get a message.
                        print("Error: Please, allow the bot to view ancient messages.")
                        server["ip_update"]["embed_message_id"] = -1


            _embed = Embed(
                title=_req_json["motd"]["clean"][0] if _req_json["online"] and server["use_motd_as_name"] else server["default_name"],
                color=__colors["online"] if _req_json["online"] else __colors["offline"]
            )

            if not _req_json["online"]:
                if server["channel_update"]["change_name"]:
                    _channel = __client.get_channel(server["channel_update"]["channel_id"])
                    if _channel.name is not server["channel_update"]["name_offline"]:
                        await _channel.edit(name=server["channel_update"]["name_offline"])
                _embed.add_field(
                    name="State: ",
                    value="%s OFFLINE" % emoji.emojize("<:Skeleton_Skull_web:1379540672473989232>"),
                    inline=False
                )
                print("Server %s offline. Created embed." % server["server_address"])

            else:
                if server["channel_update"]["change_name"]:
                    _channel = __client.get_channel(server["channel_update"]["channel_id"])
                    if _channel.name is not server["channel_update"]["name_online"]:
                        await _channel.edit(name=server["channel_update"]["name_online"])
                _server_data = {
                    "State": "%s ONLINE" % emoji.emojize("<:mc_heart:1379541442996998154>"),
                    "Motd": "%s %s" % (emoji.emojize("<:mc_note:1379541624107040848>"), _req_json["motd"]["clean"][0]),
                    "Version": "%s `%s`" % ("<:mc_grass:1379540907950477362>", _req_json["version"]),
                    "Heroes": "%s `%i / %i`" % ("<:mc_stevevillager:1379612567772856410>", _req_json["players"]["online"], _req_json["players"]["max"]),
                }
                if server["channel_update"]["show_player_list"] and _req_json["players"]["online"] > 0:
                    _server_data["Heroes"] += "\n* <:steve_cool:1379540820683657368> %s" % "\n* <:steve_cool:1379540820683657368> ".join([_player["name"] for _player in _req_json["players"]["list"]])
                if server["channel_update"]["show_ip"]:
                    _server_data["Actual IP"] = "%s `%s`" % (emoji.emojize(":desktop:"), _req_json["ip"])
                for _key in _server_data:
                    _embed.add_field(
                        name=_key,
                        value=_server_data[_key],
                        inline=False
                    )
                print("Server online. Created embed.")

            _embed.add_field(
                name="Last update",
                value="%s <t:%s:f> (<t:%s:R>)" % (emoji.emojize(":arrows_counterclockwise:"), int(datetime.now().timestamp()), int(datetime.now().timestamp()))
            )
            print("Added timestamp to embed.")

            if "embed_message_id" not in server["channel_update"] or server["channel_update"]["embed_message_id"] == -1:
                try:
                    print("Creating and sending message.")
                    _channel = __client.get_channel(server["channel_update"]["channel_id"])
                    _embed_message = await _channel.send(embed=_embed)
                    server["channel_update"]["embed_message_id"] = _embed_message.id
                    print("Message created correctly.")
                except:
                    print("Error: Could not send message embed to channel.")
            else:
                try:
                    print("Getting old message with id %i" % server["channel_update"]["embed_message_id"])
                    _channel = __client.get_channel(server["channel_update"]["channel_id"])
                    _embed_message = await _channel.fetch_message(server["channel_update"]["embed_message_id"])
                    print("Editing the old message...")
                    await _embed_message.edit(embed=_embed)
                    print("Edited the old embed message correctly.")
                except discord_errors.NotFound:
                    print("Could not find embed message to edit.")
                    server["channel_update"]["embed_message_id"] = -1
                except discord_errors.Forbidden:
                    # You do not have the permissions required to get a message.
                    print("Error: Please, allow the bot to view ancient messages.")
                    server["channel_update"]["embed_message_id"] = -1

            config_save(__config)


# ToDo: Check if bot has authorizations (send message, delete message, send embed in every configured channel)

async def link_server_to_guild(
        discord_server: int,
        server_address: str,
        channel_update_id: int,
        change_channel_name=False,
        channel_name_online="🟩-online",
        channel_name_offline="🟥-offline",
        show_player_list=True,
        show_ip=True,
        ip_update_channel=False,
        ip_update_channel_id=-1,
        ip_recreate_message=False,
        default_server_name="",
        use_motd_as_default_server_name=False
    ):
    _server = {
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
            "show_ip": show_ip
        },
        "ip_update": {
            "enabled": ip_update_channel,
            "channel_id": ip_update_channel_id,
            "delete_and_recreate_message": ip_recreate_message,
        }
    }
    for _present_server in __config["guilds"]:
        if discord_server == _present_server["guild_id"]:
            for _k in _server:
                if isinstance(_server[_k], dict):
                    for _j in _server[_k]:
                        _present_server[_k][_j] = _server[_k][_j]
                else:
                    _present_server[_k] = _server[_k]
            if "enabled" in _present_server and _present_server["enabled"]:
                _msg = "Server already active. Updated."
            else:
                _present_server["enabled"] = True
                _msg = "Linked!"
            config_save(__config)
            return _msg

    __config["guilds"].append(_server)
    config_save(__config)
    return "Linked!"


@__tree.command(name="unlink", description="Unlink this guild. Stop showing Minecraft server updates.")
@app_commands.rename(delete_embeds="delete_messages")
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
async def command_unlink(interaction:Interaction, delete_embeds:bool=True):
    _found = False
    for _server in __config["guilds"]:
        if _server["guild_id"] == interaction.guild_id:
            _server["enabled"] = False
            if delete_embeds:
                try:
                    _embed_message = await __client.get_channel(_server["channel_update"]["channel_id"]).fetch_message(_server["channel_update"]["embed_message_id"])
                    await _embed_message.delete()
                except discord_errors.NotFound:
                    print("Could not find embed message to delete.")
                _server["channel_update"]["embed_message_id"] = -1
                try:
                    _embed_message = await __client.get_channel(_server["ip_update"]["channel_id"]).fetch_message(_server["ip_update"]["embed_message_id"])
                    await _embed_message.delete()
                except discord_errors.NotFound:
                    print("Could not find embed message to delete.")
                _server["ip_update"]["embed_message_id"] = -1
            _found = True
            await interaction.response.send_message(content="Unlinked!", ephemeral=True)
            break
    if not _found:
        await interaction.response.send_message(content="Guild not found.", ephemeral=True)
    config_save(__config)


@__tree.command(name="link", description="Link this guild to a Minecraft server")
@app_commands.guild_only()
@app_commands.rename(
    server_address='minecraft_server_address',
    change_channel_name='change_status_channel_name',
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
    use_motd_as_default_server_name="[False]"
)
@app_commands.checks.has_permissions(administrator=True)
async def command_link_mc_server(
        interaction:Interaction,
        server_address:str,
        change_channel_name:bool=False,
        channel_name_online:str="🟩-online",
        channel_name_offline:str="🟥-offline",
        show_player_list:bool=True,
        show_ip:bool=True,
        ip_update_channel:str="",
        default_server_name:str="",
        use_motd_as_default_server_name:bool=False
    ):
    _answer = await link_server_to_guild(
        discord_server=interaction.guild_id,
        server_address=server_address,
        channel_update_id=interaction.channel_id,
        change_channel_name=change_channel_name,
        channel_name_online=channel_name_online.replace(' ', '-'),
        channel_name_offline=channel_name_offline.replace(' ', '-'),
        show_player_list=show_player_list,
        show_ip=show_ip,
        ip_update_channel=False if ip_update_channel == "" else True,
        ip_update_channel_id=-1 if not ip_update_channel else int(ip_update_channel),
        default_server_name=default_server_name,
        use_motd_as_default_server_name=use_motd_as_default_server_name,
    )
    await interaction.response.send_message(content=_answer, ephemeral=True)


__client.run(__config["discord_bot_token"])
