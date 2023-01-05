from enum import Enum, unique
from typing import List, Literal, Optional, Union

from pydantic import BaseModel


class BannerStore(BaseModel) :
	banner: Optional[str]


class CostsStore(BaseModel) :
	costs: int


@unique
class ConfigType(str, Enum) :
	banner: str = 'banner'
	costs: str = 'costs'


class UpdateBannerRequest(BaseModel) :
	config: Literal[ConfigType.banner]
	value: BannerStore


class UpdateCostsRequest(BaseModel) :
	config: Literal[ConfigType.costs]
	value: CostsStore


UpdateConfigRequest: type = Union[UpdateBannerRequest, UpdateCostsRequest]


class SaveSchemaResponse(BaseModel) :
	fingerprint: str


class FundingResponse(BaseModel) :
	funds: int
	costs: int


class BannerResponse(BannerStore) :
	pass


class BlockingBehavior(Enum) :
	hide: str = 'hide'
	omit: str = 'omit'


class UserConfig(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[List[str]]]
	blocked_users: Optional[List[int]]
