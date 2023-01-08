from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Type, Union
from re import Match, Pattern, compile as re_compile

from aiohttp import ClientResponse
from avrofastapi.schema import convert_schema
from avrofastapi.serialization import AvroDeserializer, AvroSerializer, Schema, parse_avro_schema
from fuzzly_posts import PostGateway
from fuzzly_posts.models import Post
from kh_common.auth import KhUser
from kh_common.base64 import b64decode, b64encode
from kh_common.caching import AerospikeCache, ArgsCache
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.config.constants import avro_host
from kh_common.config.credentials import creator_access_token
from kh_common.exceptions.http_error import HttpErrorHandler, NotFound, BadRequest
from kh_common.gateway import Gateway
from kh_common.sql import SqlInterface
from patreon import API as PatreonApi
from pydantic import BaseModel

from fuzzly_configs.models import BannerStore, ConfigType, CostsStore, SaveSchemaResponse, UserConfig, UserConfigRequest, UserConfigResponse, Color


PatreonClient: PatreonApi = PatreonApi(creator_access_token)
KVS: KeyValueStore = KeyValueStore('kheina', 'configs', local_TTL=60)
UserConfigSerializer: AvroSerializer = AvroSerializer(UserConfig)
UserConfigKeyFormat: str = 'user.{user_id}'
SetAvroSchemaGateway: Gateway = Gateway(avro_host + '/v1/schema', SaveSchemaResponse, 'POST')
GetAvroSchemaGateway: Gateway = Gateway(avro_host + '/v1/schema/{fingerprint}', decoder=ClientResponse.read)
AvroMarker: bytes = b'\xC3\x01'
ColorRegex: Pattern = re_compile(r'^(?:#(?P<hex>[a-f0-9]{8}|[a-f0-9]{6})|(?P<var>[a-z0-9-]+))$')


