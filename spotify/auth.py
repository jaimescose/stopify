import settings
import spotipy
import spotipy.util as util

def auth_user(username, scope='user-top-read') -> spotipy.Spotify:
    token = util.prompt_for_user_token(
        username=username,
        scope=scope,
        client_id=settings.spotipy['SPOTIFY_CLIENT_ID'],
        client_secret=settings.spotipy['SPOTIFY_CLIENT_SECRET'],
        redirect_uri=settings.spotipy['SPOTIFY_REDIRECT_URI']
    )

    if token:
        return spotipy.Spotify(auth=token)
    
    raise Exception("Can't get token for", username)
