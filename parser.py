argmodes = {"set": "bqeIkfljov", "unset": "bqeIkov"}

def split_modes(modes):
    splitmodes = []
    argscount = 1
    setmode = True
    for mode in modes[0]:
        if mode == "+":
            setmode = True
            continue
        elif mode == "-":
            setmode = False
            continue
        if setmode:
            if mode in argmodes["set"]:
                modearg = modes[argscount]
                argscount += 1
                splitmodes.append("+{} {}".format(mode, modearg))
            else:
                splitmodes.append("+{}".format(mode))
        else:
            if mode in argmodes["unset"]:
                modearg = modes[argscount]
                argscount += 1
                splitmodes.append("-{} {}".format(mode, modearg))
            else:
                splitmodes.append("-{}".format(mode))

    return splitmodes

def unsplit_modes(modes):
    unsplitmodes = [""]
    finalmodes = []
    argscount = 0
    setmode = True
    for mode in modes:
        if mode.startswith("+"):
            if len(unsplitmodes[0]) == 0:
                unsplitmodes[0] = "+"
            elif not setmode:
                unsplitmodes[0] += "+"
            setmode = True
        elif mode.startswith("-"):
            if len(unsplitmodes[0]) == 0:
                unsplitmodes[0] = "-"
            elif setmode:
                unsplitmodes[0] += "-"
            setmode = False
        mode = mode.lstrip("+-")
        mode = mode.split()
        unsplitmodes[0] += mode[0]
        if len(mode) > 1:
            unsplitmodes.append(mode[1])
            argscount += 1
            if argscount == 4:
                finalmodes.append(" ".join(unsplitmodes))
                unsplitmodes = [""]
                argscount = 0
    
    if unsplitmodes != [""]:
        finalmodes.append(" ".join(unsplitmodes))
    
    return finalmodes