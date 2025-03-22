import discord
from discord.ext import commands
import asyncio
import re
import time
import os
from datetime import timedelta
from keep_alive import keep_alive

# Bot settings
TOKEN = os.getenv('TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
keep_alive()
# Banned words list
banned_words = ["badword1", "badword2", "badword3"]
self_promo_keywords = ["discord.gg", "youtube.com", "twitch.tv"]

# Anti-Spam Settings
user_message_count = {}
spam_threshold = 5  # Messages within 10 seconds

# Kick Command
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Not specified"):
    await member.kick(reason=reason)
    await ctx.send(f"🚨 {member.mention} has been kicked! Reason: {reason}")

# Ban Command
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Not specified"):
    await member.ban(reason=reason)
    await ctx.send(f"🚨 {member.mention} has been banned! Reason: {reason}")

# Recover Timeout Command
@bot.command()
@commands.has_permissions(moderate_members=True)
async def recover(ctx, member: discord.Member):
    try:
        # Attempt to remove timeout using the correct method
        await member.edit(timed_out_until=None)
        await ctx.send(f"✅ {member.mention}'s timeout has been removed.")
    except Exception as e:
        await ctx.send(f"❌ Failed to remove timeout for {member.mention}: {str(e)}")


@bot.command()
@commands.has_permissions(mute_members=True)
async def mute(ctx, member: discord.Member, *, reason="Not specified"):
    await member.edit(mute=True)
    await ctx.send(f"🔇 {member.mention} has been muted! Reason: {reason}")

@bot.command()
@commands.has_permissions(mute_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(mute=False)
    await ctx.send(f"🔊 {member.mention} has been unmuted.")

warnings = {}

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="Not specified"):
    if member not in warnings:
        warnings[member] = 0
    warnings[member] += 1
    await ctx.send(f"⚠️ {member.mention} has been warned! Reason: {reason}. Total warnings: {warnings[member]}")


@bot.command()
async def userinfo(ctx, member: discord.Member):
    embed = discord.Embed(title=f"User Info: {member.name}", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    await ctx.send(embed=embed)


join_times = {}
@bot.event
async def on_member_join(member):
    now = time.time()
    # Check the number of joins within a short time period
    recent_joins = [t for t in join_times.values() if now - t < 10]
    
    # If there are more than 5 recent joins within 10 seconds, treat it as a raid
    if len(recent_joins) > 5:
        await member.guild.ban(member, reason="Raid detected")
        await member.guild.text_channels[0].send(f"🚨 RAID ALERT! {member.name} has been banned for participating in a raid attempt!")
    else:
        join_times[member.id] = now

 # Verification process: User must react to a message to get verified
@bot.command()
async def verify(ctx):
    # Send a verification message
    verification_message = await ctx.send("Please react with ✅ to get verified!")

    # Add the reaction required
    await verification_message.add_reaction("✅")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✅'

    try:
        # Wait for the user to react
        await bot.wait_for('reaction_add', timeout=60.0, check=check)
        await ctx.send("✅ You are now verified!")
    except asyncio.TimeoutError:
        await ctx.send("❌ You took too long to verify!")
       
cooldowns = {}
@bot.command()
async def restricted_command(ctx):
    user_id = ctx.author.id
    current_time = time.time()

    if user_id in cooldowns and current_time - cooldowns[user_id] < 5:
        await ctx.send(f"❌ {ctx.author.mention}, you're doing that too fast! Please wait before trying again.")
    else:
        cooldowns[user_id] = current_time
        await ctx.send("✅ Command executed successfully!")

@bot.event
async def on_message(message):
    # Check for suspicious behavior
    if message.author.bot:
        return

    # If the user has been inactive or has unusual activity
    if message.author.joined_at and (time.time() - message.author.joined_at.timestamp() < 86400):
        # Send an alert if the user has just joined and is sending lots of messages
        if message.author.id not in user_message_count:
            user_message_count[message.author.id] = []

        user_message_count[message.author.id].append(message.created_at.timestamp())

        if len(user_message_count[message.author.id]) > 10:  # Threshold: more than 10 messages in the first day
            # Alert admins
            admin_channel = discord.utils.get(message.guild.text_channels, name="admin-alerts")
            if admin_channel:
                await admin_channel.send(f"🚨 Suspicious Activity Detected! {message.author.name} is sending messages excessively shortly after joining.")
            return

    await bot.process_commands(message)

   
        
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def setnick(ctx, member: discord.Member, nickname: str):
    await member.edit(nick=nickname)
    await ctx.send(f"✅ {member.mention}'s nickname has been changed to {nickname}.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def assignrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✅ {member.mention} has been assigned the role {role.name}.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"✅ {role.name} has been removed from {member.mention}.")

@bot.command()
async def serverinfo(ctx):
    embed = discord.Embed(title=f"Server Info: {ctx.guild.name}", color=discord.Color.green())
    embed.add_field(name="ID", value=ctx.guild.id)
    embed.add_field(name="Members", value=ctx.guild.member_count)
    embed.add_field(name="Created At", value=ctx.guild.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    await ctx.send(embed=embed)

# Auto Timeout for Bad Words and Self-Promotion
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    for word in banned_words:
        if word in message.content.lower():
            await message.delete()
            await message.author.timeout(timedelta(days=7))
            await message.channel.send(f"🚨 {message.author.mention} has been timed out for using bad words!")
            return
    
    for promo in self_promo_keywords:
        if promo in message.content.lower():
            await message.delete()
            await message.author.timeout(timedelta(days=7))
            await message.channel.send(f"🚨 {message.author.mention} has been timed out for self-promotion!")
            return
    
    # Anti-Spam Check
    user_id = message.author.id
    if user_id not in user_message_count:
        user_message_count[user_id] = []
    
    user_message_count[user_id].append(message.created_at.timestamp())
    
    if len(user_message_count[user_id]) > spam_threshold:
        user_message_count[user_id] = [t for t in user_message_count[user_id] if t > message.created_at.timestamp() - 10]
        if len(user_message_count[user_id]) >= spam_threshold:
            await message.author.timeout(timedelta(days=7))
            await message.channel.send(f"🚨 {message.author.mention} has been timed out for spamming!")
            return

    await bot.process_commands(message)

# Logging Actions
@bot.event
async def on_member_remove(member):
    log_channel = discord.utils.get(member.guild.channels, name="logs")
    if log_channel:
        await log_channel.send(f"🚨 {member.name} has left or was kicked/banned from the server.")

# Run Bot
bot.run(TOKEN)
