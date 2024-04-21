from flask import Flask, render_template, request
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import pandas as pd
import time
import user_secret_data

app = Flask(__name__)

# You need to replace the user_secret_data with your actual API stuff
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_API_KEY = user_secret_data.yt_api_key

SPOTIFY_CLIENT_ID = user_secret_data.sp_client_id
SPOTIFY_CLIENT_SECRET = user_secret_data.sp_client_secret
SPOTIFY_REDIRECT_URI = user_secret_data.sp_redirect_uri
SPOTIFY_SCOPE = 'playlist-modify-public'

def spotify_client():
    auth_manager = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URI, scope=SPOTIFY_SCOPE, open_browser=False)
    return spotipy.Spotify(auth_manager=auth_manager)

def youtube_client():
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)

def extract_playlist_id(url):
    return url.split('list=')[1].split('&')[0]

def get_playlist_items(client, playlist_id):
    request = client.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=playlist_id
    )
    response = request.execute()

    return response['items']

def create_dataset(spotify, playlist_items):
    df = pd.DataFrame(columns=['Input String', 'Song Name', 'Artist'])

    for item in playlist_items:
        video_title = item['snippet']['title']
        results = spotify.search(q=video_title, type='track')
        time.sleep(0.01)

        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            df = pd.concat([df, pd.DataFrame([{'Input String': video_title, 'Song Name': track['name'], 'Artist': track['artists'][0]['name']}])], ignore_index=True)

    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if request.method == 'POST':
        youtube_playlist_url = request.form.get('youtube-link')
        playlist_id = extract_playlist_id(youtube_playlist_url)

        youtube = youtube_client()
        playlist_items = get_playlist_items(youtube, playlist_id)

        spotify = spotify_client()
        user_id = spotify.current_user()['id']
        spotify_playlist = spotify.user_playlist_create(user_id, 'My YouTube Playlist')

        with open('videos.txt', 'w') as file:
            for item in playlist_items:
                video_title = item['snippet']['title']
                channel_name = item['snippet']['channelTitle']
                file.write(f'{video_title} - {channel_name}\n')

        df = create_dataset(spotify, playlist_items)

        for index, row in df.iterrows():
            query = f'{row["Song Name"]} {row["Artist"]}'
            results = spotify.search(q=query, type='track')

            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                spotify.playlist_add_items(spotify_playlist['id'], [track['uri']])
                time.sleep(0.01)

        return 'Playlist created successfully!'
    
@app.route('/spotify/callback')
def spotify_callback():
    code = request.args.get('code')
    spotify = spotify_client()
    token_info = spotify.auth_manager.get_access_token(code)
    return 'Spotify authorized successfully!'

if __name__ == '__main__':
    app.run(debug=True)