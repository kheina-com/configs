from typing import Dict, Tuple

from avrofastapi.serialization import AvroDeserializer, AvroSerializer
from kh_common.auth import KhUser
from kh_common.caching import AerospikeCache
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.config.credentials import creator_access_token
from kh_common.exceptions.http_error import HttpErrorHandler, NotFound
from kh_common.hashing import Hashable
from kh_common.sql import SqlInterface
from patreon import API as PatreonApi
from pydantic import BaseModel

from models import BannerStore, ConfigType, CostsStore


PatreonClient: PatreonApi = PatreonApi(creator_access_token)
KVS: KeyValueStore = KeyValueStore('kheina', 'configs', local_TTL=60)
Serializers: Dict[str, Tuple[AvroSerializer, AvroDeserializer]] = {
	ConfigType.banner: (AvroSerializer(BannerStore), AvroDeserializer(BannerStore)),
	ConfigType.costs: (AvroSerializer(CostsStore), AvroDeserializer(CostsStore)),
}


assert Serializers.keys() == set(ConfigType.__members__.values()), 'Did you forget to add serializers for a config?'


class Configs(SqlInterface, Hashable) :

	def __init__(self) :
		Hashable.__init__(self)
		SqlInterface.__init__(self)


	@HttpErrorHandler('retrieving patreon campaign info')
	@AerospikeCache('kheina', 'configs', 'patreon-campaign-funds', TTL_minutes=10)
	def getFunding(self) -> int :
		return PatreonClient.fetch_campaign().data()[0].attribute('campaign_pledge_sum')


	@HttpErrorHandler('retrieving config')
	@AerospikeCache('kheina', 'configs', '{config}', _kvs=KVS)
	async def getConfig(self, config: ConfigType) -> BaseModel :
		deserializer: AvroDeserializer = Serializers[config][1]
		data = await self.query_async("""
			SELECT bytes
			FROM kheina.public.configs
			WHERE key = %s;
			""",
			(config,),
			fetch_one=True,
		)

		if not data :
			raise NotFound('no data was found for the provided config.')

		return deserializer(data[0])


	@HttpErrorHandler('updating config')
	async def updateConfig(self, user: KhUser, config: ConfigType, value: BaseModel) -> None :
		serializer: AvroSerializer = Serializers[config][0]
		data: bytes = serializer(value)
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