class Configs(SqlInterface) :

	UserConfigFingerprint: bytes
	Serializers: Dict[str, Tuple[AvroSerializer, bytes]]
	SerializerTypeMap: Dict[BannerStore, Type[BaseModel]] = {
		ConfigType.banner: BannerStore,
		ConfigType.costs: CostsStore,
	}

	async def startup(self) :
		self.Serializers = {
			ConfigType.banner: (AvroSerializer(BannerStore), b64decode((await SetAvroSchemaGateway(body=convert_schema(BannerStore))).fingerprint)),
			ConfigType.costs: (AvroSerializer(CostsStore), b64decode((await SetAvroSchemaGateway(body=convert_schema(CostsStore))).fingerprint)),
		}
		self.UserConfigFingerprint = b64decode((await SetAvroSchemaGateway(body=convert_schema(UserConfig))).fingerprint)
		assert self.Serializers.keys() == set(ConfigType.__members__.values()), 'Did you forget to add serializers for a config?'
		assert self.SerializerTypeMap.keys() == set(ConfigType.__members__.values()), 'Did you forget to add serializers for a config?'


	@lru_cache(maxsize=32)
	async def getSchema(fingerprint: bytes) -> Schema:
		return parse_avro_schema(await GetAvroSchemaGateway(fingerprint=b64encode(fingerprint).decode()))


	@HttpErrorHandler('retrieving patreon campaign info')
	@AerospikeCache('kheina', 'configs', 'patreon-campaign-funds', TTL_minutes=10)
	def getFunding(self) -> int :
		return PatreonClient.fetch_campaign().data()[0].attribute('campaign_pledge_sum')


	@HttpErrorHandler('retrieving config')
	@AerospikeCache('kheina', 'configs', '{config}', _kvs=KVS)
	async def getConfig(self, config: ConfigType) -> BaseModel :
		data: List[bytes] = await self.query_async("""
			SELECT bytes
			FROM kheina.public.configs
			WHERE key = %s;
			""",
			(config,),
			fetch_one=True,
		)

		if not data :
			raise NotFound('no data was found for the provided config.')

		value: bytes = bytes(data[0])
		assert value[:2] == AvroMarker

		deserializer: AvroDeserializer = AvroDeserializer(read_model=self.SerializerTypeMap[config], write_model=await Configs.getSchema(value[2:10]))
		return deserializer(value[10:])


	@HttpErrorHandler('updating config')
	async def updateConfig(self, user: KhUser, config: ConfigType, value: BaseModel) -> None :
		serializer: Tuple[AvroSerializer, bytes] = self.Serializers[config]
		data: bytes = AvroMarker + serializer[1] + serializer[0](value)
		await self.query_async("""
			INSERT INTO kheina.public.configs
			(key, bytes, updated_by)
			VALUES
			(%s, %s, %s)
			ON CONFLICT ON CONSTRAINT configs_pkey DO 
				UPDATE SET
					updated_on = now(),
					bytes = %s,
					updated_by = %s;
			""",
			(
				config, data, user.user_id,
				data, user.user_id,
			),
			commit=True,
		)
		KVS.put(config, value)


	def _validateColors(colors: Optional[Dict[Color, str]]) -> Optional[Dict[Color, Union[str, int]]] :
		if not colors :
			return None

		output: Dict[Color, Union[str, int]] = { }

		# color input is very strict
		for color, value in colors.items() :
			match: Match[str] = ColorRegex.match(value)
			if not match :
				raise BadRequest(f'{value} is not a valid color. value must be in the form "#xxxxxx", "#xxxxxxxx", or the name of another color variable (without the preceding deshes)')

			if match.group('hex') :
				if len(match.group('hex')) == 6 :
					output[color] = int(match.group('hex') + 'ff', 16)

				elif len(match.group('hex')) == 8 :
					output[color] = int(match.group('hex') + 'ff', 16)

				else :
					raise BadRequest(f'{value} is not a valid color. value must be in the form "#xxxxxx", "#xxxxxxxx", or the name of another color variable (without the preceding deshes)')

			else :
				try :
					output[color] = Color(match.group('var'))

				except :
					raise BadRequest(f'{value} is not a valid color. value must be in the form "#xxxxxx", "#xxxxxxxx", or the name of another color variable (without the preceding deshes)')

		return output


	@HttpErrorHandler('saving user config')
	async def setUserConfig(self, user: KhUser, value: UserConfigRequest) -> None :
		user_config: UserConfig = UserConfig(
			blocking_behavior=value.blocking_behavior,
			blocked_tags=value.blocked_tags,
			# TODO: internal tokens need to be added so that we can convert handles to user ids
			blocked_users=None,
			wallpaper=value.wallpaper,
			colors=Configs._validateColors(value.colors),
		)

		data: bytes = AvroMarker + self.UserConfigFingerprint + UserConfigSerializer(user_config)
		config_key: str = UserConfigKeyFormat.format(user_id=user.user_id)
		await self.query_async("""
			INSERT INTO kheina.public.configs
			(key, bytes, updated_by)
			VALUES
			(%s, %s, %s)
			ON CONFLICT ON CONSTRAINT configs_pkey DO 
				UPDATE SET
					updated_on = now(),
					bytes = %s,
					updated_by = %s;
			""",
			(
				config_key, data, user.user_id,
				data, user.user_id,
			),
			commit=True,
		)

		KVS.put(config_key, user_config)


	@AerospikeCache('kheina', 'configs', UserConfigKeyFormat, _kvs=KVS)
	async def _getUserConfig(self, user_id: int) -> UserConfig :
		data: List[bytes] = await self.query_async("""
			SELECT bytes
			FROM kheina.public.configs
			WHERE key = %s;
			""",
			(UserConfigKeyFormat.format(user_id=user_id),),
			fetch_one=True,
		)

		if not data :
			return UserConfig()

		value: bytes = bytes(data[0])
		assert value[:2] == AvroMarker

		deserializer: AvroDeserializer = AvroDeserializer(read_model=UserConfig, write_model=await Configs.getSchema(value[2:10]))
		return deserializer(value[10:])


	@ArgsCache(TTL_minutes=1)
	async def getPost(post_id: str) -> Post :
		return await PostGateway(post=post_id)


	@HttpErrorHandler('retrieving user config')
	async def getUserConfig(self, user: KhUser) -> UserConfigResponse :
		user_config: UserConfig = await self._getUserConfig(user.user_id)

		wallpaper: Optional[Post] = None

		if user_config.wallpaper :
			wallpaper = await Configs.getPost(user_config.wallpaper.decode())

		return UserConfigResponse(
			blocking_behavior=user_config.blocking_behavior,
			blocked_tags=user_config.blocked_tags,
			# TODO: internal tokens need to be added so that we can convert user ids to handles
			blocked_users=None,
			wallpaper=wallpaper,
		)


	@HttpErrorHandler('retrieving custom theme')
	async def getUserTheme(self, user: KhUser) -> str :
		user_config: UserConfig = await self._getUserConfig(user.user_id)

		if not user_config.colors :
			return ''

		colors: str = ''

		for name, value in user_config.colors.items() :
			if isinstance(value, int) :
				colors += f'--{name.value}:{value:08x};'

			elif isinstance(value, Color) :
				colors += f'--{name.value}:var(--{value.value});'

		return 'html{' + colors + '}'
