from kh_common.exceptions.http_error import HttpErrorHandler, NotFound
from kh_common.caching import ArgsCache
from kh_common.hashing import Hashable
from kh_common.sql import SqlInterface
from kh_common.auth import KhUser


class Configs(SqlInterface, Hashable) :

	def __init__(self) :
		Hashable.__init__(self)
		SqlInterface.__init__(self)


	@ArgsCache(60)
	@HttpErrorHandler('retrieving config')
	def getConfig(self, config: str) -> str :
		data = self.query("""
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
	def updateConfig(self, user: KhUser, config: str, value: str) -> None :
		self.query("""
			INSERT INTO kheina.public.configs
			(key, value, updated_by)
			VALUES
			(%s, %s, %s)
			ON CONFLICT ON CONSTRAINT configs_pkey DO 
				UPDATE SET
					updated_on = now(),
					value = %s,
					updated_by = %s
				WHERE key = %s;
			""",
			(
				config, value, user.user_id,
				value, user.user_id, config,
			),
			commit=True,
		)
