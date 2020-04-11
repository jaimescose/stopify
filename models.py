from app import db
from sqlalchemy.types import JSON
from flask import session
import requests
from datetime import datetime
import spotipy
import settings
import json

spotify_api_base = 'https://accounts.spotify.com'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    spotify_profile = db.relationship(
        'SpotifyProfile',
        uselist=False
    )

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
    refresh_token = db.Column(db.String, unique=True, nullable=False)
    posted_tracks = db.Column(db.Integer, default=0)
    tracks = db.Column(JSON)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True,
        unique=True
    )

    @classmethod
    def request_token(cls):
        required_scopes = 'user-read-email, user-top-read'
        spotify_endpoint = '/'.join([spotify_api_base, 'authorize?'])

        data = {
            'client_id': settings.spotipy['SPOTIFY_CLIENT_ID'],
            'response_type': 'code',
            'redirect_uri': settings.spotipy['SPOTIFY_REDIRECT_URI'],
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

            data = {
                'grant_type': 'refresh_token',
                'refresh_token': token,
                'client_id': settings.spotipy['SPOTIFY_CLIENT_ID'],
                'client_secret': settings.spotipy['SPOTIFY_CLIENT_SECRET']
            }
            response = requests.post(url=spotify_endpoint, data=data)
            response = response.json()

            token = response.get("access_token")

        return spotipy.Spotify(auth=token)

    @classmethod
    def process_callback(cls, code):
        spotify_endpoint = '/'.join([spotify_api_base, 'api', 'token?'])

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.spotipy['SPOTIFY_REDIRECT_URI'],
            'client_id': settings.spotipy['SPOTIFY_CLIENT_ID'],
            'client_secret': settings.spotipy['SPOTIFY_CLIENT_SECRET']
        }

        response = requests.post(url=spotify_endpoint, data=data)
        response = response.json()
        
        refresh_token = response.get("refresh_token")

        sp = SpotifyProfile.auth_user(refresh_token)
        spotify_user = sp.current_user()

        spotify_profile = SpotifyProfile.query.filter_by(
            email=spotify_user['email']
        ).first()
        user = User.query.get(spotify_profile.user_id)

        if not spotify_profile:
            spotify_profile = SpotifyProfile(
                username=spotify_user['id'],
                email=spotify_user['email'],
                refresh_token=refresh_token
            )
            db.session.add(spotify_profile)
            db.session.commit()

        if not user:
            user = User(spotify_profile=spotify_profile)
            db.session.add(user)
            db.session.commit()

        session['user_id'] = user.id

        return user

    def get_user_top_tracks(self, time_range='short_term', limit=4, force=False):
        if self.posted_tracks % limit == 0 or force:
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
        else:
            top_tracks = json.loads(self.tracks)

        return top_tracks
