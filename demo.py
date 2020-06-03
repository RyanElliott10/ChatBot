#! /usr/bin/env python
#
# Example program using irc.bot.
#
# Joel Rosdahl <joel@rosdahl.net>
# slight modifications by Foaad Khosmood

"""A simple example bot.
This is an example bot that uses the SingleServerIRCBot class from
irc.bot.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
It also responds to DCC CHAT invitations and echos data sent in such
sessions.
The known commands are:
    stats -- Prints some channel information.
    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.
    die -- Let the bot cease to exist.
    dcc -- Let the bot invite you to a DCC CHAT connection.
"""

import random
from typing import Dict, List, Optional, Tuple

import irc.bot
import irc.strings
import lyricsgenius
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr

# I really shouldn't have pushed this, but I frankly don't care enough to fix it. Please, just
# don't do anything nefarious with my Genius token.
genius = lyricsgenius.Genius("yG-J-SmcufDh3ftiSz8UA7aMfiRg_dztK0PVileWreO0ceCNa6KJqTYSdwSTgzkX")


SONGS: List[Dict] = []


class SongArtist(object):

    def __init__(self, **entries):
        self.__dict__.update(entries)


def song_artist_from_utter(utter: str) -> Tuple[str, Optional[SongArtist]]:
    """Finds song with the given utterance, returns random two lines with that utterance along with
    the associated artist and song data."""
    utter = utter.lower()
    try:
        song = genius.search_genius(utter)['hits'][0]
        song_id = song['result']['api_path'].split('/')[-1]
        song = genius.get_song(song_id)['song']
        lyrics = genius._scrape_song_lyrics_from_url(song['url']).lower().split('\n')
        artist_id = song['album']['artist']['id']
        artist = genius.get_artist(artist_id)['artist']

        info = {
            'artist_name': song['album']['artist']['name'],
            'artist_description': artist['description']['plain'],
            'artist_image': artist['image_url'],
            'song_name': song['title'],
            'song_release_date': song['release_date'],
            'song_lyrics': lyrics
        }

        sa = SongArtist(**info)

        match_lines = []
        for i, line in enumerate(lyrics[:-1]):
            if utter in line:
                match_lines.append(' '.join([line, lyrics[i+1]]))

        return random.choice(match_lines), SongArtist(**info)
    except:
        return "That's a pretty unique thing to say, I couldn't even think of any related songs!", None


lyrics = song_artist_from_utter("How you pull up, Baby?")
print(lyrics)


class TestBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def do_command(self, e, cmd):
        nick = e.source.nick
        c = self.connection

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = sorted(chobj.users())
                c.notice(nick, "Users: " + ", ".join(users))
                opers = sorted(chobj.opers())
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = sorted(chobj.voiced())
                c.notice(nick, "Voiced: " + ", ".join(voiced))
        elif cmd == "dcc":
            dcc = self.dcc_listen()
            c.ctcp("DCC", nick, "CHAT chat %s %d" % (
                ip_quad_to_numstr(dcc.localaddress),
                dcc.localport))
        elif cmd == "hello":  # Foaad: change this
            c.privmsg(self.channel, "well double hello to you too!")
        elif cmd == "about":  # Foaad: add your name
            c.privmsg(
                self.channel, "I was made by Dr. Foaad Khosmood for the CPE 466 class in Spring 2016. I was furthere modified by _____")
        elif cmd == "usage":
            # Foaad: change this
            c.privmsg(self.channel, "I can answer questions like this: ....")
        else:
            c.notice(nick, "Not understood: " + cmd)


def main():
    import sys
    if len(sys.argv) != 4:
        print("Usage: testbot <server[:port]> <channel> <nickname>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    bot = TestBot(channel, nickname, server, port)
    bot.start()


if __name__ == "__main__":
    main()
