from asyncio import Task, ensure_future, run

from fastapi.responses import PlainTextResponse
from kh_common.auth import Scope
from kh_common.server import Request, ServerApp

from configs import Configs
from fuzzly_configs.models import BannerResponse, CostsStore, FundingResponse, UpdateConfigRequest, UserConfig, UserConfigRequest, UserConfigResponse


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


@app.on_event('startup')
async def startup() :
	await configs.startup()


@app.on_event('shutdown')
async def shutdown() :
	configs.close()


################################################## INTERNAL ##################################################
@app.get('/i1/user/{user_id}', response_model=UserConfig)
async def i1UserConfig(req: Request, user_id: int) -> UserConfig :
	await req.user.verify_scope(Scope.internal)
	return await configs._getUserConfig(user_id)


##################################################  PUBLIC  ##################################################
@app.get('/v1/banner', response_model=BannerResponse)
async def v1Banner() -> BannerResponse :
	return await configs.getConfig('banner')


@app.get('/v1/funding', response_model=FundingResponse)
async def v1Funding() -> FundingResponse :
	costs: Task[CostsStore] = ensure_future(configs.getConfig('costs'))
	return FundingResponse(
		funds=configs.getFunding(),
		costs=(await costs).costs,
	)


@app.post('/v1/update_config', status_code=204)
async def v1UpdateConfig(req: Request, body: UpdateConfigRequest) -> None :
	await req.user.verify_scope(Scope.mod)
	await configs.updateConfig(
		req.user,
		body.config,
		body.value,
	)


@app.post('/v1/update_user_config', status_code=204)
async def v1UpdateUserConfig(req: Request, body: UserConfigRequest) -> None :
	await req.user.authenticated(Scope.user)
	await configs.setUserConfig(
		req.user,
		body,
	)


@app.get('/v1/user', response_model=UserConfigResponse)
async def v1UserConfig(req: Request) -> UserConfigResponse :
	await req.user.authenticated()
	return await configs.getUserConfig(req.user)


@app.get('/v1/theme.css', response_model=str)
async def v1UserTheme(req: Request) -> PlainTextResponse :
	await req.user.authenticated()
	return PlainTextResponse(
		content=await configs.getUserTheme(req.user),
		media_type='text/css',
		headers={
			'cache-control': 'no-cache',
		},
	)


run(startup())  # fastapi/starlette doesn't trigger startup event, so run it manually
if __name__ == '__main__' :
	from uvicorn.main import run
	run(app, host='0.0.0.0', port=5006)
