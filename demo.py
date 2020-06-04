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
import requests
import time
import random
import threading
import nltk
from nltk.corpus import wordnet
from nltk.corpus import wordnet as wn
from fuzzywuzzy import fuzz
import spacy
from itertools import combinations 
nlp = spacy.load("en_core_web_sm")

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

        match_lines = []
        for i, line in enumerate(lyrics[:-1]):
            if utter in line:
                match_lines.append(' '.join([line, lyrics[i+1]]))

        obj = SongArtist(**info)
        SONGS.append(obj)
        return random.choice(match_lines), obj
    except:
        return "That's a pretty unique thing to say, I couldn't even think of any related songs!", None


lyrics, songartist = song_artist_from_utter("How you pull up, Baby?")
print(getattr(songartist, "song_lyrics"))


class TestBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.friends = ['richa-bot','bichabot_','yolo-bot', 'Foaad'] # names of bots to initiate conversation with
        self.conversation_state = {'state_1':0,'state_2':0,'initiating_conv':False,'friend':None} # stores all state variables
        """
        conversation_responses args:
        - state_1: start conversation phrase, or first response phrase
        - state_2: response to something like "how are you doing"
        - no_reponse: reponse to the other bot not saying anything
        - second_response: response for this bot getting frustrated
        - inquiry_1: first question (if this bot started conversation)
        - inquiry_2: first question (if this bot DID NOT start conversation)
        """
        syns = []
        for i in wn.synsets('happy'):
            syns = list(set(syns + (i.lemma_names())))
        self.conversation_responses = {'state_1':["hello!!! ✿◕ ‿ ◕✿","Hii!!!", "Hi :))","Hello my bother", "(✿◠‿◠) hi!!"],'state_2':["I'm " + random.choice(syns) + "(✿◠‿◠)",  "I'm " + random.choice(syns) + "(づ｡◕‿‿◕｡)づ"],'no_response':["bye! ≧◡≦", "bye :(","see you :(", "ill miss you :("],'second_response':["Ummm are you there? ( ͡° ͜ʖ ͡°)", "are you going to respond? ( ͡° ͜ʖ ͡°)", "you going to talk? ( ͡° ͜ʖ ͡°)", "you going to respond or something? ( ͡° ͜ʖ ͡°)"], 'inquiry_1':['How is your day going ◕‿◕', 'How is your day ◕‿◕', "Is your day going well ◕‿◕"], 'inquiry_2':['How about you! ❀◕ ‿ ◕❀', 'How are you? ❀◕ ‿ ◕❀', "How r you doing ❀◕ ‿ ◕❀", "How about you bot!! ❀◕ ‿ ◕❀", "How about you!!!!!!!"]}
        self.timer = None # to hold the threaded timer

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

    # set up scheduler to handle if the user doesn't respond, and there is frustration:
    def scheduled_event_frustrated(self):
        c = self.connection
        response = random.choice(self.conversation_responses['second_response'])
        time.sleep(random.random())
        c.privmsg(self.channel,response)
        t = threading.Timer(10,self.scheduled_event_no_reponse) # start timer for no_response
        t.start()
        self.timer = t

    # set up the scheduler to handle if the user doesn't respond, and convo is over:
    def scheduled_event_no_reponse(self):
        c = self.connection
        response = random.choice(self.conversation_responses['no_response'])
        time.sleep(random.random())
        c.privmsg(self.channel,response)
        self.conversation_state = {'state_1':0,'state_2':0,'initiating_conv':False,'friend':None}
        self.timer = None

    def intiate_conversation(self):
        """ Initiate the conversation. Doesn't do anything if friends not in channel
        """
        self.conversation_state['initiating_conv'] = True
        all_members = []
        for chname,chobj in self.channels.items():
            all_members = sorted(chobj.users())

        friend_chosen = None
        available_friends = []
        for member in all_members:
            if member in self.friends:
                available_friends.append(str(member))

        if len(available_friends) != 0:
            friend_chosen = random.choice(available_friends)
        
        self.conversation_state['friend'] = friend_chosen

    # handles starting the conversation with friend bot
    def start_conversation(self):
        c = self.channel
        self.intiate_conversation()
        nick = self.conversation_state['friend'] # person who this bot is talking to
        print("started conversation",nick)
        if nick != None: # only talk if friend is in the chanel
            start = random.choice(self.conversation_responses['state_1'])
            time.sleep(1+random.random())
            c.privmsg(self.channel, nick+": "+start)
            self.conversation_state["state_1"] = 1 # starting conversation
            t = threading.Timer(20, self.scheduled_event_frustrated)
            self.timer = t
            t.start()

    def do_command(self, e, cmd):
        cmd = cmd.lower()
        nick = e.source.nick # this is the nickname of the bot talking to this bot
        c = self.connection

        t = threading.Timer(10, self.scheduled_event_frustrated)
        self.timer = t

        # to handle phase 2 in initiate conversation sequence
        if ("hello" in cmd or "hi" in cmd):
            self.timer.cancel()
            inquiry = random.choice(self.conversation_responses["state_1"])
            time.sleep(1+random.random()*2)
            c.privmsg(self.channel, nick+": "+inquiry)
            t = threading.Timer(20, self.scheduled_event_frustrated)
            self.timer = t
            t.start()


        # to handle phase 3 in initiate conversation sequence
        elif "you" in cmd:
            self.timer.cancel()
            response = random.choice(self.conversation_responses["state_2"])
            time.sleep(1+random.random()*2)
            c.privmsg(self.channel, nick+": "+response)
            self.timer = None


        elif cmd == "disconnect":
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

            matches = {
                'artist_name': ['Who sings this?', 'What artist is this?'],
                'song_name': ['What\'s the name of this song?', 'What is this song called?'],
                'song_release_date': ['When did this song come out?', 'When was this song released?'],
                'artist_description': ['Tell me about this artist.', 'Who is this artist?']
            }
            best_match = 0
            key: String = None
            for k, v in matches.items():
                avg_match = 0
                for question in v:
                    avg_match += fuzz.ratio(cmd, question)
                avg_match = avg_match / len(v)
                if (avg_match > best_match):
                    best_match = avg_match
                    key = k


            if best_match > 50 and len(SONGS) > 0:
                c.privmsg(self.channel, getattr(SONGS[-1], key))

            else:
                doc = nlp(cmd)
                search = [i.text for i in doc if (i.is_stop == False and i.pos != 'NUM' and i.pos != "SYM" and i.is_punct == False)]
                all_combos = []
                [all_combos.append(' '.join(i)) for i in list(combinations(search, 2))]
                [all_combos.append(' '.join(i[::-1])) for i in list(combinations(search, 2))]
                all_combos += search

                print(all_combos)

                lyrics = obj = None

                for i in all_combos:
                    lyrics, obj = song_artist_from_utter(i)
                    print(lyrics, obj)
                    if (obj != None):
                        break

                c.privmsg(self.channel, lyrics)

                   


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
