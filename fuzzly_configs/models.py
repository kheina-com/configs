from enum import Enum, unique
from typing import List, Literal, Optional, Set, Union

from fuzzly_posts.models import Post
from pydantic import BaseModel, ConstrainedStr, conbytes, constr


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
	wallpaper: Optional[conbytes(min_length=8, max_length=8)]


PostId: ConstrainedStr = constr(regex=r'^[a-zA-Z0-9_-]{8}$')


class UserConfigRequest(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[Set[str]]]
	blocked_users: Optional[List[str]]
	wallpaper: Optional[PostId]


class UserConfigResponse(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[Set[str]]]
	blocked_users: Optional[List[str]]
	wallpaper: Optional[Post]


assert UserConfig.__fields__.keys() == UserConfigResponse.__fields__.keys() == UserConfigResponse.__fields__.keys()
