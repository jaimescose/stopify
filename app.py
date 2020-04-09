from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.debug = Config.DEBUG
db = SQLAlchemy(app)

import settings
import requests

from models import User, SpotifyProfile

spotify_api_base = 'https://accounts.spotify.com'


@app.route('/', methods=['GET', 'POST'])
def index():
    method = request.method
    if method == 'POST':
        session_exists, returned_value = SpotifyProfile.request_token()

        if session_exists:
            spotify_profile = returned_value
            
            return redirect(url_for('user', spotify_profile_id=spotify_profile.id))

        spotify_endpoint = returned_value
        return redirect(spotify_endpoint)

    elif method == 'GET':
        return render_template('index.html')


@app.route('/spotify')
def spotify():
    code = request.args.get('code')

    spotify_profile = SpotifyProfile.process_callback(code)

    return redirect(url_for('user', spotify_profile_id=spotify_profile.id))


@app.route('/user/<int:spotify_profile_id>')
def user(spotify_profile_id):
    # TODO: currently working with spotify_profile_id but should be user_id
    spotify_profile = SpotifyProfile.query.get(spotify_profile_id)

    top_tracks = spotify_profile.get_user_top_tracks()

    return render_template('tracks.html', tracks=top_tracks)
