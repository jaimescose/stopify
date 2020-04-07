from .auth import auth_user

def get_user_top_tracks(username, time_range='short_term', limit=4):
    sp = auth_user(username)
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

    img1 = top_tracks[0]['image']['url']
    img2 = top_tracks[1]['image']['url']

    # mix_images(img1, img2)

    return top_tracks
