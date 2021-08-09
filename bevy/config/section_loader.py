from bevy import Context
import bevy.config.config as config
from typing import Any, Optional


class SectionLoader:
    def __init__(self, section_name: str, filename: Optional[str] = None):
        self.section_name = section_name
        self.filename = filename

    def __bevy_build__(self, bevy_context: Context, *args, **kwargs) -> Any:
        config_manager = bevy_context.get(config.Config)
        return config_manager.get_section(self.section_name, self.filename)
