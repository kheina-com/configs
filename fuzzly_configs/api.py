from kh_common.caching import AerospikeCache
from kh_common.client import Client
from kh_common.gateway import Gateway

from fuzzly_configs.constants import Host
from fuzzly_configs.models import UserConfig, UserConfigKeyFormat, UserConfigResponse


class ConfigClient(Client) :

	def __init__(self: 'ConfigClient', *a, internal=False, **kv) :
		super().__init__(*a, **kv)
		self._config: Gateway = None
		self.config: Gateway = self.authenticated(Gateway(Host + '/v1/user', UserConfigResponse, method='GET'))

		if internal :
			self._config = AerospikeCache('kheina', 'configs', UserConfigKeyFormat, read_only=True)(self.authenticated(Gateway(Host + '/i1/user/{user_id}', UserConfig, method='GET')))
