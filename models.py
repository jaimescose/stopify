from app import db
from flask import session
import requests
from datetime import datetime
import spotipy
import settings

spotify_api_base = 'https://accounts.spotify.com'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    spotify_profile = db.relationship('SpotifyProfile')


class SpotifyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    refresh_token = db.Column(db.String, unique=True, nullable=False)
    tracks_posted = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    @classmethod
    def request_token(cls):
        if session['spotify_refresh_token']:
            resfresh_token = session['spotify_refresh_token']

            spotify_profile = SpotifyProfile.query.filter_by(refresh_token=resfresh_token).first()

            if spotify_profile:
                return True, spotify_profile

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

        return False, spotify_endpoint

    @classmethod
    def auth_user(cls, token, refresh_token=True) -> spotipy.Spotify:
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
            session['spotify_access_token'] = token

        return spotipy.Spotify(auth=token)

    def get_user_top_tracks(self, time_range='short_term', limit=4):
        sp = SpotifyProfile.auth_user(self.refresh_token)

        results = sp.current_user_top_tracks(
            time_range=time_range, 
            limit=limit
        )

        top_tracks = []
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

        return top_tracks
