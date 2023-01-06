from kh_common.config.constants import config_host
from kh_common.gateway import Gateway

from fuzzly_configs.models import UserConfigResponse


__version__: str = '0.0.2'


UserConfigGateway: Gateway = Gateway(config_host + '/v1/user', UserConfigResponse, 'GET')
