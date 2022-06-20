from dotenv import load_dotenv
from os import getenv

load_dotenv()

DISCORD_TOKEN = getenv("DISCORD_TOKEN")
DISCORD_DEV_TOKEN = getenv("DISCORD_DEV_TOKEN")
LICHESS_TOKEN = getenv("LICHESS_TOKEN")

GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS")
PORT = getenv("PORT")
PRIVATE_EXTENSIONS = bool(getenv("PRIVATE_EXTENSIONS", False))