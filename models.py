from pydantic import BaseModel
from typing import Union


class UpdateConfig(BaseModel) :
	config: str
	value: Union[str, None]
