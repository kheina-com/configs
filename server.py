from kh_common.server import Request, ServerApp
from kh_common.caching import KwargsCache
from fastapi.responses import Response
from models import UpdateConfig
from configs import Configs


app = ServerApp(auth_required=False)
configs = Configs()


@app.on_event('shutdown')
async def shutdown() :
	configs.close()


@app.get('/v1/banner')
async def v1FetchUser() :
	return configs.getConfig('banner')


@app.post('/v1/update_config', status_code=204)
async def v1UpdateSelf(req: Request, body: UpdateConfig) :
	await req.user.authenticated()

	configs.updateConfig(
		req.user,
		body.config,
		body.value,
	)


if __name__ == '__main__' :
	from uvicorn.main import run
	run(app, host='0.0.0.0', port=5006)
