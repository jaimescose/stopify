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
            
            return redirect(url_for('user', user_id=spotify_profile.id))

        spotify_endpoint = returned_value
        return redirect(spotify_endpoint)

    elif method == 'GET':
        return render_template('index.html')


@app.route('/spotify')
def spotify():
    code = request.args.get('code')

    spotify_profile = SpotifyProfile.process_callback(code)

    return redirect(url_for('user', user_id=spotify_profile.id))


@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
def user(user_id):
    user_allowed, spotify_profile = SpotifyProfile.user_allowed(user_id)
    if user_allowed:
        force = False
        if request.method == 'POST':
            # TODO: currently working with spotify_profile_id but should be user_idrequest.method == 'POST':
            if request.form['button'] == 'twitter':
                return 'twitter'
            elif request.form['button'] == 'refresh':
                force = True
        
        top_tracks = spotify_profile.get_user_top_tracks(force=force)

        if len(top_tracks) != 0:
            return render_template('tracks.html', tracks=top_tracks)
        else:
            message = {
                'text': 'Sorry, you have nothing to see here :('
            }
            return render_template('error.html', message=message)
    else:
        message = {
            'text': 'Sorry, you are not allowed to do this :('
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


@app.route('/logout')
def logout():
    session.pop('user_id')
    return redirect(url_for('index'))


@app.route('/login')
def login():
    _, spotify_endpoint = SpotifyProfile.request_token()
    return redirect(spotify_endpoint)
