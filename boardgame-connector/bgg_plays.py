from .bgg_api import BASE_URL

from itertools import groupby
from lxml import etree
from datetime import timedelta, datetime
import logging
import requests
import requests_cache

# Text in a BGG play comment that equates to a cooperative game win
WON_TEXT = "Won"

# Text in a BGG play comment that equates to a cooperative game loss
LOST_TEXT = "Lost"


class BggPlays:
    """ Data object for played games.
    """

    def __init__(self, username):
        """ Create a new Plays instance. Use `fetch_data` to get
        plays data from the BGG API.

        Fetched data is saved into memory (`self.data`). All requests
        to the BGG API are cached for 12 hours to prevent unnecessary
        traffic to the API.

        :param username: the name of the user to fetch data for
        """
        self.data = None
        self.username = username
        requests_cache.install_cache('bgg', expire_after=timedelta(hours=12))

    def fetch_data(self):
        """ Fetch and parse plays data from BGG API.

        :return a list of `play` objects. Each play has a `length`, `game_name`, an `game_id` and a `comment`
        """
        logging.info("Fetching data from the BGG API")
        uri = 'plays'
        params = {'username': self.username}
        xml_root = BggPlays.request_data(uri, params)
        plays = []

        for xml_play in xml_root:
            play = {}
            play['date'] = datetime.fromisoformat(xml_play.get('date'))

            for xml_play_child in xml_play:
                if xml_play_child.tag == 'item':
                    play['game_id'] = int(xml_play_child.get('objectid'))
                    play['game_name'] = xml_play_child.get('name')
                    # play['game_thumbnail'] = self._get_thumbnail(play['game_id'])
                elif xml_play_child.tag == 'comments':
                    play['comment'] = xml_play[1].text

            play['length'] = int(xml_play.get('length'))
            logging.debug("Play parsed: {}".format(play))

            plays.append(play)

        self.data = plays
        logging.info("Data fetched")

    def latest_played_games(self) -> list:
        """ Get the names of games last played as a list.

        :return a list of dicts that look like this:
        ```
        { "name": "name of the game", "date": "2018-06-22", "thumbnail": "http://thumbnail.url.example.com" }
        ```
        """
        if self.data is None:
            raise Exception("No data found for latest played games. Maybe it has not been fetched yet.")

        num_games = 10

        return [
            {'name': play['game_name'],
             'date': play['date'],
             'thumbnail': self._get_thumbnail(play['game_id'])}
            for play in self.data[:num_games]
        ]

    def cooperative_game_statistics(self) -> dict:
        """ Get cooperative game statistics (number of wins and number of losses). These are parsed from BGG play
        log comments (looking for the terms "Won" or "Lost").

        :return dict that looks like this:
        ```
        { "wins": 4, "losses": 4, "win_percentage": 50 }
        ```
        """
        if self.data is None:
            raise Exception("No data found for latest played games. Maybe it has not been fetched yet.")

        wins = len([play for play in self.data if 'comment' in play and WON_TEXT in play['comment']])
        losses = len([play for play in self.data if 'comment' in play and LOST_TEXT in play['comment']])
        percentage = (wins / (wins + losses)) * 100

        return {'wins': wins, 'losses': losses, 'win_percentage': int(percentage)}

    def game_info_by_id(self, game_id: int) -> dict:
        """ Get the first game that matches game_id from the plays.

        :param game_id: the game id to look for
        :return: a dict that look like this:
        ```
        { "name": "name of the game", "thumbnail": "http://thumbnail.url.example.com" }
        ```
        """
        play = next(g for g in self.data if g['game_id'] == game_id)
        return {'name': play['game_name'], 'thumbnail': self._get_thumbnail(play['game_id'])}

    def most_played_game(self) -> dict:
        """ Get the game that has the most amount of time marked on it, and how many minutes total
        it has been played.

        :return a dict that look like this:
        ```
        { "name": "name of the game", "thumbnail": "http://thumbnail.url.example.com", 'time': 134 }
        ```
        """
        if self.data is None:
            raise Exception("No data found for latest played games. Maybe it has not been fetched yet.")

        grouped = groupby(sorted(self.data, key=lambda k: k['game_id']), key=lambda k: k['game_id'])

        summed = []
        for key, group in grouped:
            sum_length = sum(g['length'] for g in group)
            summed.append((key, sum_length))

        most_played = max(summed, key=lambda k: k[1])

        game = self.game_info_by_id(most_played[0])
        game['time'] = most_played[1]

        return game

    @staticmethod
    def request_data(uri: str, params: dict) -> etree:
        """ Do a GET request to the BGG API.

        :param uri: the URI to request data from
        :param params: URL parameters to add to the request
        :return xml element tree containing the response
        """
        url = BASE_URL + uri
        response = requests.get(url, params=params)
        if response.status_code != 200:
            logging.error("Fetching failed! Status code {}".format(response.status_code))

        data = etree.fromstring(response.content)
        return data

    @staticmethod
    def _get_thumbnail(game_id: int) -> str:
        """ Return the thumbnail URL for the given game.

        :param game_id: id of the game in BGG to get thumbnail for
        :return: URL of the thumbnail
        """
        xml_root = BggPlays.request_data('thing', {'id': game_id})
        for node in xml_root[0]:
            if node.tag == 'thumbnail':
                return node.text
