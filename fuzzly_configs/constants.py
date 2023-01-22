from kh_common.config.constants import Environment, environment


CONSTANTS = {
	Environment.test: {
		'Host': '',
	},
	Environment.local: {
		'Host': 'http://localhost:5006',
	},
	Environment.dev: {
		'Host': 'https://config-dev.fuzz.ly',
	},
	Environment.prod: {
		'Host': 'https://config.fuzz.ly',
	},
}


locals().update(CONSTANTS[environment])


del CONSTANTS
