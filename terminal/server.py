import socket
from threading import Thread
import os
from time import sleep
import json

ALPHABET = [chr(i) for i in range(33, 97)]
for i in range(97, 123):
    ALPHABET.append(chr(i))

def crypt(password, step=27):
    result = ""
    for elem in password:
        i = ALPHABET.index(elem) + step
        if i > len(ALPHABET) - 1: i -= len(ALPHABET)
        result += ALPHABET[i]
    return result

def decrypt(password, step=27):
    result = ""
    for elem in password:
        i = ALPHABET.index(elem) - step
        if i > len(ALPHABET) - 1: i -= len(ALPHABET)
        result += ALPHABET[i]
    return result

def check_password(password):
    if set(password) < set(ALPHABET): return False
    return True

# The main class of server
class Server:
    __connections = [] # an array with all connections (object of users)
    version = "1.0.10" # release, beta, alpha
    updating = False # flag for updating. if user just input [UPDATE] OK 200 {User.version} and updating is false nothing happens
    def __init__(self, ip="localhost", port=9090, max_users=10_000):
        self.server = socket.socket() # create object of socket
        self.server.bind((ip, port)) # our window is ip and port (localhost and 9090 by default)
        self.server.listen(max_users) # max users (pls, don't do bigger than 10_000
        Thread(target=self.check_connection, daemon=True).start() # start wait connections
        Thread(target=self.checking_version, daemon=True).start() # start check version each 256 second
        print("Server is started.") # notification to administrator

    # nicknames are unique, we need to check that nick that user inputs isn't already used
    @staticmethod
    def check_nickname(nick):
        for user in Server.__connections:
            if user.nickname == nick: return False  # Nickname is already used
        return True  # Nickname is valid

    def check_client(self, user):
        with open("clients.json", 'r') as f:
            data = json.load(f)
            for nick in data.keys():
                if nick == user.nickname:
                    return False
            return True

    def add_new_client(self, user):
        with open("clients.json", 'r') as f:
            data = json.load(f)
            data[user.nickname] = user.password
        with open("clients.json", 'w') as f:
            pass

    # waiting for connection
    def check_connection(self):
        while True:
            conn, addr = self.server.accept() # waiting for connection
            nick = conn.recv(1024).decode() # first message of user is his nickname
            if Server.check_nickname(nick): # check this nickname
                conn.send("You successfully connected! Input '/help' to get information about commands.".encode())

                # after that we need to check version of client
                if self.check_version(conn):
                    new_user = User(conn, addr, nick) # create new object of user
                    # client_version = conn.recv(1024).decode() # get version of client from user
                    # if client_version != User.version:
                    #     filesize = os.path.getsize(f'client {User.version}.py')
                    #     conn.send(f"You need to update your client. Press any key to do this, or '/exit' to abort operation. {filesize} {User.version}".encode())
                    #     answer = conn.recv(1024).decode()
                    #     if answer != "/exit":
                    #         self.send_client(conn)
                    #         conn.close()
                    #     else:
                    #         conn.close()
                    # else:
                    #     conn.send(b"OK 200")
                    print(f"{addr} | {nick} connected.")  # notification for administrator
                    Server.__connections.append(new_user)  # add to connections object of new user
                    Thread(target=self.check_message, args=(new_user,), daemon=True).start() # we need to check message from user
                else:
                    conn.close()
            else: # nickname is already used
                conn.send("Nickname is already used. Try again.".encode())
                conn.close()

    # we need to check version of client each 2**10 second
    def checking_version(self):
        while True:
            sleep(2**10)
            if f"client {User.version}" not in os.listdir():
                Server.updating = True
                User.version = get_user_version() # update version for the server
                self.send_bytes(None, f"[UPDATE] There is a new version of chat! Would you like to download it?: {self.get_client_file_size()} {User.version}".encode())
            else:
                Server.updating = False

    # check version for the one client
    def check_version(self, user):
        User.version = get_user_version() # update version for the server
        client_version = user.recv(1024).decode('utf-8')
        if client_version == User.version:
            user.send(b"OK")
            return True
        else:
            user.send(f"[UPDATE] There is a new version of chat! Would you like to download it?: {self.get_client_file_size()} {User.version}".encode())
            answer = user.recv(1024).decode('utf-8')

            if answer == "y":
                self.send_client(user)
                return False # we don't need to connect this user, because his client will be restarted
                # and he will use old nickname. So, we don't need to add this user to connections for now
            else:
                return False


    def get_client_file_size(self):
        for file in os.listdir():
            if file.split()[0] == "client":
                return os.path.getsize(file)

    # check message from each user
    def check_message(self, user):
        while True:
            data = user.conn.recv(1024)
            decode_data = data.decode().split()

            match decode_data[0].lower():
                case "/exit": # user wants to leave
                    print(f"{user.addr} | {user.nickname}", " disconnected") # information for the server
                    self.send_message(user, " disconnected")
                    user.conn.close()
                    Server.__connections.pop(Server.__connections.index(user))
                    break
                case "/members": self.send_members(user) # information about all users
                case "/pm": self.send_private_message(user, decode_data[1], decode_data[2:]) # private message
                case "/transfer": self.send_file(user, " ".join(decode_data[1:-1]), int(decode_data[-1])) # file
                case "[update]":
                    User.version = get_user_version()
                    if data.decode() == f"[UPDATE] OK 200 {User.version}" and Server.updating:
                        self.send_client(user.conn)
                    else:
                        user.conn.send("[BREAK]".encode()) # stop the

                case _: self.send_message(user, f": {" ".join(decode_data)}") # just the message

    # send text message (data) to every user except <user>
    def send_message(self, user, data): # we get normal data. In UTF-8
        for client in Server.__connections:
            if client is not user:
                client.conn.send(f"{user.nickname}{data}".encode())

    # without design
    def send_bytes(self, user, data):
        for client in Server.__connections:
            if client is not user:
                client.conn.send(data)

    # send file to every user except <user>
    def send_file(self, user, filename, filesize): # filesize in bytes

        # create folder downloads for shared files
        if not os.path.exists("downloads"):
            os.mkdir("downloads")

        # get file from user that sharing file
        with open(f"downloads/{filename}", 'wb') as f:
            part_of_data = user.conn.recv(1024)
            f.write(part_of_data)
            i = filesize / 1024 # we get by 1024 bytes, so...
            while i > 1:
                i -= 1
                part_of_data = user.conn.recv(1024)
                f.write(part_of_data)

        # send base information to all users except file author
        self.send_bytes(user, f"[TRANSFERING] {user.nickname} sent file <{filename}> {filesize}".encode())

        # send file to all users except file author
        with open(f"downloads/{filename}", 'rb') as f:
            data = f.read(1024)
            self.send_bytes(user, data)
            while data:
                data = f.read(1024)
                self.send_bytes(user, data)

        os.remove(f"downloads/{filename}") # we don't need to keep this file on our server

        print(f"File {filename} is shared to users.") # information for administrator

    # send updated version of client to user with socket <conn>
    def send_client(self, conn):
        while True:
            try:
                with open(f"client {User.version}", 'rb') as f:
                    data = f.read(1024)
                    conn.send(data)
                    while data:
                        data = f.read(1024)
                        conn.send(data)
                break
            except: # error can be when we open the file. Because we updated client, but server don't have enough
                # time to update version for it
                User.version = get_user_version()
                # then we try again (while True)

    # send all users to the <user>
    def send_members(self, user):
        members = "Members:\n"
        for client in Server.__connections:
            members += "-" + client.nickname + "\n"
        user.conn.send(members.encode())

    # to send <data> from <user_from> to <user_to>
    def send_private_message(self, user_from, user_to, data):
        data = " ".join(data)
        for user in Server.__connections:
            if user.nickname == user_to:
                user.conn.send(f"Private Message from {user_from.nickname}: {data}".encode())
                break
        else: # break wasn't used
            user_from.conn.send(b"Nickname is incorrect, you can use /members to see all members of chat.")

    # to close all connections and the server
    def __del__(self):
        for user in Server.__connections:
            user.conn.close()
        self.server.close()
        print("Server is done.")

def get_user_version():
    for file in os.listdir():
        if "client" in file:
            return file.split()[1]

# object of user. It contains object of socket, addr and nickname of user
class User:
    version = get_user_version()
    def __init__(self, conn, addr, nick, password=None):
        self.conn = conn
        self.addr = addr
        self.nickname = nick
        self.password = password

# information for administrator
print("You can press any key to stop the server.")

server = Server()

while True:
    input() # Just press any key to stop the server
    break

# close all connections and the server
del server