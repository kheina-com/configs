from typing import Union

from pydantic import BaseModel


class UpdateConfig(BaseModel) :
	config: str
	value: Union[str, None]


class FundingResponse(BaseModel) :
	funds: int
	costs: int


class BannerResponse(BaseModel) :
	banner: str
