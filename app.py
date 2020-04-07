from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.debug = Config.DEBUG
db = SQLAlchemy(app)

import settings
import requests
from spotify.main import get_user_top_tracks

from models import User, SpotifyProfile

spotify_api_base = 'https://accounts.spotify.com'


@app.route('/', methods=['GET', 'POST'])
def index():
    method = request.method
    if method == 'POST':
        username = request.form['username']

        top_tracks = get_user_top_tracks(username)

        return render_template('result.html', tracks=top_tracks)

    elif method == 'GET':
        return render_template('index.html')


@app.route('/home', methods=['GET', 'POST'])
def home():
    method = request.method
    if method == 'POST':
        session_exists, returned_value = SpotifyProfile.request_token()

        if session_exists:
            spotify_profile = returned_value
            
            return redirect(url_for('user', spotify_profile_id=spotify_profile.id))

        spotify_endpoint = returned_value
        return redirect(spotify_endpoint)

    elif method == 'GET':
        return render_template('spotify_login.html')


@app.route('/spotify')
def spotify():
    session.clear()
    code = request.args.get('code')

    spotify_endpoint = '/'.join([spotify_api_base, 'api', 'token?'])

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.spotipy['SPOTIFY_REDIRECT_URI'],
        'client_id': settings.spotipy['SPOTIFY_CLIENT_ID'],
        'client_secret': settings.spotipy['SPOTIFY_CLIENT_SECRET']
    }

    print(spotify_endpoint)
    response = requests.post(url=spotify_endpoint, data=data)
    response = response.json()
    
    access_token = response.get("access_token")
    session['spotify_access_token'] = access_token
    refresh_token = response.get("refresh_token")
    session['spotify_refresh_token'] = refresh_token

    sp = SpotifyProfile.auth_user(access_token, refresh_token=False)
    spotify_user = sp.current_user()

    spotify_profile = SpotifyProfile(
        username=spotify_user['id'],
        email=spotify_user['email'],
        refresh_token=refresh_token
    )
    db.session.add(spotify_profile)
    db.session.commit()

    # user = User(
    #     spotify_profile_id=spotify_profile.id
    # )
    # db.session.add(user)
    # db.session.commit()

    return redirect(url_for('user', spotify_profile_id=spotify_profile.id))


@app.route('/user/<int:spotify_profile_id>')
def user(spotify_profile_id):
    # TODO: currently working with spotify_profile_id but should be user_id
    spotify_profile = SpotifyProfile.query.get(spotify_profile_id)

    top_tracks = spotify_profile.get_user_top_tracks()

    return render_template('result.html', tracks=top_tracks)
