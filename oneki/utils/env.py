from dotenv import load_dotenv
from os import getenv

load_dotenv()

TOKEN_DISCORD = getenv("TOKEN_DISCORD")
TOKEN_DISCORD_DEV = getenv("TOKEN_DISCORD_DEV")
TOKEN_LICHESS = getenv("TOKEN_LICHESS")

GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS")
PORT = getenv("PORT")