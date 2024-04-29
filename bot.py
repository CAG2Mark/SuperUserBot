import asyncio
import logging
import disnake
from guilddata import GuildData

from disnake.ext import commands
import bcrypt
from datetime import datetime

from removequeue import RemoveQueue

def success_embed(message: str) -> disnake.Embed:
    return disnake.Embed(
        description=":white_check_mark: " + message,
        color=disnake.Colour.green()
    )

def error_embed(message: str) -> disnake.Embed:
    return disnake.Embed(
        description=":x: " + message,
        color=disnake.Colour.red()
    )

def warn_embed(message: str) -> disnake.Embed:
    return disnake.Embed(
        description=":warning: " + message,
        color=disnake.Colour.yellow()
    )

def hash_salt_password(password: bytes) -> str:
    salt = bcrypt.gensalt()
    pw_hash = bcrypt.hashpw(password, salt)
    return pw_hash.hex() # note: bcryprt lib stores the salt with the hash

class Bot:
    logger = logging.getLogger("superuserbot")

    def __init__(self, token, guild_data: GuildData, remove_queue: RemoveQueue) -> None:
        client = commands.InteractionBot()
        self.client = client
        self.data: GuildData = guild_data
        self.rq = remove_queue

        self.initialized = False
        
        @client.event
        async def on_ready():
            self.logger.info(f"Successfully logged in to Discord with username {client.user}")
            self.initialized = True 

        @client.slash_command(name='sudo', 
                              description='Gives you the sudo role for a certain period of time.', 
                              dm_permission=False)
        async def sudo_command(inter: disnake.ApplicationCommandInteraction,
                               password: str = commands.Param(default="", name="password", description="Your password. Leave empty if you do not have a password on this guild yet."),
                               duration: int = commands.Param(default=5, name="duration", description="The time you receive the administrator role for in minutes.", gt=1, lt=20)):
            pw_bytes = password.encode('utf-8')
            del password
            pw_hash = self.data.get_user_password_hashsalt(inter.guild_id, inter.user.id)

            if pw_hash:
                pw_hash_bytes = bytes.fromhex(self.data.get_user_password_hashsalt(inter.guild_id, inter.user.id))
            
            if not pw_hash or bcrypt.checkpw(pw_bytes, pw_hash_bytes):
                sudoer_role = self.data.get_guild_sudoer_role(inter.guild_id)
                has_sudoer_role = any([r.id == sudoer_role for r in inter.user.roles])

                if not has_sudoer_role:
                    await inter.response.send_message(embed=error_embed(f"<@{inter.user.id}> is not in the sudoers file. This incident will be reported."), ephemeral=True)
                    return

                sudo_role_id = self.data.get_guild_role(inter.guild_id)
                sudo_role = inter.guild.get_role(sudo_role_id)

                if not sudo_role:
                    await inter.response.send_message(embed=error_embed("Misconfigured sudo role. Please contact an administrator."), ephemeral=True)
                    return
                
                try:
                    await inter.user.add_roles(sudo_role)
                except disnake.errors.Forbidden:
                    await inter.response.send_message(embed=error_embed("I do not have permission to grant you the sudo role. Please contact an administrator."), ephemeral=True)
                    return;
                except disnake.errors.NotFound:
                    await inter.response.send_message(embed=error_embed("Could not find the sudo role. Please contact an administrator."), ephemeral=True)
                    return;
                except:
                    await inter.response.send_message(embed=error_embed("Unkown error when giving you the sudo role. Please contact an administrator."), ephemeral=True)
                    return;

                del_time = int(datetime.utcnow().timestamp()) + duration * 60
                self.rq.add(del_time, inter.user.id, inter.guild_id, sudo_role_id)

                await inter.response.send_message(embed=success_embed("You are now in sudo mode."), ephemeral=True)
            else:
                await inter.response.send_message(embed=error_embed("Incorrect password."), ephemeral=True, delete_after=4)

        @client.slash_command(name='set_password', 
                              description='Set your password on this guild. DO NOT use the same password elsewhere.', 
                              dm_permission=False)
        async def set_password_command(inter: disnake.ApplicationCommandInteraction,
                               password: str = commands.Param(default="", name="password", description="The password to set.", min_length=6, max_length=51)):
            pw = self.data.get_user_password_hashsalt(inter.guild_id, inter.user.id)
            sudo_role = self.data.get_guild_role(inter.guild_id)
            has_sudo_role = any([r.id == sudo_role for r in inter.user.roles])

            if pw and not has_sudo_role:
                await inter.response.send_message(embed=warn_embed("Please enter sudo mode using `/sudo` to change your password."), ephemeral=True)
                return
        
            if not password.strip():
                self.data.set_user_password_hash(inter.guild_id, inter.user.id, "")
                await inter.response.send_message(embed=warn_embed("You have set an empty password. This is not recommended."), ephemeral=True)
            else:
                pw_bytes = password.encode('utf-8')
                del password
                pw_hash = hash_salt_password(pw_bytes)
                self.data.set_user_password_hash(inter.guild_id, inter.user.id, pw_hash)
                await inter.response.send_message(embed=success_embed("Successfully set your password."), ephemeral=True)

        @client.slash_command(name='set_sudoers_role', 
                              description='Sets the sudoers role. This role allows the bearer to use `/sudo`.', 
                              dm_permission=False)
        @commands.default_member_permissions(administrator=True)
        async def set_sudoers_role(inter: disnake.ApplicationCommandInteraction,
                                     role: disnake.Role = commands.Param(description="The sudoers rule.")):
            self.data.set_guild_sudoer_role(inter.guild_id, role.id)
            await inter.response.send_message(embed=success_embed(f"Set the sudoers role to **{role.name}**."))

        @client.slash_command(name='set_sudo_role', 
                              description='Sets the sudo role. This is the role someone is given then running `/sudo`.', 
                              dm_permission=False)
        @commands.default_member_permissions(administrator=True)
        async def set_sudo_role_command(inter: disnake.ApplicationCommandInteraction,
                                     role: disnake.Role = commands.Param(description="The role someone is given when running `/sudo`.")):
            self.data.set_guild_role(inter.guild_id, role.id)
            await inter.response.send_message(embed=success_embed(f"Set the sudo role to **{role.name}**."))

        async def wrap():
            while True:
                await asyncio.sleep(1)
                cur_time = int(datetime.utcnow().timestamp())
                while self.rq.get_min_time() <= cur_time and self.rq.queue:
                    (_, user, guild, role) = self.rq.pop()
                    
                    guild = client.get_guild(guild)
                    if not guild: continue

                    user = await guild.get_or_fetch_member(user)
                    if not user: continue

                    role = user.get_role(role)
                    if not role: continue
                
                    await user.remove_roles(role)
                    

        client.loop.create_task(wrap())

        client.run(token)


    