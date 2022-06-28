# Oneki-py
---
Oneki-bot written in python

## Installation
**Python 3.8 or higher is required**

```bash
# clone the repo
$ git clone https://github.com/OnekiDevs/oneki-py.git

# change the working directory to oneki-py
$ cd oneki-py

# install the requirements
$ python3 -m pip install -r requirements.txt
```

## Example env
```
DISCORD_TOKEN = ""
DISCORD_DEV_TOKEN = ""

GOOGLE_APPLICATION_CREDENTIALS = {}

DEBUG_CHANNEL = ...
```
## Env values
- **DISCORD_TOKEN**: Required -> your bot token
    > optional only if DISCORD_DEV_TOKEN is specified
- **DISCORD_DEV_TOKEN**: Optional -> your dev bot token
    > this is the token that takes priority
- **GOOGLE_APPLICATION_CREDENTIALS**: Required -> your google app credentials
    > use firestore
- **DEBUG_CHANNEL**: Optional -> discord text channel id
    > all errors are sent to this channel, it is recommended to specify it to avoid errors

## Credits
I would like to thank the following people
- [Rapptz](https://github.com/Rapptz) creator of discord.py and RoboDanny
- [LostLuma](https://github.com/LostLuma) creator of [mousey](https://github.com/LostLuma/Mousey) bot

## License
- [GPL v3.0](LICENSE)