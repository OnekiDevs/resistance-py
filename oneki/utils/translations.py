import os
import json

from enum import Enum
from typing import Union, Optional


DEFAULT_LANGUAGE = "en"


class TypeTranslation(Enum):
    command = "c"
    view = "v"
    event = "e"
    func = "f"
    
    
class Translation:
    def __init__(self, translation: dict) -> None:
        for k, v in translation.items():
            if isinstance(v, dict):
                v = Translation(v)
                
            setattr(self, k, v)
            

class Translations:
    def __init__(self, translations) -> None:
        self._translations = translations
    
    @classmethod
    def load(cls, path: Optional[Union[str, os.PathLike]] = os.path.join("resource/lang")):
        translations = {}
        for lang in os.listdir(path):
            lang_translations = {}
            for cog in os.listdir(f"{path}/{lang}"):
                with open(f"{path}/{lang}/{cog}", "r") as f:
                    for name, translation in json.loads(f.read()).items():
                        lang_translations[name] = Translation(translation)

            translations[lang] = lang_translations
        
        return cls(translations)
            
    def _get_translations(self, lang, *, type, name) -> Translation:
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
    
    def command(self, lang, command_name) -> Translation:
        command_translations = self._get_translations(lang, type=TypeTranslation.command, name=command_name)
        return command_translations
        
    def view(self, lang, interaction_name) -> Translation:
        command_translations = self._get_translations(lang, type=TypeTranslation.view, name=interaction_name)
        return command_translations
    
    def event(self, lang, event_name) -> Translation:
        event_translations = self._get_translations(lang, type=TypeTranslation.event, name=event_name)
        return event_translations
    
    def function(self, lang, function_name) -> Translation:
        function_translations = self._get_translations(lang, type=TypeTranslation.func, name=function_name)
        return function_translations
