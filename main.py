# Lyrics
from lyricsgenius import Genius
from os import listdir
from os.path import isfile, join
import json
# GPT
from transformers import GPT2Tokenizer, TFGPT2LMHeadModel
# Flask
import flask
from flask import render_template
from flask import Flask
app = Flask(__name__)
# Utils
import random

########## PARAMS ##########

### Model###
# Base gpt2
#model = "gpt2"
# Works best on RPi (about 500 MB)
#model = "ml6team/gpt-2-small-conditional-quote-generator"
model = "/Users/alex/funstuff-local/LyricsTrain/caches/ts-model-1-40-2/tf_model.h5"
# Works best on good systems (>1 GB)
#model = "ml6team/gpt-2-medium-conditional-quote-generator"
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
genius_key = ""

########## Globals ##########
song_list = {}
cache_dir = "/Users/alex/funstuff-local/LyricsTrain/caches/"
tokenizer = GPT2Tokenizer.from_pretrained("distilgpt2", cache_dir=cache_dir)
model = TFGPT2LMHeadModel.from_pretrained(os.path.join(cache_dir, model))

########## Funcs ##########

def get_song_list(album_list, genius, do_song_update):
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

    # add all found songs to a list
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
    # Need to remove lines that aren't actually lyrics
    processed_lyrics = []
    for i in range(0,len(lyrics)):
        lyric = lyrics[i]
        lyric.replace("\n","")

        if not "[" in lyric and lyric != "":
            processed_lyrics.append(lyric)

    # Get random starting location in the selected song and extract lines
    start = random.randint(0,len(processed_lyrics)-(in_lines+out_lines))
    lyric_in = ""
    for i in range(0, in_lines):
        to_add = processed_lyrics[i+start]
        lyric_in = lyric_in + to_add + "\n"
        
    lyric_out = ""
    for i in range(0, out_lines):
        to_add = processed_lyrics[i+start+in_lines]
        lyric_out = lyric_out + to_add + "\n"
    
    # This value for output length seems to work well, but you can adjust it
    out_len = int(len(lyric_in+lyric_out))

    # Actually generate text
    tokenized = tokenizer(lyric_in)
    output = model.generate(
        input_ids=tokenized.input_ids,
        temperature=1,
        do_sample=True,
        max_length=out_len,
        min_length=15)

    ai_out = output[0]["generated_text"][len(lyric_in):]
    
    # removes final newlines and replace \n with <br> for HTML
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

# Executed the first time the website is visited
@app.before_first_request
def create_app():
    global song_list, album_list, do_download, genius_key
    genius = Genius(genius_key)
    song_list = get_song_list(album_list, genius, do_download)

# Executed every time the website is reloaded
@app.route('/')
@app.route('/index')
def index():
    global song_list, generator
    web_content = get_web_content(song_list, generator, in_lines=2, out_lines=2)
    return render_template("index.html", web_content=web_content)
