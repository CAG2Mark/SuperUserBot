import logging
import os
import bot
from dotenv import load_dotenv

from guilddata import GuildData
from removequeue import RemoveQueue

load_dotenv()

TOKEN = os.getenv('TOKEN')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logging.getLogger('disnake').setLevel(logging.WARNING)
logging.getLogger('logger.http').setLevel(logging.WARNING)

logger = logging.getLogger("superuserbot")
logger.setLevel(logging.DEBUG)

logger.info("Started superuserbot")

gdata = GuildData()
gdata.load()

rq = RemoveQueue()
rq.load()

instance = bot.Bot(TOKEN, gdata, rq)
