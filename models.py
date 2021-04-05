from pydantic import BaseModel


class UpdateConfig(BaseModel) :
	config: str
	value: str
