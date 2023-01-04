from kh_common.auth import Scope
from kh_common.server import Request, ServerApp

from configs import Configs
from models import FundingResponse, UpdateConfig, BannerResponse


app = ServerApp(
	auth_required = False,
	allowed_hosts = [
		'localhost',
		'127.0.0.1',
		'*.kheina.com',
		'kheina.com',
		'*.fuzz.ly',
		'fuzz.ly',
	],
	allowed_origins = [
		'localhost',
		'127.0.0.1',
		'dev.kheina.com',
		'kheina.com',
		'dev.fuzz.ly',
		'fuzz.ly',
	],
)
configs: Configs = Configs()


@app.on_event('shutdown')
async def shutdown() :
	configs.close()


@app.get('/v1/banner', response_model=BannerResponse)
async def v1Banner() :
	return BannerResponse(
		banner=await configs.getConfig('banner'),
	)


@app.get('/v1/funding', response_model=FundingResponse)
async def v1Funding() :
	return FundingResponse(
		funds=configs.getFunding(),
		costs=(await configs.getConfig('costs', int))['costs'],
	)


@app.post('/v1/update_config', status_code=204)
async def v1UpdateConfig(req: Request, body: UpdateConfig) :
	await req.user.verify_scope(Scope.mod)

	await configs.updateConfig(
		req.user,
		body.config,
		body.value,
	)


if __name__ == '__main__' :
	from uvicorn.main import run
	run(app, host='0.0.0.0', port=5006)
