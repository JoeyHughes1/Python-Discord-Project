import os
import discord
import random
from pymongo import MongoClient
from numpy import transpose


// I tried my best to get a for loop to work but there was some obscure error that stopped it from working
// so I had to do this
def boardString(board):
    response = ""
    response += "   ".join(list(map(str, board[0]))) + '\n'
    response += "   ".join(list(map(str, board[1]))) + '\n'
    response += "   ".join(list(map(str, board[2]))) + '\n'
    response += "   ".join(list(map(str, board[3]))) + '\n'
    response += "   ".join(list(map(str, board[4]))) + '\n'
    response += "   ".join(list(map(str, board[5]))) + '\n'
    return response.replace('0', ':white_circle:').replace('1', ':red_circle:').replace('2', ':yellow_circle:')


TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
client = discord.Client(intents=intents)

cluster = MongoClient(os.getenv('CONNECTION_URL'))
db = cluster['DiscordBotDB']
collection = db['Scores']
challenge = db['Challenges']
games = db['Games']


# bot = commands.Bot(command_prefix='=')


@client.event
async def on_message(message):
    if message.content.startswith('=c4'):
        args = message.content.split(' ')
        command = args[1]
        targetName = ""
        if len(args) >= 3:
            if args[2].startswith('\"'):
                for i in range(3, len(args)):
                    args[2] += " " + args[i]
                args[2] = args[2].replace('"', '')
            targetName = args[2]
        if command == 'challenge':
            if games.count_documents({'playerOne': message.author.id}) == 1 or games.count_documents(
                    {'playerTwo': message.author.id}) == 1:
                await message.channel.send(
                    'You cannot challenge, you are currently in a game! See your current game with "=c4 board"')
                return
            if challenge.count_documents({'challenger': message.author.id}) != 0:
                await message.channel.send(
                    "You have already sent a challenge. Please wait for it to be accepted or retract your challenge"
                    " with =c4 retract.")
                return
            count = 0
            target = message.author
            for mem in message.guild.members:
                if mem.name.lower() == targetName.lower() and count == 0 \
                        and targetName.lower() != message.author.name.lower():
                    count = 1
                    target = mem
                elif mem.name == targetName and count == 1:
                    await message.channel.send(
                        'Cannot challenge that person as there are multiple people with that name.')
                    return
            if count == 1:
                post = {"challenger": message.author.id, "target": target.id}
                challenge.insert_one(post)
                await message.channel.send(
                    f'You have sent a challenge to {target}, they must type "=c4 accept '
                    f'{message.author.name}" to accept your challenge.')
            elif count == 0:
                await message.channel.send(
                    'I could not find a person with that name in this channel. '
                    'Make sure you are not @ mentioning the person, just typing their username. '
                    'Also make sure you are not challenging yourself.')
        if command == 'accept':
            if games.count_documents({'playerOne': message.author.id}) == 1 or games.count_documents(
                    {'playerTwo': message.author.id}) == 1:
                await message.channel.send(
                    'You cannot accept, you are currently in a game! '
                    'See your current game with "=c4 board", or abandon the game with "=c4 abandon".')
                return
            if challenge.count_documents(
                    {'target': message.author.id}) == 0:  # If there are no challenges with the sender as the target
                await message.channel.send('You have no pending challenges.')
            else:  # if the sender has challenges
                target = message.author
                for mem in message.guild.members:
                    if mem.name.lower() == targetName.lower():
                        target = mem
                if target == message.author:  # If there is no match for the name and people in the channel
                    await message.channel.send(
                        'I could not find that person in this channel. Make sure you typed their name correctly')
                else:
                    query = {'challenger': target.id, 'target': message.author.id}
                    if challenge.count_documents(query) == 0:  # If there are no targets from the person in the channel
                        await message.channel.send('You have no challenges from that person.')
                    else:  # If there is a challenge, accept it.
                        challenge.find_one_and_delete(query)
                        games.insert_one(
                            {'playerOne': target.id, 'playerTwo': message.author.id,
                             'turnNumber': random.choice([1, 2]),
                             'board': [[0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0],
                                       [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]})
                        await message.channel.send('Accepted!')
                        await message.channel.send(
                            'The current board looks like this:\n0,0,0,0,0,0,0\n0,0,0,0,0,0,0\n0,0,0,0,0,0,0\n0,0,0,'
                            '0,0,0,0\n0,0,0,0,0,0,0\n0,0,0,0,0,0,0\n '.replace('0', ":white_circle:").replace(',',
                                                                                                              '   '))
                        if games.find_one({'playerTwo': message.author.id})['turnNumber'] != 1:
                            await message.channel.send(
                                'By random choice you get the first turn. You have the :yellow_circle: pieces Take '
                                'turns with "=c4 drop [column number 1-7]". Have fun!')
                        else:
                            await message.channel.send(
                                'By random choice your opponent gets the first turn. You have the :yellow_circle: '
                                'pieces. Take turns with "=c4 drop [column number]". Have fun!')
        if command == 'board':
            if games.count_documents({'playerOne': message.author.id}) == 0 and games.count_documents(
                    {'playerTwo': message.author.id}) == 0:
                await message.channel.send(
                    'You are not in a game right now. Send a challenge (=c4 challenge [username])'
                    ' or accept a challenge (=c4 accept [username]) to start a game.')
                return

            if games.count_documents({'playerOne': message.author.id}) == 1:  # if the caller is player one
                # we take the transpose of the board because writing the board is the opposite of how it is stored
                board = transpose(games.find_one({'playerOne': message.author.id})['board'])
                game = games.find_one({'playerOne': message.author.id})
                if game['turnNumber'] == 1:
                    response = f"{message.author.name}: :red_circle:  (<-- current turn) \n" \
                               f"{client.get_user(game['playerTwo']).name}: :yellow_circle:"
                else:
                    response = f"{message.author.name}: :red_circle: \n" \
                               f"{client.get_user(game['playerTwo']).name}: :yellow_circle: (<-- current turn)"
            else:  # if the caller is player two
                board = transpose(games.find_one({'playerTwo': message.author.id})['board'])
                game = games.find_one({'playerTwo': message.author.id})
                if game['turnNumber'] == 2:
                    response = f"{client.get_user(game['playerOne']).name}: :red_circle: \n" \
                               f"{message.author.name}: :yellow_circle: (<-- current turn)"
                else:
                    response = f"{client.get_user(game['playerOne']).name}: :red_circle: (<-- current turn) \n" \
                               f"{message.author.name}: :yellow_circle: "

            await message.channel.send("The current board looks like this:\n" + boardString(
                board) + "\n" + response + '\nTake turns with "=c4 drop [column number 1-7]"')
        if command == 'retract':
            await message.channel.send(
                f'your challenge against '
                f'{client.get_user(challenge.find_one({"challenger": message.author.id})["target"])} was cancelled')
            challenge.find_one_and_delete({'challenger': message.author.id})
        if command == 'drop':
            if games.count_documents({'playerOne': message.author.id}) == 0 and games.count_documents(
                    {'playerTwo': message.author.id}) == 0:
                await message.channel.send(
                    'You are not in a game right now. Send a challenge (=c4 challenge [username])'
                    ' or accept a challenge (=c4 accept [username]) to start a game.')
                return

            if games.count_documents({'playerOne': message.author.id}) == 1:
                game = games.find_one({'playerOne': message.author.id})
                player = 'playerOne'
                response = f"{message.author.name}: :red_circle: \n" \
                           f"{client.get_user(game['playerTwo']).name}: :yellow_circle: (<-- current turn)"
                if game['turnNumber'] == 2:
                    await message.channel.send(
                        "It's not your turn, feel free to harass your opponent until they play a move")
                    return
            else:
                game = games.find_one({'playerTwo': message.author.id})
                player = 'playerTwo'
                response = f"{client.get_user(game['playerOne']).name}: :red_circle: (<-- current turn) \n" \
                           f"{message.author.name}: :yellow_circle:"
                if game['turnNumber'] == 1:
                    await message.channel.send(
                        "It's not your turn, feel free to harass your opponent until they play a move")
                    return
            for i in range(5, -1, -1):
                if game['board'][int(targetName) - 1][i] == 0:
                    game['board'][int(targetName) - 1][i] = game['turnNumber']
                    games.find_one_and_update({player: message.author.id}, {'$set': {'board': game['board']}})

                    # Win Checking
                    lines = [[], [], [], []]  # an array holding the cardinal directions  through the most recent drop.
                    # The following generate lines by, for the diagonals, going up left or up right until you hit
                    # the edge, then going down right or down left until it hits the edge, recording the values along
                    # the way. then it records the column and row.
                    # It then runs through those arrays and records sequences of the number just played. If this
                    # sequence reaches 4, then its a connect 4 and whoever just went wins.
                    lowerlimit = 0  # used to transfer between for loops the edge of the range for the diagonals
                    # (i.e. the second to last circle on the right at the bottom would reach only 1 for the upper right
                    # lowerlimit, because you can only go up right once before you reach the edge.
                    for j in range(1, 4, 1):  # up left
                        if (int(targetName) - 1 - j) in range(0, 7) and (i - j) in range(0, 6):
                            lowerlimit = j
                        else:
                            break
                    for j in range(lowerlimit, -4, -1):  # down right and recording
                        if (int(targetName) - 1 - j) in range(0, 7) and (i - j) in range(0, 6):
                            lines[0].append(game['board'][int(targetName) - 1 - j][i - j])
                        else:
                            break
                    lowerlimit = 0  # resetting lower limit
                    for j in range(1, 4, 1):  # up right
                        if (int(targetName) - 1 + j) in range(0, 7) and (i - j) in range(0, 6):
                            lowerlimit = j
                        else:
                            break
                    for j in range(lowerlimit, -4, -1):  # down left and recording
                        if (int(targetName) - 1 + j) in range(0, 7) and (i - j) in range(0, 6):
                            lines[1].append(game['board'][int(targetName) - 1 + j][i - j])
                        else:
                            break
                    lines[2] = game['board'][int(targetName) - 1]  # column
                    for j in range(len(game['board'])):  # row
                        lines[3].append(game['board'][j][i])
                    for j in range(len(lines)):  # searching through the arrays for a sequence of four numbers
                        connect = 0
                        if len(lines[j]) >= 4:
                            for k in range(len(lines[j])):
                                if lines[j][k] == game['turnNumber']:
                                    connect += 1
                                    if connect == 4:  # If you have a connect four
                                        await message.channel.send(
                                            f'YOU JUST WON!! Good job!\nThe winning board looks like this:\n'
                                            f'{boardString(transpose(game["board"]))}'
                                            f'Congratulations, {message.author.name}!')
                                        games.find_one_and_delete({player: message.author.id})
                                        return
                                else:
                                    connect = 0

                    if game['turnNumber'] == 1:
                        games.find_one_and_update({player: message.author.id}, {'$set': {'turnNumber': 2}})
                    else:
                        games.find_one_and_update({player: message.author.id}, {'$set': {'turnNumber': 1}})
                    break
                elif i == 0:
                    await message.channel.send("That column is full, please pick another one.")
                    return
            await message.channel.send(
                "Your move was made, now the board looks like this:\n" + boardString(
                    transpose(game['board'])) + "\n" + response, delete_after=60)
            await message.channel.send('You can see the current board with "=c4 board"', delete_after=120)
        if command == 'abandon':
            if games.count_documents({'playerOne': message.author.id}) == 0 and games.count_documents(
                    {'playerTwo': message.author.id}) == 0:
                await message.channel.send(
                    'You are not in a game right now. '
                    'Feel free to send a challenge or accept a challenge to start a game.')
                return
            if games.count_documents({'playerOne': message.author.id}) == 0:
                games.find_one_and_delete({'playerTwo': message.author.id})
            else:
                games.find_one_and_delete({'playerOne': message.author.id})
            await message.channel.send('Game abandoned. Send a challenge or accept a challenge to begin a new one.')
        if command == 'mychallenges':
            response = ''  # This will hold the list of names of challengers
            for x in challenge.find({"target": message.author.id}):
                response += client.get_user(x['challenger']).name + ", "
            await message.channel.send(
                f'You have challenges from {challenge.count_documents({"target": message.author.id})} user(s):'
                f' {response}')


@client.event  # when the bot is ready to be used
async def on_ready():
    print('Connected and ready')


client.run(TOKEN)
