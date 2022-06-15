from typing import Union
import os
import json

from enum import Enum


DEFAULT_LANGUAGE = "en"


class TypeTranslation(Enum):
    command = "c"
    view = "v"
    event = "e"
    func = "f"


class Translations:
    def __init__(self, path: Union[str, os.PathLike] = None):
        self._path = path or os.path.join("resource/lang")
        # lang: dict(translation)
        self._translations = self.load(self._path)

    @staticmethod
    def load(path: str) -> dict:
        translations = {}
        for lang in os.listdir(path):
            lang_translation = {}
            for dir in os.listdir(path + f"/{lang}"):
                try:
                    with open(path + f"/{lang}/{dir}", "r") as f:
                        content = f.read()
                        for k, v in json.loads(content).items():
                            lang_translation[k] = v
                except:
                    for name in os.listdir(path + f"/{lang}/{dir}"):
                        with open(path + f"/{lang}/{dir}/{name}", "r") as f:
                            content = f.read()
                            for k, v in json.loads(content).items():
                                lang_translation[k] = v

            translations[lang] = lang_translation
        
        return translations

    def reload(self) -> dict:
        self._translations = self.load(self._path)
        return self._translations

    def _get_translations(self, lang, *, type, name):
        """
        Command = TypeTranslation.command;
        View = TypeTranslation.view
        Event = TypeTranslation.event;
        Function = TypeTranslation.func
        """ 
        _name = type.value + "_" + name
        lang = lang.split("-")[0]
        
        default_translation = self._translations[DEFAULT_LANGUAGE][_name]
        translation = self._translations[lang].get(_name, default_translation)
        return translation
    
    def command(self, lang, command_name):
        command_translations = self._get_translations(lang, type=TypeTranslation.command, name=command_name)
        return command_translations
        
    def view(self, lang, interaction_name):
        command_translations = self._get_translations(lang, type=TypeTranslation.view, name=interaction_name)
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