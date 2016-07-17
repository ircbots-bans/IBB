import zirc, ssl
import parser
import threading
import requests
from time import sleep, time
from fnmatch import fnmatch
import repl

mainChannel = "##ircbots-bans"
banFile = "https://raw.githubusercontent.com/ircbots-bans/ircbots-bans/master/bans.md"
exemptFile = "https://raw.githubusercontent.com/ircbots-bans/ircbots-bans/master/exempts.md"
refreshRate = 60 # 20 # 300

class Bot(zirc.Client):
    def __init__(self):
        self.connection = zirc.Socket(wrapper=ssl.wrap_socket)
        self.config = zirc.IRCConfig(host="irc.freenode.net", 
            port=6697,
            nickname="IBB",
            ident="ibb",
            realname="Utility bot for ##ircbots-bans",
            channels=[mainChannel],
            sasl_user="IBB",
            sasl_pass="") # ^_^
        self.connect(self.config)
        
        self.sync = False
        
        self.admins = ["*!*@zirc/dev/zz"]
        
        self.start()
        
    def on_mode(self, event):
        if event.target == mainChannel:
            raw = event.raw.split()
            mode = event.arguments[0]
            affected = event.arguments[1]
            
            if event.arguments == ["+o", self.config["nickname"]]:
                self.GitHubData = []
                self.bans = []
                self.exempts = []
            
                self.syncChannel()
            
            else:
                parsedModes = parser.split_modes(raw[3:])
                
                for item in parsedModes:
                    item = item.split()
                    
                    if item[0] == "+b" and item[1] not in self.bans:
                        self.bans.append(item[1])
                    
                    elif item[0] == "-b" and item[1] in self.bans:
                        self.bans.remove(item[1])
                        
                    if item[0] == "+e" and item[1] not in self.exempts:
                        self.exempts.append(item[1])
                    
                    elif item[0] == "-e" and item[1] in self.exempts:
                        self.exempts.remove(item[1])
                
            self.applyChanges()
            
    def on_all(self, event):
        message = event.raw.split()
        
        if self.sync:
            if event.type == "367":
                self.bans.append(message[4])
            
            elif event.type == "368":
                self.syncedBans = True
            
            elif event.type == "348":
                self.exempts.append(message[4])
            
            elif event.type == "349":
                self.syncedExempts = True
            
            if self.syncedBans and self.syncedExempts:
                self.sync = False
                checkThread = threading.Thread(target=self.checkBanHash)
                checkThread.setDaemon(True)
                checkThread.start()
                
    def syncChannel(self):
        if not self.sync:
            self.sync = True
            self.syncedExempts = False
            self.syncedBans = False
            
            self.send("MODE " + mainChannel + " be")
        
    def parseBanFile(self, banData, exemptData): #does this need to be part of Bot(zirc.Client) ? no
        banData = banData.split("\n")[2:]  # Skip two first unneeded lines
        banData.pop(-1) # Remove last empty item
        exemptData = exemptData.split("\n")[2:]
        exemptData.pop(-1)

        GitHubBans = []
        for item in banData:
            GitHubBans.append(item.split(" | "))
        
        for item in exemptData:
            item = item.split(" | ")
            item[0] = "exempt " + item[0]
            GitHubBans.append(item)
        
        return GitHubBans
        
    def banType(self, item):
        if item[0] == "banmask":
            return item[1].replace("\\", "")
            
        elif item[0] == "chan link":
            return "$j:" + item[1].replace("\\", "")
            
        elif item[0] == "realname":
            return "$r:" + item[1].replace("\\", "")
            
        elif item[0] == "account":
             return "$a:" + item[1].replace("\\", "")
             
        elif item[0] == "ext_banmask":
            return "$x:" + item[1].replace("\\", "")
        
    def applyChanges(self):
        bans = []
        exempts = []
        
        for item in self.GitHubData:
            if item[0].split(" ")[0] == "exempt":
                _item = [" ".join(item[0].split(" ")[1:])]+item[1:]
                exempts.append(self.banType(_item))
                
            else:
                bans.append(self.banType(item))
                
        modes = []
        
        for iteration, ban in enumerate(bans): # git
            if not ban in self.bans:
                modes.append("+b " + ban)
        
        for iteration, ban in enumerate(self.bans): #local
            if (iteration + 1) <= len(self.bans) and self.bans[iteration] not in bans:
                modes.insert(0, "-b " + self.bans[iteration]) # We should remove bans in first for some race conditions
                
        for iteration, exempt in enumerate(exempts): # git
            if not exempt in self.exempts:
                modes.append("+e " + exempt)
        
        for iteration, exempt in enumerate(self.exempts): # local
            if (iteration + 1) <= len(self.exempts) and self.exempts[iteration] not in exempts:
                modes.insert(0, "-e " + self.exempts[iteration]) # Same as above

        #self.privmsg(mainChannel, "A " + str(modes))
        parsedModes = parser.unsplit_modes(modes)
        #self.privmsg(mainChannel, "B " + str(parsedModes))
            
        if parsedModes:
            self.send("MODE " + mainChannel + " " + parsedModes[0])
        
        return
            
    def checkBanHash(self):
        """
            Checks if the GitHub ban file is different to the banlist of
            given channel

        """
        while True:
            banData = requests.get(banFile + "?" + str(time())).text
            exemptData = requests.get(exemptFile + "?" + str(time())).text
            self.GitHubData = self.parseBanFile(banData, exemptData)       
            
            self.applyChanges()
            
            sleep(refreshRate)
    def on_privmsg(bot,irc,event):
        if " ".join(event.arguments).startswith("!>>"):
            for admin in bot.admins:
                if fnmatch(event.source, admin):
                    output = repl.Repl({"bot": bot, "irc": irc, "event": event}).run(" ".join(event.arguments).replace("!>> ", "", 1))
                    for line in output.split("\n"):
                        irc.reply(event, line)
                    break
Bot()