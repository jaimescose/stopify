from app import db
import settings

import json
from sqlalchemy.types import JSON
from flask import session
import requests
from datetime import datetime
from requests_oauthlib import OAuth1Session

import spotipy
import twitter

from utils import encrypt_token, decrypt_token

spotify_api_base = 'https://accounts.spotify.com'
twitter_api_base = 'https://api.twitter.com/oauth'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    spotify_profile = db.relationship('SpotifyProfile', uselist=False)
    twitter_profile = db.relationship('TwitterProfile', uselist=False)
    last_post_date = db.Column(db.DateTime, nullable=True)
    posted_tracks = db.Column(db.Integer, default=0)

    @classmethod
    def get_active_user(cls):
        if 'user_id' in session:
            return User.query.get(session['user_id'])

        return None

    def get_top_tracks(self, force=False):
        spotify_profile = self.spotify_profile
        return spotify_profile.get_user_top_tracks(force=force)


class SpotifyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    tracks = db.Column(JSON)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True,
        unique=True
    )
    _refresh_token = db.Column('refres_token', db.String, unique=True, nullable=False)

    @property
    def refresh_token(self):
        return decrypt_token(self._refresh_token, 'spotify')

    @refresh_token.setter
    def refresh_token(self, value):
        self._refresh_token = encrypt_token(value, 'spotify')

    @classmethod
    def get_credentials(cls):
        return settings.spotify['SPOTIFY_CLIENT_ID'], \
            settings.spotify['SPOTIFY_CLIENT_SECRET'], \
            settings.spotify['SPOTIFY_REDIRECT_URI'], \
            settings.spotify['ENCRYPTION_KEY']

    @classmethod
    def request_token(cls):
        required_scopes = 'user-read-email, user-top-read'
        spotify_endpoint = '/'.join([spotify_api_base, 'authorize?'])
        credentials = cls.get_credentials()

        data = {
            'client_id': credentials[0],
            'response_type': 'code',
            'redirect_uri': credentials[2],
            'scope': required_scopes,
            'show_dialog': True
        }

        spotify_endpoint = spotify_endpoint + (
            'client_id={client_id}'
            '&response_type={response_type}'
            '&redirect_uri={redirect_uri}'
            '&scope={scope}'
            '&show_dialog={show_dialog}'
        ).format_map(data)

        return spotify_endpoint

    @classmethod
    def auth_user(cls, token, refresh_token=True) -> spotipy.Spotify():
        if refresh_token:
            spotify_endpoint = '/'.join([spotify_api_base, 'api', 'token?'])
            credentials = cls.get_credentials()

            data = {
                'grant_type': 'refresh_token',
                'refresh_token': token,
                'client_id': credentials[0],
                'client_secret': credentials[1]
            }
            response = requests.post(url=spotify_endpoint, data=data)
            response = response.json()

            token = response.get("access_token")

        return spotipy.Spotify(auth=token)

    @classmethod
    def process_callback(cls, code):
        spotify_endpoint = '/'.join([spotify_api_base, 'api', 'token?'])
        credentials = cls.get_credentials()

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': credentials[2],
            'client_id': credentials[0],
            'client_secret': credentials[1]
        }

        response = requests.post(url=spotify_endpoint, data=data)
        response = response.json()
        
        refresh_token = response.get("refresh_token")

        sp = SpotifyProfile.auth_user(refresh_token)
        spotify_user = sp.current_user()

        spotify_profile = SpotifyProfile.query.filter_by(
            email=spotify_user['email']
        ).first()

        if not spotify_profile:
            spotify_profile = SpotifyProfile(
                username=spotify_user['id'],
                email=spotify_user['email'],
                refresh_token=refresh_token
            )
            db.session.add(spotify_profile)
            db.session.commit()

            user = User(spotify_profile=spotify_profile)
            db.session.add(user)
            db.session.commit()
        else:
            user = User.query.get(spotify_profile.user_id)            

        session['user_id'] = user.id

        return user

    def get_user_top_tracks(self, time_range='short_term', limit=4, force=False):
        if not force:
            top_tracks = self.tracks
            if top_tracks:
                return json.loads(top_tracks)

        sp = SpotifyProfile.auth_user(self.refresh_token)

        results = sp.current_user_top_tracks(
            time_range=time_range, 
            limit=limit
        )

        top_tracks = []
        items = results['items']
        if len(items) != 0:
            for item in results['items']:
                album = item['album']
                artist = album['artists'][0]['name']
                image = album['images'][0]
                track = {
                    'name': item['name'],
                    'number': item['track_number'],
                    'popularity': item['popularity'],
                    'preview': item['preview_url'],
                    'artist': artist,
                    'image': image
                }
                
                top_tracks.append(track)

        self.tracks = json.dumps(top_tracks)
        db.session.commit()

        return top_tracks


class TwitterProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    twitter_id = db.Column(db.Integer)
    username = db.Column(db.String(80), unique=True, nullable=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True,
        unique=True
    )
    _token = db.Column('token', db.String, unique=True, nullable=False)
    _token_secret = db.Column('token_secret', db.String, unique=True, nullable=False)

    @property
    def token(self):
        return decrypt_token(self._token, 'twitter')

    @token.setter
    def token(self, value):
        self._token = encrypt_token(value, 'twitter')

    @property
    def token_secret(self):
        return decrypt_token(self.c, 'twitter')

    @token_secret.setter
    def token_secret(self, value):
        self.token_secret = encrypt_token(value, 'twitter')

    @classmethod
    def get_credentials(cls):
        return settings.twitter['TWITTER_CLIENT_ID'], \
            settings.twitter['TWITTER_CLIENT_SECRET'], \
            settings.twitter['TWITTER_REDIRECT_URI'], \
            settings.twitter['ENCRYPTION_KEY']
    
    @classmethod
    def request_token(cls):
        twitter_endpoint = '/'.join([twitter_api_base, 'request_token'])

        credentials = TwitterProfile.get_credentials()
        oauth_session = OAuth1Session(
            client_key=credentials[0],
            client_secret=credentials[1]
        )

        data = {
            'outh_callback': credentials[2]
        }

        response = oauth_session.get(twitter_endpoint, params=data)

        oauth_token, oauth_token_secret, oauth_callback_confirmed = response.text.split('&')
        oauth_token = oauth_token.split('=')[1]
        oauth_token_secret = oauth_token_secret.split('=')[1]
        oauth_callback_confirmed = oauth_callback_confirmed.split('=')[1]

        twitter_endpoint = '/'.join([twitter_api_base, 'authenticate?oauth_token={}'])
        twitter_endpoint = twitter_endpoint.format(oauth_token)

        return twitter_endpoint

    @classmethod
    def process_callback(cls, oauth_token, oauth_verifier):
        twitter_endpoint = '/'.join([twitter_api_base, 'access_token'])

        data = {
            'oauth_token': oauth_token,
            'oauth_verifier': oauth_verifier
        }

        response = requests.post(twitter_endpoint, params=data)

        oauth_token, oauth_token_secret, twitter_id, username = response.text.split('&')
        oauth_token = oauth_token.split('=')[1]
        oauth_token_secret = oauth_token_secret.split('=')[1]
        twitter_id = twitter_id.split('=')[1]
        username = username.split('=')[1]

        twitter_profile = TwitterProfile.query.filter_by(
            twitter_id = twitter_id
        ).first()

        if not twitter_profile:
            twitter_profile = TwitterProfile(
                twitter_id=twitter_id,
                username=username,
                token=oauth_token,
                token_secret=oauth_token_secret
            )
            db.session.add(twitter_profile)
            db.session.commit()

            user = User.query.get(session['user_id'])
            user.twitter_profile = twitter_profile
            db.session.commit()
