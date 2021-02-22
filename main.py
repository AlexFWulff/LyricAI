# Lyrics
from lyricsgenius import Genius
from os import listdir
from os.path import isfile, join
import json
# GPT
from transformers import pipeline, set_seed
# Flask
import flask
from flask import render_template
from flask import Flask
app = Flask(__name__)
# Utils
import random
from time import sleep

########## PARAMS ##########

### Model###
# Base gpt2
#model = "gpt2"
# Works best on RPi (about 500 MB)
#model = "ml6team/gpt-2-small-conditional-quote-generator"
# Works best on good systems (>1 GB)
model = "ml6team/gpt-2-medium-conditional-quote-generator"
# This one is fun
#model = "huggingtweets/realdonaldtrump"

### Song Stuff ###
album_list = {}
album_list["Ray LaMontagne"] = ["Trouble"]
album_list["Sturgill Simpson"] = ["Metamodern Sounds in Country Music"]
album_list["John Mayer"] = ["Continuum"]
album_list["Jason Isbell"] = ["Southeastern", "The Nashville Sound", "Reunions"]
album_list["Bob Dylan"] = ["Blonde on Blonde", "Highway 61 Revisited"]
album_list["Taylor Swift"] = ["Folklore", "Evermore"]

# Download albums?
do_download = False
# Genius API Key
genius_key = "YOUR KEY HERE"

########## Globals ##########
song_list = {}
generator = pipeline('text-generation', model=model)

########## Funcs ##########

def get_song_list(album_list, genius, do_song_update):
    print(do_song_update)
    file_list = []
    
    if do_song_update:
        for artist_name, albums in album_list.items():
            for album_name in albums:
                album = genius.search_album(album_name, artist_name)
                if album == None:
                    print("%s by %s not found!"%(album_name,artist_name))
                    continue

                filename = album_name.replace(" ", "") + ".json"
                album.save_lyrics(filename=filename,overwrite=True,verbose=True)
                file_list.append(filename)
    else:
        for file in listdir("./"):
            if file.endswith(".json"):
                file_list.append(file)

    song_list = []

    for file in file_list:
        with open(file) as f:
            data = json.load(f)
            all_songs = []
            for song in data["tracks"]:
                song["song"]["album"] = data["name"]
                song_list.append(song["song"])

    return song_list

def get_web_content(song_list, generator, in_lines=2, out_lines=2):
    song = random.choice(song_list)
    lyrics = song["lyrics"].splitlines()
    processed_lyrics = []
    # Preprocess Lyrics
    for i in range(0,len(lyrics)):
        lyric = lyrics[i]
        lyric.replace("\n","")

        if not "[" in lyric and lyric != "":
            processed_lyrics.append(lyric)
    
    start = random.randint(0,len(processed_lyrics)-(in_lines+out_lines))
    lyric_in = ""
    for i in range(0, in_lines):
        to_add = processed_lyrics[i+start]
        lyric_in = lyric_in + to_add + "\n"
        
    lyric_out = ""
    for i in range(0, out_lines):
        to_add = processed_lyrics[i+start+in_lines]
        lyric_out = lyric_out + to_add + "\n"

    out_len = int(len(lyric_in+lyric_out)/3)
    
    output = generator(lyric_in, max_length=out_len, num_return_sequences=1)
    ai_out = output[0]["generated_text"][len(lyric_in):]

    # removes final newlines
    lyric_in = lyric_in[:-1]
    lyric_in = lyric_in.replace("\n","<br>")
    lyric_out = lyric_out[:-1]
    lyric_out = lyric_out.replace("\n","<br>")
    ai_out = ai_out.replace("\n", "<br>")

    web_content = {}
    web_content["song_title"] = song["title"]
    web_content["album"] = song["album"]
    web_content["artist"] = song["artist"]
    web_content["lyric_in"] = lyric_in
    web_content["lyric_out"] = lyric_out
    web_content["ai_out"] = ai_out
    return web_content

@app.before_first_request
def create_app():
    global song_list, album_list, do_download, genius_key
    genius = Genius(genius_key)
    song_list = get_song_list(album_list, genius, do_download)

@app.route('/')
@app.route('/index')
def index():
    global song_list, generator
    web_content = get_web_content(song_list, generator, in_lines=2, out_lines=2)
    return render_template("index.html", web_content=web_content)
