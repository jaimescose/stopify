from app import db
import settings


import json
from sqlalchemy.types import JSON
from sqlalchemy.orm.attributes import flag_modified
from flask import session
import requests
from datetime import datetime, date, timedelta
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
    posted_tracks = db.Column(JSON)

    @classmethod
    def get_active_user(cls):
        if 'user_id' in session:
            try:
                return User.query.get(session['user_id'])
            except Exception as e:
                session.clear()
                print(f"Unable to fetch user with active session {session['user_id']}. Error: {e}")

        return None

    def stop_posting_tweets(self):
        self.is_active = False
        db.session.commit()

        session['twitter'] = False

    def get_top_tracks(self, time_range='short_term', limit=4):
        spotify_profile = self.spotify_profile

        sp = SpotifyProfile.auth_user(spotify_profile.refresh_token)

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
                    'id': item['id'],
                    'name': item['name'],
                    'number': item['track_number'],
                    'popularity': item['popularity'],
                    'preview': item['preview_url'],
                    'artist': artist,
                    'image': image,
                    'url': item['external_urls']['spotify']
                }
                
                top_tracks.append(track)

        return top_tracks
    
    def post_track_status(self, allow_check=True):
        allow_post = True
        if allow_check:
            last_post_date = self.last_post_date
            if last_post_date:
                today = date.today()
                previous_date = today - timedelta(days=7)

                if previous_date != self.last_post_date:
                    allow_post = False

        if allow_post:        
            top_tracks = self.get_top_tracks()

            posted_tracks_ids = self.posted_tracks
            if not posted_tracks_ids:
                posted_tracks_ids = []
                track = top_tracks[0]
            else:
                # posted_tracks_ids = json.loads(posted_tracks_ids)
                min_found = 5
                for track_item in top_tracks:
                    if track_item['id'] in posted_tracks_ids:
                        found = posted_tracks_ids.index(track_item['id'])

                        if found < min_found:
                            min_found = found
                            track = track_item
                    else:
                        track = track_item
                        break

            twitter_profile = self.twitter_profile

            credentials = TwitterProfile.get_credentials()
            api = twitter.Api(
                consumer_key=credentials[0], 
                consumer_secret=credentials[1],
                access_token_key=twitter_profile.token,
                access_token_secret=twitter_profile.token_secret
            )

            domain_url = settings.domain_url
            tweet = (f"{track['name']} - {track['artist']}: {track['url']}\n"
            "This is one of my most listened songs on Spotify the last few weeks.\n\n"
            f"Check yours at: {domain_url}")

            try:
                status = api.PostUpdate(tweet)
            except Exception as e:
                print(f'Unable to post status on user {self.id}. Error: {e}')
            else:
                if status:
                    status_url = f'https://twitter.com/{twitter_profile.username}/status/{status.id}'
                    self.last_post_date = date.today()

                    if len(posted_tracks_ids) == 4:
                        posted_tracks_ids.pop(0)
                    posted_tracks_ids.append(track['id'])
                    self.posted_tracks = posted_tracks_ids

                    flag_modified(self, 'posted_tracks')

                    db.session.commit()

                    return status_url

        return None


class SpotifyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
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
        session['twitter'] = False

        twitter_profile = TwitterProfile.query.filter_by(user_id=user.id).first()
        if twitter_profile:
            session['twitter'] = True

        return user


class TwitterProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    twitter_id = db.Column(db.String)
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
        return decrypt_token(self._token_secret, 'twitter')

    @token_secret.setter
    def token_secret(self, value):
        self._token_secret = encrypt_token(value, 'twitter')

    @classmethod
    def get_credentials(cls):
        return settings.twitter['TWITTER_CLIENT_ID'], \
            settings.twitter['TWITTER_CLIENT_SECRET'], \
            settings.twitter['TWITTER_REDIRECT_URI'], \
            settings.twitter['ENCRYPTION_KEY']
    
    @classmethod
    def request_token(cls, authenticate=True):
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

        if authenticate:
            method = 'authenticate'
        else:
            method = 'authorize'
        twitter_endpoint = '/'.join([twitter_api_base, method + '?oauth_token={}'])
        twitter_endpoint = twitter_endpoint.format(oauth_token)

        return twitter_endpoint

    @classmethod
    def process_callback(cls, oauth_token, oauth_verifier) -> User:
        twitter_endpoint = '/'.join([twitter_api_base, 'access_token'])

        data = {
            'oauth_token': oauth_token,
            'oauth_verifier': oauth_verifier
        }

        response = requests.post(twitter_endpoint, params=data)

        oauth_token, oauth_token_secret, twitter_id, username = response.text.split('&')
        oauth_token = oauth_token.split('=')[1]
        oauth_token_secret = oauth_token_secret.split('=')[1]
        twitter_id = str(twitter_id.split('=')[1])
        username = username.split('=')[1]

        twitter_profile = TwitterProfile.query.filter_by(
            twitter_id = twitter_id
        ).first()

        user = User.query.get(session['user_id'])
        if not twitter_profile:
            twitter_profile = TwitterProfile(
                twitter_id=twitter_id,
                username=username,
                token=oauth_token,
                token_secret=oauth_token_secret
            )
            db.session.add(twitter_profile)
            db.session.commit()
            
            user.twitter_profile = twitter_profile
        else:
            twitter_profile.token = oauth_token
            twitter_profile.token_secret = oauth_token_secret
                
        user.is_active = True
        db.session.commit()
        
        session['twitter'] = True

        return user
