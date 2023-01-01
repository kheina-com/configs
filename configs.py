from typing import Any, Dict

from kh_common.auth import KhUser
from kh_common.caching import AerospikeCache
from kh_common.config.credentials import creator_access_token
from kh_common.exceptions.http_error import HttpErrorHandler, NotFound
from kh_common.hashing import Hashable
from kh_common.sql import SqlInterface
from patreon import API as PatreonApi


# at some point we probably want to convert all of this to using avro and storing things as binary
patreon_client: PatreonApi = PatreonApi(creator_access_token)


class Configs(SqlInterface, Hashable) :

	def __init__(self) :
		Hashable.__init__(self)
		SqlInterface.__init__(self)


	@HttpErrorHandler('retrieving patreon campaign info')
	@AerospikeCache('kheina', 'configs', 'patreon-campaign-funds')
	def getFunding(self) -> int :
		return patreon_client.fetch_campaign().data()[0].attribute('campaign_pledge_sum')


	@HttpErrorHandler('retrieving config')
	@AerospikeCache('kheina', 'configs', '{config}', local_TTL=60)
	async def getConfig(self, config: str) -> Dict[str, str] :
		data = await self.query_async("""
			SELECT value
			FROM kheina.public.configs
			WHERE key = %s;
			""",
			(config,),
			fetch_one=True,
		)

		if not data :
			raise NotFound('no data was found for the provided config.')

		return {
			config: data[0],
		}


	@HttpErrorHandler('updating config')
	async def updateConfig(self, user: KhUser, config: str, value: str) -> None :
		await self.query_async("""
			INSERT INTO kheina.public.configs
			(key, value, updated_by)
			VALUES
			(%s, %s, %s)
			ON CONFLICT ON CONSTRAINT configs_pkey DO 
				UPDATE SET
					updated_on = now(),
					value = %s,
					updated_by = %s
			""",
			(
				config, value, user.user_id,
				value, user.user_id,
			),
			commit=True,
		)
