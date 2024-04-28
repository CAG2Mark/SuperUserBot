import os
import json

from utils import mutex, datawrite

from threading import Lock

lock = Lock()
filelock = Lock()

GUILD_ROLES = "guild_roles"
GUILD_SUDOERS_ROLES = "guild_sudoers_roles"
GUILD_PASSWORDS = "guild_passwords"

FILE = "guilddata.json"


def argstostr(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *[str(x) for x in args], **kwargs)
        self.export()
        return result
    return wrapper

# converts all but the last argument to a string
def inpargstostr(func):
    def wrapper(self, *args, **kwargs):
        newargs = []
        for i, a in enumerate(args):
            if i < len(args) - 1:
                newargs.append(str(a))
            else:
                newargs.append(a)

        result = func(self, *newargs, **kwargs)
        self.export()
        return result
    return wrapper

class GuildData:
    def __init__(self):
        self.map = {}
        self.map[GUILD_ROLES] = {}
        self.map[GUILD_SUDOERS_ROLES] = {}
        self.map[GUILD_PASSWORDS] = {}

    def roles(self):
        return self.map[GUILD_ROLES]
    
    def sudoers_roles(self):
        return self.map[GUILD_SUDOERS_ROLES]
    
    def passwords(self):
        return self.map[GUILD_PASSWORDS]

    @argstostr
    @mutex(lock=lock)
    def get_guild_role(self, guild) -> int:
        if guild in self.roles():
            return self.roles()[guild]
        return None

    @inpargstostr
    @mutex(lock=lock)
    @datawrite
    def set_guild_role(self, guild: int, role: int):
        self.roles()[guild] = role

    @argstostr
    @mutex(lock=lock)
    def get_guild_sudoer_role(self, guild) -> int:
        if guild in self.sudoers_roles():
            return self.sudoers_roles()[guild]
        return None

    @inpargstostr
    @mutex(lock=lock)
    @datawrite
    def set_guild_sudoer_role(self, guild: int, role: int):
        self.sudoers_roles()[guild] = role
    
    @argstostr
    @mutex(lock=lock)
    def get_user_password_hashsalt(self, guild: int, user: int) -> str:
        if not guild in self.passwords():
            return None
        
        if not user in self.passwords()[guild]:
            return None
        
        return self.passwords()[guild][user]
    
    @inpargstostr
    @mutex(lock=lock)
    @datawrite
    def set_user_password_hash(self, guild: int, user: int, hashsalt: str):
        if not guild in self.passwords():
            self.passwords()[guild] = {}
        
        self.passwords()[guild][user] = hashsalt

    @mutex(lock=filelock)
    def export(self):
        with open(FILE, 'w') as f:
            json.dump(self.map, f)
    
    @mutex(lock=filelock)
    def load(self):
        if not os.path.exists(FILE): 
            return

        with open(FILE, 'r') as f:
            self.map = json.load(f)