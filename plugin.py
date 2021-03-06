import csv
import json
import logging as log
import os
import re
import sqlite3
import sys
import http.client
from contextlib import contextmanager
from galaxy.api.consts import Platform, LocalGameState
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import Authentication, Game, LicenseInfo, LicenseType, LocalGame
from pathlib import Path
from winreg import *

# Constants
PLATFORM = 0
TITLE = 1
KEY = 2


class GFNPlugin(Plugin):
	def __init__(self, reader, writer, token):
		super().__init__(
			Platform.Test,  # choose platform from available list
			"0.2",  # version
			reader,
			writer,
			token
		)

	# implement methods
	@staticmethod
	async def gfn_convert(_store: str, _title: str):
		_store = _store.lower()
		if _store == 'ubisoft connect':
			_store = 'uplay'

		_title = re.sub(r'[\W_]+', '', _title.lower())

		return _store + '_' + _title

	async def name_fix(self, _original: str):
		global gfn_mappings

		translated = _original

		if _original in self.gfn_mappings:
			translated = self.gfn_mappings[_original]
			log.debug('Translating {0} to {1}', _original, translated)

		return translated

	async def get_games(self):
		global local_games
		global gfn_mappings

		self.gfn_mappings = {}
		mappings_file = Path(__file__).resolve().parent.joinpath('gfn_mappings.csv')
		if mappings_file.is_file():
			with open(mappings_file, mode='r') as infile:
				reader = csv.reader(infile)
				self.gfn_mappings = {rows[0]: rows[1] for rows in reader}
				log.debug('Mappings: {0}'.format(str(self.gfn_mappings)))
		else:
			log.debug('Could not find mappings file [{0}]'.format(str(mappings_file)))

		gfn_site = 'api-prod.nvidia.com'

		conn = http.client.HTTPSConnection(gfn_site, timeout=20)
		payload = "{apps(country:\"DE\" language:\"de_DE\"){numberReturned,pageInfo{endCursor,hasNextPage},items{title,sortName,variants{appStore,publisherName,id}}}}\r\n"
		conn.request("POST", "/gfngames/v1/gameList", payload)
		res = conn.getresponse()

		gfn_games = []
		gfn_steam = []
		gfn_ids = {}
		
		if res.status == 200:
			data = res.read().decode("utf-8")
			json_data = json.loads(data)
			items = json_data['data']['apps']['items']

			for item in items:
				name = item['title']
				variants = item['variants']
				for variant in variants:
					store = variant['appStore']
					id = variant['id']
					
					gg_id = await self.gfn_convert(store, name)
					gfn_games.append(gg_id)
					gfn_ids[gg_id] = id
		else:
			log.error("Failure contacting GFN server, response code: {0}".format(res.status))

		with self.open_db() as cursor:
			sql = """
				select distinct substr(gp.releaseKey,1,instr(gp.releaseKey,'_')-1) platform,
				replace(substr(value,instr(value,':"')+2),'"}','') title, gp.releaseKey
				from gamepieces gp
				join gamepiecetypes gpt on gp.gamepiecetypeid = gpt.id
					where gpt.type = 'originalTitle' and gp.releaseKey not like 'test_%' and gp.releaseKey not like 'gfn_%'
			"""
			cursor.execute(sql)
			owned_games = list(cursor.fetchall())

		matched_games = []
		local_games = []

		log.debug("GFN games: {0}".format(gfn_games))
		log.debug("GFN ids: {0}".format(gfn_ids))
		for game in owned_games:
			test_title = await self.gfn_convert(game[PLATFORM], game[TITLE])
			test_title = await self.name_fix(test_title)
			game_id = ''

			if game[KEY] in gfn_steam:
				game_id = game[KEY].replace('steam_', 'gfn_')
			elif test_title in gfn_games:
				game_id = 'gfn_' + str(gfn_ids[test_title])
				#if 'Xepic_pillarsofeternitydefinitiveedition' != test_title and \
				#	'Xepic_alanwakesamericannightmare' != test_title and \
				#	'Xepic_fortheking' != test_title and \
				#	'Xuplay_watchdogs' != test_title and \
				#	'Xepic_assassinscreedsyndicate' != test_title and \
				#	'Xepic_risingstorm2vietnam' != test_title:
				#		matched_games.append(Game(game_id, game[TITLE], None, LicenseInfo(LicenseType.SinglePurchase)))
			else:
				log.debug("Not found {0}: {1} [{2}]".format(game[PLATFORM], game[TITLE], test_title))

			if game_id != '':
				log.debug("Found {0}: {1} [{2}] [{3}]".format(game[PLATFORM], game[TITLE], test_title, game_id))
				matched_games.append(Game(game_id, game[TITLE], None, LicenseInfo(LicenseType.SinglePurchase)))
				local_game = LocalGame(game_id, LocalGameState.Installed)
				self.local_games.append(local_game)

		log.debug('Matched games: {0}'.format(str(matched_games)))
		return matched_games

	@contextmanager
	def open_db(self):
		# Prepare the DB connection
		database_location = '{0}/GOG.com/Galaxy/storage/galaxy-2.0.db'.format(os.getenv('ProgramData'))
		_connection = sqlite3.connect(database_location)
		_cursor = _connection.cursor()

		_exception = None
		try:
			yield _cursor
		except Exception as e:
			_exception = e

		# Close the DB connection
		_cursor.close()
		_connection.close()

		# Re-raise the unhandled exception if needed
		if _exception:
			raise _exception

	# required

	async def authenticate(self, stored_credentials=None):
		return Authentication('anonymous', 'Anonymous')

	async def get_owned_games(self):
		return await self.get_games()

	async def launch_game(self, game_id):
		a_key = r"GeForceNOW\Shell\Open\Command"
		a_reg = ConnectRegistry(None, HKEY_CLASSES_ROOT)
		a_key = OpenKey(a_reg, a_key)
		gfn_id = game_id.replace('gfn_', '')
		log.debug("Game id is {0}".format(gfn_id))
		gfn_app = '"' + QueryValue(a_key, None) + ' --url-route="#?cmsId=' + str(gfn_id) + '&launchSource=External""'
		log.debug("Launch command is {0}".format(gfn_app))

		os.system(gfn_app)

	local_games = []
	gfn_mappings = {}

	async def get_local_games(self):
		global local_games
		log.debug('Local games: {0}'.format(self.local_games))
		return self.local_games


def main():
	create_and_run_plugin(GFNPlugin, sys.argv)


# run plugin event loop
if __name__ == "__main__":
	main()
