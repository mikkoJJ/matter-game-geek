from .bgg_plays import BggPlays

import argparse
import logging
from flask import Flask, render_template

app = Flask(__name__)
#app.register_blueprint(api)


@app.route('/')
@app.route('/<name>')
def get_root(name=None):
    if name is None:
        return "Please give the username to fetch data for"

    data = BggPlays(name)
    data.fetch_data()
    games = data.latest_played_games()

    logging.debug("latest games played: {}".format(games))

    html = render_template('full_statistics.html', games=games, name=name)

    return html


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--loglevel', help='Log level', default='INFO', choices=['INFO', 'WARNING', 'DEBUG'])
    parser.add_argument('-p', '--port', help='Port to host in', type=int, default=8080)
    args = parser.parse_args()

    logging.basicConfig(format='[%(levelname)s] %(message)s', level=getattr(logging, args.loglevel.upper()))

    app.run('0.0.0.0', args.port)
