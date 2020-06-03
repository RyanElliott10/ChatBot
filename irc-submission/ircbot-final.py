# Nate Andre

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

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
import requests
import time
import random
import threading
import nltk
from nltk.corpus import wordnet
from nltk.corpus import wordnet as wn


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

    def on_pubmsg(self, c, e): # handles the parsing of all public messaging to determine if 
        bot_nickname = self.connection.get_nickname() # this bot's nickname
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(bot_nickname): # message directed to us
            self.do_command(e, a[1].strip()) # this is what handles the reponse to the the query
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
        nick = self.conversation_state['friend']
        c.privmsg(self.channel,nick+": "+response)
        t = threading.Timer(3,self.scheduled_event_no_reponse) # start timer for no_response
        t.start()
        self.timer = t

    # set up the scheduler to handle if the user doesn't respond, and convo is over:
    def scheduled_event_no_reponse(self):
        c = self.connection
        response = random.choice(self.conversation_responses['no_response'])
        time.sleep(random.random())
        nick = self.conversation_state['friend']
        c.privmsg(self.channel,nick+": "+response)
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
            t = threading.Timer(5, self.scheduled_event_frustrated)
            self.timer = t
            t.start()

    def do_command(self, e, cmd):
        cmd = cmd.lower()
        nick = e.source.nick # this is the nickname of the bot talking to this bot
        c = self.connection

        # starts the initiate conversation sequence (phase 1)
        if "start conversation" in cmd:
            """ initiate the conversation
            """
            self.intiate_conversation()
            nick = self.conversation_state['friend'] # person who this bot is talking to
            print("started conversation",nick)
            if nick != None: # only talk if friend is in the chanel
                start = random.choice(self.conversation_responses['state_1'])
                time.sleep(1+random.random())
                c.privmsg(self.channel, nick+": "+start)
                self.conversation_state["state_1"] = 1 # starting conversation
                t = threading.Timer(5, self.scheduled_event_frustrated)
                self.timer = t
                t.start()


        # to handle phase 2 in initiate conversation sequence
        elif ("hello" in cmd or "hi" in cmd) and self.conversation_state['state_1'] == 1 and self.conversation_state['state_2'] == 0 and self.conversation_state['initiating_conv'] == True:
            if nick == self.conversation_state['friend']: # talking to the same person
                print("second part of initiated conversation")
                self.timer.cancel()
                inquiry = random.choice(self.conversation_responses["inquiry_1"])
                time.sleep(1+random.random()*2)
                c.privmsg(self.channel, nick+": "+inquiry)
                self.conversation_state["state_2"] = 1
                t = threading.Timer(5, self.scheduled_event_frustrated)
                self.timer = t
                t.start()


        # to handle phase 3 in initiate conversation sequence
        elif "you" in cmd and self.conversation_state['state_1'] == 1 and self.conversation_state['state_2'] == 1 and self.conversation_state['initiating_conv'] == True:
            if nick == self.conversation_state['friend']: # talking to same person
                print("third part of initiated conversation")
                self.timer.cancel()
                response = random.choice(self.conversation_responses["state_2"])
                time.sleep(1+random.random()*2)
                c.privmsg(self.channel, nick+": "+response)
                self.conversation_state = {'state_1':0,'state_2':0,'initiating_conv':False,'friend':None}
                self.timer = None


        # start of the converation, when this bot is the responder
        elif ("hello" in cmd or "hi" in cmd) and self.conversation_state['state_1'] == 0 and self.conversation_state['state_2'] == 0 and self.conversation_state['initiating_conv'] == False:
            print("got to the part 1")
            self.conversation_state['friend'] = nick
            self.conversation_state["state_1"] = 1 # boolean to symbolize state 1 received
            response = random.choice(self.conversation_responses["state_1"])
            time.sleep(1+random.random()*2)
            c.privmsg(self.channel, nick+": "+response)
            t = threading.Timer(5, self.scheduled_event_no_reponse)
            self.timer = t
            t.start()


        # last part of the conversation when this bot is the responder
        elif "you" in cmd and self.conversation_state['state_1'] == 1 and self.conversation_state['state_2'] == 0 and self.conversation_state['initiating_conv'] == False:
            print("got to the part 2")
            self.timer.cancel()
            inquiry = random.choice(self.conversation_responses['inquiry_2'])
            self.conversation_state["state_2"] = 1
            response = random.choice(self.conversation_responses["state_2"])
            time.sleep(1+random.random()*2)
            c.privmsg(self.channel, nick+": "+response)
            time.sleep(1+random.random()*2)
            c.privmsg(self.channel, nick+": "+inquiry)
            t = threading.Timer(5, self.scheduled_event_frustrated)
            self.timer = t
            t.start()


        # when the end of the conversation is seen, when this bot is the responder
        elif self.conversation_state['state_1'] == 1 and self.conversation_state['state_2'] == 1 and self.conversation_state['initiating_conv'] == False:
            print("got to the part 3")
            self.timer.cancel()
            self.timer = None
            self.conversation_state = {'state_1':0,'state_2':0,'initiating_conv':False,'friend':None}


        elif cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "forget": # remove all state variables
            self.conversation_state = {'state_1':0,'state_2':0,'initiating_conv':False,'friend':None}
            if self.timer != None: # cancel any queued events
                self.timer.cancel()
                self.timer = None
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
        elif cmd == "about":
            c.privmsg(self.channel, "I was made by Dr. Foaad Khosmood for the CPE 466 class in Spring 2016. I was further modified by Nate Andre")


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
