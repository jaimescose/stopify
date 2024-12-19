from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.debug = Config.DEBUG
db = SQLAlchemy(app)

import settings
import requests

from models import TwitterProfile, SpotifyProfile, User

spotify_api_base = 'https://accounts.spotify.com'


@app.route('/', methods=['GET', 'POST'])
def index():
    method = request.method
    if method == 'POST':
        active_user = User.get_active_user()
        if active_user:
            return redirect(url_for('user', user_id=user.id))

        spotify_endpoint = SpotifyProfile.request_token()
        return redirect(spotify_endpoint)

    elif method == 'GET':
        return render_template('index.html')


@app.route('/spotify')
def spotify():
    code = request.args.get('code')

    user = SpotifyProfile.process_callback(code)

    return redirect(url_for('user', user_id=user.id))


@app.route('/twitter')
def twitter():
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    user = TwitterProfile.process_callback(oauth_token, oauth_verifier)
    status_url = user.post_track_status()

    if status_url:
        return redirect(status_url)

    return redirect(url_for('user', user_id=user.id))


@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
def user(user_id):
    active_user = User.get_active_user()
    message = None
    if active_user:
        if active_user.id == user_id:
            if request.method == 'POST':
                if request.form['button'] == 'twitter-share':
                    authenticate = False
                    if 'twitter' in session:
                        if session['twitter']:
                            authenticate = True

                    twitter_endpoint = TwitterProfile.request_token(authenticate)
                    return redirect(twitter_endpoint)

                elif request.form['button'] == 'twitter-stop':
                    active_user.stop_posting_tweets()
                    

            top_tracks = active_user.get_top_tracks()

            if len(top_tracks) != 0:
                return render_template('tracks.html', tracks=top_tracks)
            else:
                message = {
                    'text': 'Sorry, you have nothing to see here :('
                }
            
    if not message:
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
                },
                {
                    'author_name': 'Adrian Korte',
                    'author_url': 'https://unsplash.com/@adkorte?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText',
                    'source_url': unsplash_url,
                    'source_name': 'Unsplash'
                }
            ]
        }
    }
    return render_template('about.html', about=about)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/login')
def login():
    spotify_endpoint = SpotifyProfile.request_token()
    return redirect(spotify_endpoint)
