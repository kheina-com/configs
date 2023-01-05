from typing import Dict, Tuple, Type, List

from avrofastapi.serialization import AvroDeserializer, AvroSerializer, parse_avro_schema, Schema
from kh_common.auth import KhUser
from kh_common.caching import AerospikeCache
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.config.constants import avro_host
from kh_common.config.credentials import creator_access_token
from kh_common.exceptions.http_error import HttpErrorHandler, NotFound
from kh_common.sql import SqlInterface
from patreon import API as PatreonApi
from pydantic import BaseModel
from kh_common.gateway import Gateway
from avrofastapi.schema import convert_schema
from aiohttp import ClientResponse
from kh_common.base64 import b64encode
from functools import lru_cache

from models import BannerStore, ConfigType, CostsStore, UserConfig, SaveSchemaResponse


PatreonClient: PatreonApi = PatreonApi(creator_access_token)
KVS: KeyValueStore = KeyValueStore('kheina', 'configs', local_TTL=60)
Serializers: Dict[str, Tuple[AvroSerializer, bytes]] = { }
SerializerTypeMap: Dict[BannerStore, Type[BaseModel]] = {
	ConfigType.banner: BannerStore,
	ConfigType.costs: CostsStore,
}
UserConfigSerializer: AvroSerializer = AvroSerializer(UserConfig)
UserConfigDeserializer: AvroDeserializer = AvroDeserializer(UserConfig)
UserConfigKeyFormat: str = 'user_config.{user_id}'
UserConfigFingerprint: bytes = b''
SetAvroSchemaGateway: Gateway = Gateway(avro_host + '/v1/schema', SaveSchemaResponse, 'POST')
GetAvroSchemaGateway: Gateway = Gateway(avro_host + '/v1/schema/{fingerprint}', decoder=ClientResponse.read)
AvroMarker: bytes = b'\xC3\x01'


assert SerializerTypeMap.keys() == set(ConfigType.__members__.values()), 'Did you forget to add serializers for a config?'


class Configs(SqlInterface) :

	async def startup(self) :
		Serializers[ConfigType.banner] = (AvroSerializer(BannerStore), (await SetAvroSchemaGateway(body=convert_schema(BannerStore))).fingerprint)
		Serializers[ConfigType.costs] = (AvroSerializer(CostsStore), (await SetAvroSchemaGateway(body=convert_schema(CostsStore))).fingerprint)
		UserConfigFingerprint = (await SetAvroSchemaGateway(body=convert_schema(UserConfig))).fingerprint.encode()
		assert Serializers.keys() == set(ConfigType.__members__.values()), 'Did you forget to add serializers for a config?'


	@lru_cache(maxsize=32)
	async def getSchema(fingerprint: str) -> Schema:
		return parse_avro_schema(await GetAvroSchemaGateway(fingerprint=fingerprint))


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

		assert data[0][:2] == AvroMarker
		fingerprint: str = b64encode(data[0][2:10])

		deserializer: AvroDeserializer = AvroDeserializer(read_model=SerializerTypeMap[config], write_model=await self.getSchema(fingerprint))

		return deserializer(data[0][10:])


	@HttpErrorHandler('updating config')
	async def updateConfig(self, user: KhUser, config: ConfigType, value: BaseModel) -> None :
		serializer: Tuple[AvroSerializer, bytes] = Serializers[config]
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


	@HttpErrorHandler('saving user config')
	async def setUserConfig(self, user: KhUser, value: UserConfig) -> None :
		data: bytes = AvroMarker + UserConfigFingerprint + UserConfigSerializer(value)
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
		KVS.put(config_key, value)


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
			raise NotFound('no data was found for the provided config.')

		assert data[0][:2] == AvroMarker
		fingerprint: str = b64encode(data[0][2:10])

		deserializer: AvroDeserializer = AvroDeserializer(read_model=UserConfig, write_model=await self.getSchema(fingerprint))

		return deserializer(data[0][10:])


	@HttpErrorHandler('saving user config')
	async def getUserConfig(self, user: KhUser) -> UserConfig :
		return await self._getUserConfig(user.user_id)
