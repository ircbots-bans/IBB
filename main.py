import zirc, ssl
import threading
import requests
from time import sleep

mainChannel = "##ircbots-bans"
banFile = "https://raw.githubusercontent.com/ircbots-bans/ircbots-bans/master/bans.md"
exemptFile = "https://raw.githubusercontent.com/ircbots-bans/ircbots-bans/master/exempts.md"
refreshRate = 30 # 300

class Bot(zirc.Client):
    def __init__(self):
        self.connection = zirc.Socket(wrapper=ssl.wrap_socket)
        self.config = zirc.IRCConfig(host="irc.freenode.net", 
            port=6697,
            nickname="IBB",
            ident="bot",
            realname="IRC Bot Bans",
            channels=[mainChannel],
            sasl_user="IBB",
            sasl_pass="123456789") # ^_^
        self.connect(self.config)
        
        self.sync = False
        
        self.start()
        
    def on_mode(self, event):
        if event.target == mainChannel:
            raw = event.raw.split()
            mode = event.arguments[0]
            affected = event.arguments[1]
            
            if event.arguments == ["+o", self.config["nickname"]]:
                self.bans = []
                self.exempts = []
            
                self.syncChannel()
            
            if mode == "+e":
                self.exempts.append(raw[4])

            elif mode == "-e":
                self.exempts.remove(raw[4])
                
            elif mode == "+b":
                self.bans.append(raw[4])
                
            elif mode == "-b":
                self.bans.remove(raw[4])

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
                self.checkBanHash()

    def syncChannel(self):
        if not self.sync:
            self.sync = True
            self.syncedExempts = False
            self.syncedBans = False
            
            self.send("MODE " + mainChannel + " b")
            self.send("MODE " + mainChannel + " e")
            #You can also use: (less bandwidth :p)
            #self.send("MODE " + mainChannel + " be")
        
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
                item[0] = " ".join(item[0].split(" ")[1:])
                exempts.append(self.banType(item))
                
            else:
                bans.append(self.banType(item))
                
        removeExempts = []
        ammendExempts = []
        removeBans = []        
        ammendBans = []
        
        for iteration, ban in enumerate(bans): # git
            if not ban in self.bans:
                ammendBans.append(ban)
        
            elif self.bans[iteration] not in bans:
                removeBans.append(self.bans[iteration])
                
        for iteration, exempt in enumerate(exempts): # git
            if not exempt in self.exempts:
                ammendExempts.append(exempts)
        
            elif self.exempts[iteration] not in exempts:
                removeExempts.append(self.exempts[iteration])
                
        #if removeBans or ammendBans:
         #   self.privmsg(mainChannel, "{0} bans need to be added and {1} bans need to be removed"
          #      .format(str(len(ammendBans)), str(len(removeBans)))
           # )
            
        #if removeExempts or ammendExempts:
         #   self.privmsg(mainChannel, "{0} exempts need to be added and {1} exempts need to be removed"
          #      .format(str(len(ammendExempts)), str(len(removeExempts)))
           # )
           
        for ban in ammendBans:
            self.send("MODE " + mainChannel + " +b " + str(ban))
            
        for ban in removeBans:
            self.send("MODE " + mainChannel + " -b " + str(ban))
              
        for exempt in ammendExempts:
            self.send("MODE " + mainChannel + " +e " + str(exempt))
            
        for exempt in removeExempts:
            self.send("MODE " + mainChannel + " -e " + str(exempt))
            
    def checkBanHash(self):
        """
            Checks if the GitHub ban file is different to the banlist of
            given channel

        """
        while True:
            banData = requests.get(banFile).text
            exemptData = requests.get(exemptFile).text
            self.GitHubData = self.parseBanFile(banData, exemptData)       
            
            self.applyChanges()
            
            sleep(refreshRate)
Bot()