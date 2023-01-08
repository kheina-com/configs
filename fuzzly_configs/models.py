from enum import Enum, unique
from typing import Dict, List, Literal, Optional, Set, Union

from fuzzly_posts.models import Post
from pydantic import BaseModel, ConstrainedStr, conbytes, constr
from avrofastapi.schema import AvroInt


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


class Color(Enum) :
	transition: str = 'transition'
	fadetime: str = 'fadetime'
	warning: str = 'warning'
	error: str = 'error'
	valid: str = 'valid'
	general: str = 'general'
	mature: str = 'mature'
	explicit: str = 'explicit'
	icolor: str = 'icolor'
	bg0color: str = 'bg0color'
	bg1color: str = 'bg1color'
	bg2color: str = 'bg2color'
	bg3color: str = 'bg3color'
	blockquote: str = 'blockquote'
	textcolor: str = 'textcolor'
	bordercolor: str = 'bordercolor'
	linecolor: str = 'linecolor'
	borderhover: str = 'borderhover'
	subtle: str = 'subtle'
	shadowcolor: str = 'shadowcolor'
	activeshadowcolor: str = 'activeshadowcolor'
	screen_cover: str = 'screen-cover'
	border_size: str = 'border-size'
	border_radius: str = 'border-radius'
	wave_color: str = 'wave-color'
	stripe_color: str = 'stripe-color'
	main: str = 'main'
	pink: str = 'pink'
	yellow: str = 'yellow'
	green: str = 'green'
	blue: str = 'blue'
	orange: str = 'orange'
	red: str = 'red'
	cyan: str = 'cyan'
	violet: str = 'violet'
	bright: str = 'bright'
	funding: str = 'funding'
	notification_text: str = 'notification-text'
	notification_bg: str = 'notification-bg'


class UserConfig(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[List[str]]]
	blocked_users: Optional[List[int]]
	wallpaper: Optional[conbytes(min_length=8, max_length=8)]
	colors: Optional[Dict[Color, Union[Color, AvroInt]]]


PostId: ConstrainedStr = constr(regex=r'^[a-zA-Z0-9_-]{8}$')


class UserConfigRequest(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[Set[str]]]
	blocked_users: Optional[List[str]]
	wallpaper: Optional[PostId]
	colors: Optional[Dict[Color, str]]


class UserConfigResponse(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[Set[str]]]
	blocked_users: Optional[List[str]]
	wallpaper: Optional[Post]
