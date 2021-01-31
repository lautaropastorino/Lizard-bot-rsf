import asyncio
from discord import Embed, Colour
from discord.utils import escape_markdown # Regexing fun simplified
import json
import os
from pprint import pformat
import random
import re
import requests

# Local imports
from secret import api_key
from commands.utilities import (register, bold, get_chal_tour_id, get_users, is_channel, pings_b_gone, checkin, seeding, signup, read_db, read_stat, save_db, settings_exist)

# All @register decorators are a product of reviewing Yaksha
# See utilities.register for more information

@register('botrole')
@register('role')
async def botrole(command, msg, user, channel, *args, **kwargs):
    # Pull the role name from the guild's roles
    return "The bot role is {0}".format(bold(channel.guild.get_role(read_db('guild', 'botrole', kwargs['guild'])).name))

@register('bracket')
async def bracket(command, msg, user, channel, *args, **kwargs):
    return read_db('channel', 'bracket', channel.id)

@register('help-lizard')
@register('helpliz')
async def help_lizard(command, msg, user, channel, *args, **kwargs):
    help_commands = kwargs.get('help', False)

    split = msg.split(' ')
    cmd = ' '.join(split[0:2]) if len(split) > 1 else split[0]

    if not help_commands:
        return "For more information about the bot and its commands: <https://github.com/lizardman301/Lizard-bot-rsf>"
    elif not split[0]:
        return ('Allows you to get help on a command. '
                '\nThe available commands are ```%s```' % ', '.join(list(help_commands.keys())))
    elif cmd in help_commands.keys():
        return help_commands[cmd]
    else:
        raise Exception(bold("Help_Lizard") + ": Invalid command: " + bold(cmd) + ". Ensure you are using the full command name."
                '\nThe available commands are ```%s```' % ', '.join(list(help_commands.keys())))

@register('not-in-discord')
@register('nid')
async def not_in_discord(command, msg, user, channel, *args, **kwargs):
    return bold("Your Discord nickname must match your challonge. If it does *NOT*, you will show as *NOT IN DISCORD*")

@register('lizardman')
@register('ping')
@register('liz')
async def ping(command, msg, user, channel, *args, **kwargs):
    print("Pinged by {0}".format(user))
    return "Fuck you, Lizardman"

@register('pingtest')
@register('pt')
async def pingtest(command, msg, user, channel, *args, **kwargs):
    return "To initiate a ping test, both players go to <https://testmyspeed.onl/> and choose a common server between each players location. Send the results of both tests to the TO."

@register('prefix-lizard')
@register('prefliz')
async def prefix(command, msg, user, channel, *args, **kwargs):
    return "The prefix is: {0}".format(read_db('guild', 'prefix-lizard', kwargs['guild']))

@register('randomselect')
@register('random')
@register('rs')
async def randomselect(command, msg, user, channel, *args, **kwargs):
    game = msg.split(' ')[0].lower() if msg.split(' ')[0] else 'sfv'
    rs_info = json.loads(open(os.path.join(os.path.dirname(__file__), 'rs.json')).read())
    games = list(rs_info.copy().keys())

    if game in games:
        chars = rs_info.get(game, []).copy()[0:-1]
    else:
        raise Exception(bold("RandomSelect") + ": Invalid game: {0}. Valid games are: {1}".format(bold(game), bold(', '.join(games))))

    return "{0} Your randomly selected character is: {1}".format(user.mention, bold(random.choice(chars)))

@register('stats')
async def stats(command, msg, user, channel, *args, **kwargs):
    cmd = msg.split(' ')[0].lower() if msg.split(' ')[0] else ''
    func_map = kwargs['func_map'] if cmd else []
    if cmd and cmd not in func_map:
        raise Exception(bold("Stats") + ": Invalid Subcommand. " + await help_lizard('','','',''))
    stats = read_stat(cmd,func_map)

    embed = Embed(title="Stats!", colour=Colour(0x0fa1dc))
    embed.set_author(name="Lizard-BOT", url="https://github.com/lizardman301/Lizard-bot-rsf", icon_url="https://raw.githubusercontent.com/lizardman301/Lizard-bot-rsf/master/doc/assets/images/cmface.png")
    embed.set_footer(text="People use this bot? Wild.")
    for stat in stats:
        embed.add_field(name=stat, value=stats[stat])

    try:
        await channel.send(embed=embed)
    except:
        raise Exception(bold("Stats") + ": Error sending embed to chat. Give Lizard-BOT the permission: " + bold("Embed Links"))

    return ''

@register('status')
async def status(command, msg, user, channel, *args, **kwargs):
    currentRound = read_db('channel', 'round', channel.id)
    if currentRound:
        # Read the status message for a channel and make it bold
        # Currently the message must have {0} so it can fill in the current round
        return bold(read_db('channel', 'status', channel.id).format(currentRound))
    return bold("Tournament has not begun. Please wait for the TOs to start Round 1!")

