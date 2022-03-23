from typing import Union
import os
import json

from enum import Enum


DEFAULT_LANGUAGE = "en"


class TypeTranslation(Enum):
    command = "c"
    interaction = "i"
    event = "e"
    func = "f"


class Translations:
    def __init__(self, path: Union[str, os.PathLike] = None):
        # lang: dict(translation)
        self._translations = self.load_translations(path or os.path.join("resource/lang"))

    @staticmethod
    def load_translations(path: str):
        translations = {}
        for lang in os.listdir(path):
            lang_translation = {}
            for cog in os.listdir(path + f"/{lang}/cogs"):
                with open(path + f"/{lang}/cogs/{cog}", "r") as f:
                    file_content = f.read()
                    for key, value in json.loads(file_content).items():
                        lang_translation[key] = value

            with open(path + f"/{lang}/events.json", "r") as f: 
                file_content = f.read()
                for key, value in json.loads(file_content).items():
                    lang_translation[key] = value

            translations[lang] = lang_translation
        
        return translations

    def _get_translations(self, lang, *, type, name):
        """
        Command = TypeTranslation.command;
        Event = TypeTranslation.event;
        Function = TypeTranslation.func
        """ 
        _name = type.value + "_" + name
        
        default_translation = self._translations[DEFAULT_LANGUAGE][_name]
        translation = self._translations[lang].get(_name, default_translation)
        return translation
    
    def command(self, lang, command_name):
        command_translations = self._get_translations(lang, type=TypeTranslation.command, name=command_name)
        return command_translations
        
    def interaction(self, lang, interaction_name):
        command_translations = self._get_translations(lang, type=TypeTranslation.interaction, name=interaction_name)
        return command_translations
    
    def event(self, lang, event_name):
        event_translations = self._get_translations(lang, type=TypeTranslation.event, name=event_name)
        return event_translations
    
    def function(self, lang, function_name):
        function_translations = self._get_translations(lang, type=TypeTranslation.func, name=function_name)
        return function_translations


if __name__ == "__main__":
    translations = Translations(os.path.join("resource/lang"))
    translation = translations.command('es', 'avatar')
    
    print(translation)