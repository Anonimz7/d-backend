from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Field Python snake_case, JSON camelCase — sama dengan bentuk data di frontend."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