@register('stream')
async def stream(command, msg, user, channel, *args, **kwargs):
    return read_db('channel', 'stream', channel.id)

@register('tos')
async def TOs(command, msg, user, channel, *args, **kwargs):
    tos = read_db('channel', 'tos', channel.id)
    # If we get a value back, return TOs
    if tos:
        return tos
    return "There are no TOs associated with this channel."

# Admin Commands

@register('challonge')
@register('chal')
async def challonge(command, msg, user, channel, *args, **kwargs):
    async with channel.typing():
        base_url = "https://api.challonge.com/v1/tournaments/" # Base url to access Challonge's API
        subcommand = msg.split(' ')[0].lower() # The function trying to be accomplished

        if not subcommand:
                raise Exception(bold("Challonge") + ": Lack of arguments. " + await help_lizard('','','',''))

        try:
            if msg.split(' ')[1].isdigit():
                raise Exception("Bracket link is only digits.")
            tour_url = msg.split(' ')[1] # Bracket to pull from
        except:
            tour_url = get_chal_tour_id(read_db('channel', 'bracket', channel.id)) # no bracket provided, give it one from DB
            if not tour_url: # no bracket found still, return so we dont have issues
                raise Exception(bold("Challonge") + ": Bracket link is missing. Try setting the bracket command or including it in the command")

        subdomain = read_db('guild', 'challonge', kwargs['guild']) # Server's subdomain with Challonge

        # Properly add the subdomain to the bracket url
        if subdomain:
            tour_url = subdomain + '-' + tour_url

        # Get the participants for the tournament
        parts_get = requests.get(base_url + tour_url + "/participants.json", params={'api_key':api_key})
        if '200' in str(parts_get.status_code):
            parts = parts_get.json() # Convert response from json to Python Dictionary

            # If Checkin
            if subcommand == 'checkin':
                not_checked_in_parts, not_discord_parts = checkin(parts, get_users(kwargs['full_msg']))

                # Message showing who is not checked in and who is not in the Discord
                return_msg = "**NOT CHECKED IN:** {0}\n**NOT IN DISCORD:** {1}\n".format(', '.join(not_checked_in_parts), ', '.join(not_discord_parts)) + await not_in_discord(0,0,0,0)

            # If Seeding
            elif subcommand == 'seeding':
                # If msg has 3 params left 3rd one must be seed number
                # Else, seed whole bracket
                seed_num = int(msg.split(' ')[-1]) if msg.split(' ')[-1].isdigit() else 0

                # Get Google Sheets ID
                sheet_id = read_db('channel', 'seeding', channel.id)

                # If seeding hasn't been set, inform user
                if not sheet_id:
                    raise Exception(bold("Challonge") + ": There is no seeding sheet for this channel. Please view <https://github.com/lizardman301/Lizard-bot-rsf/blob/master/doc/seeding_with_sheets.md> for a walkthrough")

                seeds = seeding(sheet_id, parts, base_url + '/' + tour_url, seed_num)

                # Seeding takes place in different method
                await channel.send("**SEEDING:**\n {0}".format(',\n'.join(escape_markdown(pformat(seeds))[1:-1].split(', '))))

                # Final message that seeding is complete
                return_msg = bold("SEEDING IS NOW COMPLETE!\nPLEASE REFRESH YOUR BRACKETS\nWAIT FOR THE ROUND 1 ANNOUNCEMENT TO START PLAYING")

            elif subcommand == 'signup':
                chal_user = msg.split(' ')[2]
                chal_nick = msg.split(' ')[3] if len(msg.split(' ')) > 3 else ''

                signup(base_url + '/' + tour_url, chal_user, chal_nick)

                #print(parts_get.json())
                return_msg = 'Hi'
            # Bad command catching
            else:
                raise Exception(bold("Challonge") + ": Invalid Challonge subcommand. " + await help_lizard('','','',''))

            return return_msg # Return the final message
        elif '404' in str(parts_get.status_code):
            raise Exception(bold("Challonge") + ": Lizard-BOT can not find tournament: " + tour_url)
        else:
            print(parts_get.text)
            raise Exception(bold("Challonge") + ": Unknown Challonge error for " + tour_url)

@register('coin-flip')
@register('flip')
@register('cf')
async def coin_flip(command, msg, user, channel, *args, **kwargs):
    flip = "The coin landed on: {0}"
    # Flip a coin
    if int(round(random.random()*10*2)) % 2 == 0:
        return flip.format(bold("Heads"))
    return flip.format(bold("Tails"))

