from os import listdir
import json

DEFAULT_LANGUAGE = "en"


class Translations:
    def __init__(self, default_language=DEFAULT_LANGUAGE):
        self.default_language = default_language
        
        # lang: dict(translation)
        self._translations = {}
        for lang in listdir("resource/lang"):
            directory = f"resource/lang/{lang}/cogs"

            translations = {}
            for cog_name in listdir(directory):
                with open(f"{directory}/{cog_name}", "r") as f:
                    for key, value in json.loads(f.read()).items():
                        translations[key] = value

            self._translations[lang] = translations

        # print(self._translations)

    def get_cog_translations(self, lang, *, type, name):
        """
        Command = "c";
        Event = "e";
        Function = "f"
        """
        default_translation = self._translations[self.default_language][f"{type}_{name}"]
        translation = self._translations[lang].get(f"{type}_{name}", default_translation)
        return translation
    
    def command(self, lang, command_name):
        command_translations = self.get_cog_translations(lang, type="c", name=command_name)
        return command_translations
        
    def event(self, lang, event_name):
        event_translations = self.get_cog_translations(lang, type="e", name=event_name)
        return event_translations
    
    def function(self, lang, function_name):
        function_translations = self.get_cog_translations(lang, type="e", name=function_name)
        return function_translations
