#!/usr/bin/env python

from sys import argv, exit
from getopt import getopt
from mpd import MPDClient
from random import randint, shuffle

import re
import socket

optlist, args = getopt(argv[1:], 'ha:g:H:P:')
config = {
    'artist': None,
    'genre': None,
    'mpdhost': 'localhost',
    'mpdport': 6600,
}

def filterFilesList(files):
    """
    If results from the search come from multiple sources, apply the following policy:
    1. Local results have the priority
    2. Followed by results from Google Music
    3. Followed by results from Spotify
    4. Followed by results from Soundcloud
    """

    curPriority = 999
    curSource = None
    priorities = {
        'local': 0,
        'gmusic': 1,
        'spotify': 2,
        'soundcloud': 3,
    }

    for file in files:
        for source, priority in priorities.items():
            if re.match('^%s:.*' % source, file) and priority < curPriority:
                curSource = source
                curPriority = priority

    i = 0
    while i < len(files) and i >= 0:
        if not re.match('^%s:.*' % curSource, files[i]):
            files = files[:i] + files[i+1 :]
        else:
            i += 1

    return files

def find(params):
    global config

    request = 'find'
    for key, value in params.items():
        request += ' %s "%s"' % (key, value.replace('"', '\\"'))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((config['mpdhost'], config['mpdport']))
    sock.sendall(("%s\n" % request).encode())
    response = sock.recv(4096).decode()

    # End-of-message protocol for MPD
    while not re.search('\r?\nOK\r?\n\s*$', response):
        response += sock.recv(4096).decode()

    sock.close()
    response = response.split("\n")
    files = []

    for line in response:
        m = re.match('^file:\s*(.*)$', line)
        if m:
            files.append(m.group(1))

    return filterFilesList(files)

for opt, arg in optlist:
    if opt == '-g':
        config['genre'] = arg
    elif opt == '-a':
        config['artist'] = arg
    elif opt == '-H':
        config['mpdhost'] = arg
    elif opt == '-P':
        config['mpdport'] = arg
    elif opt == '-h':
        print("Usage: python %s [-h] [-a <artist>] [-g <genre>] " + \
            "[-H <mpdhost> (default: localhost)] [-P <mpdport> (default: 6600)]" % argv[0])
        exit(0)

client = MPDClient()
client.connect(config['mpdhost'], config['mpdport'])

if config['genre']:
    albums = client.list('album', 'genre', config['genre'])
elif config['artist']:
    albums = client.list('album', 'artist', config['artist'])
else:
    albums = client.list('album')

shuffle(albums)
randAlbum = albums[0]

artists = client.list('artist', 'album', randAlbum)
if len(artists) > 1:
    artist = artists[randint(0, len(artists)-1)]
else:
    artist = artists[0]

files = find({
    'Artist' : artist,
    'Album'  : randAlbum,
})

client.clear()

for file in files:
    client.add(file)
client.play()
print("Playing \"%s - %s\"" % (artist, randAlbum))

client.close()
client.disconnect()