@register('edit')
async def edit(command, msg, user, channel, *args, **kwargs):
    params = msg.split(' ')
    full_msg = kwargs['full_msg'] # Allows us to access the role_mentions
    command_channels = {} # Stores channels to iterate over

    # Check for multi-channel changes at message start
    if full_msg.channel_mentions:
        for param in params:
            if is_channel(param):
                for chnl in full_msg.channel_mentions:
                    if chnl.id == is_channel(param) and 'text' in chnl.type:
                        command_channels.update({chnl.id: chnl.mention}) # Save channel for later
            else:
                break
        for chnl in command_channels:
            params.remove(command_channels[chnl]) # Remove the channel from the params
            
    params[0] = params[0].lower() # Make sure the command we are editing is in lowercase
    editable_command = params[0] # The command we are editing
    if editable_command not in kwargs['edit_subs']:
        raise Exception(bold("Edit") + ": Invalid Subcommand. " + await help_lizard('','','',''))

    params.remove(editable_command) # Remove the command from the params
    # Rejoin the rest of the parameters with spaces
    db_message = ' '.join(params) # The message we send to the Database
    channel_message = ' '.join(params) # The message that gets sent

    # Grab just the BigInt part of bot_role
    if editable_command in ['botrole']:
        if not full_msg.role_mentions or len(full_msg.role_mentions) > 1:
            raise Exception(bold("Edit") + " : Too few/many role mentions for botrole. Try again with only one role mentioned")
        elif full_msg.role_mentions:
            db_message = str(full_msg.role_mentions[0].id)
            channel_message = full_msg.role_mentions[0].name
        # Allow @everyone to be a botrole
        elif not params:
            db_message = str(full_msg.guild.default_role.id)
            channel_message = full_msg.guild.default_role.name
    elif editable_command in ['tos'] and (not full_msg.mentions and params):
            raise Exception(bold("Edit") + ": Invalid user mention. Try @'ing somebody")
    # Remove the bot pinging TOs on the confirmation message
    elif editable_command in ['tos']:
        mentions = pings_b_gone(full_msg.mentions)
        db_message = ' '.join(mentions.values()) # Put mention values into the database
        channel_message = ' '.join(mentions.keys()) # Send usernames back to the channel
    elif editable_command in ['seeding']:
        reg = re.compile('[a-zA-Z0-9-_]+')
        if not reg.fullmatch(params[0]) or len(params[0]) > 80:
            raise Exception(bold("Edit") + ": Invalid Sheets spreadsheet ID. Please view <https://github.com/lizardman301/Lizard-bot-rsf/blob/master/doc/seeding_with_sheets.md> for a walkthrough")
    elif editable_command in ['prefix-lizard'] and len(params[0]) > 1:
        raise Exception(bold("Edit") + ": Lizard-BOT prefix must be a singular character.")
    elif editable_command in ['bracket','status','stream'] and len(db_message) > 1945:
        raise Exception(bold("Edit") + ": Message is too long to be stored. Shorten you statement to 1945 characters or less")

    # Check for guild settings, channel settings, or multi channel settings
    if editable_command in ['botrole', 'challonge','prefix-lizard']:
        save_db('guild', editable_command, db_message, kwargs['guild']) # Save the new message to the proper setting in a given guild
    elif command_channels:
        # For each channel, save the setting
        for chnl in command_channels: 
            # We have to double check that the channel is in the DB
            if settings_exist(kwargs['guild'], chnl):
                save_db('channel', editable_command, db_message, chnl) # Save the new message to the proper setting in a given channel
        return "All listed channels had the {0} updated to {1}".format(bold(editable_command), bold(channel_message))
    else:
        save_db('channel', editable_command, db_message, channel.id) # Save the new message to the proper setting in a given channel

    return "The new {0} is: {1}".format(bold(editable_command), bold(channel_message)) # Print the new message for a given setting

@register('refresh')
async def refresh(command, msg, user, channel, *args, **kwargs):
    return bold("REFRESH YOUR BRACKETS\nREFRESH YOUR BRACKETS\nREFRESH YOUR BRACKETS\nREFRESH YOUR BRACKETS")

@register('remind')
async def remind(command, msg, user, channel, *args, **kwargs):
    params = msg.split(' ')
    time = int(params[0]) #time is in minutes
    reason = ""
    #specific reason if provided
    if len(params) > 1:
        reason = " ".join(params[1:])

    if reason:
        formatted_msg = "OK! I will ping you in {0} minutes to remind you about \"{1}\"".format(time,reason)
    else:
        formatted_msg = "OK! I will ping you in {0} minutes to remind you about something.".format(time)

    # sends message back to confirm reminder
    await channel.send(formatted_msg)

    # wait message time
    await asyncio.sleep(60 * time)
    if reason:
        formatted_msg = bold("{0}: It has been {1} minutes, don't forget \"{2}\"!").format(user.mention,time,reason)
    else:
        formatted_msg = bold("{0}: It has been {1} minutes, you have been reminded!".format(user.mention,time))

    await channel.send(formatted_msg)

@register('reset')
async def reset(command, msg, user, channel, *args, **kwargs):
    save_db('channel', 'round', '', channel.id)
    return "Round has been reset."

@register('round')
async def round_lizard(command, msg, user, channel, *args, **kwargs):
    if len(msg) > 50:
        raise Exception(bold("Round_Lizard") + ": Custom round number must be less then 50 characters")
    save_db('channel', 'round', msg, channel.id)
    return await status('status', msg, user, channel)