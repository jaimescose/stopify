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
    active_session, active_spotify_profile = SpotifyProfile.get_active_spotify_profile()
    requested_spotify_profile = SpotifyProfile.query.get(spotify_profile_id)

    if not active_spotify_profile or (requested_spotify_profile != active_spotify_profile):
        message = {
            'text': 'Sorry, you are not allowed to see this :('
        }
    else:
        top_tracks = requested_spotify_profile.get_user_top_tracks()

        if len(top_tracks) != 0:
            return render_template('tracks.html', tracks=top_tracks)
        else:
            message = {
                'text': 'Sorry, you have nothing to see here :('
            }   
    
    return render_template('error.html', message=message)



@app.route('/about')
def about():
    unsplash_url = 'https://unsplash.com/s/photos/nothing?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText'
    about = {
        'credits': {
            'images': [
                {
                    'author_name': 'Joshua Golde',
                    'author_url': 'https://unsplash.com/@joshgmit?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText',
                    'source_url': unsplash_url,
                    'source_name': 'Unsplash'
                },
                {
                    'author_name': 'Laura Skinner',
                    'author_url': 'https://unsplash.com/@thegreatcatwar?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText',
                    'source_url': unsplash_url,
                    'source_name': 'Unsplash'
                }
            ]
        }
    }
    return render_template('about.html', about=about)


@app.route('/tracks')
def tracks():
    _, spotify_profile = SpotifyProfile.get_active_spotify_profile()
    return redirect(url_for('user', spotify_profile_id=spotify_profile.id))


@app.route('/logout')
def logout():
    session.pop('spotify_refresh_token')

    return redirect(url_for('index'))


@app.route('/login')
def login():
    _, spotify_endpoint = SpotifyProfile.request_token()
    return redirect(spotify_endpoint)
