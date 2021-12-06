from os import listdir
import json

class Translations:
    def __init__(self, bot, *, default_language="en"):
        self.bot = bot
        self.default_language = default_language
        
        # lang: dict(translations_cogs)
        self._translations = {}
        for lang in listdir("resource/lang"):
            directory = f"resource/lang/{lang}/cogs"
            
            translations_cogs = {}
            for name_cog in listdir(directory):
                with open(f"{directory}/{name_cog}", "r") as f:
                    translations_cogs[name_cog.split(".")[0]] = json.loads(f.read())
            
            self._translations[lang] = translations_cogs
                    
        print(self._translations)
        
    def command(self, lang, cog, name):
        translation_command = self._translations[lang].get(cog, self._translations[self.default_language][cog])[f"c_{name}"]
        return translation_command
        


if __name__ == "__main__": 
    translations = Translations("a", default_language="es")
    print(translations.command("en", "mod", "mute"))