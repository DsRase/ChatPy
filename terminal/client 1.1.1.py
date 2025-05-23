import socket
from threading import Thread
import os
from time import sleep
from sys import argv, exit

def get_user_version():
    for file in os.listdir():
        if "client" in file:
            return file.split()[1]

class Client:
    commands = {
        "/exit": "To disconnect from this chat.",
        "/help": "To know about commands in this chat.",
        "/members": "To get information about all members of this chat.",
        "/transfer <file_path>": "To share file from your PC to the PC of all members.",
        "/pm <member> <message>": "To send private message <message> to the <member>."
    }
    version = get_user_version()
    # connecting
    def __init__(self, nickname=None, ip="localhost", port=9090):
        self._is_connected = False

        # Trying to connect. All nicknames are unique
        while not self._is_connected:
            self.user = socket.socket()
            self.user.connect((ip, port))
            self.nickname = input("Input your name >> ") if not nickname else nickname
            self.user.send(self.nickname.encode())

            answer = self.user.recv(1024).decode()  # get answer from the server about our nickname

            print(answer, end='\n\n')

            if answer != "Nickname is already used. Try again.":
                if self.check_version():
                    self._is_connected = True
                else:
                    # user input "n"
                    self.user.close()
                    exit(0)
            else:
                self.user.close()

    # starting send and listen messages
    def start(self):
        if not self._is_connected: return False
        """
        to start the client
        :return:
        """
        # we need each 'frame' check message
        Thread(target=self.check_message, daemon=True).start()
        # also we need check version (no, we don't
        # Thread(target=self.check_version, daemon=True).start()

        # the main cycle of writing data from user
        while self._is_connected:
            data = input(">> ")

            # if we don't need to send message to server, it's just for client
            if not data: continue
            elif data.lower() == "/help":
                self.help()
                continue
            elif data.lower().split()[0] == "/transfer":
                try:
                    filename = " ".join(data.split()[1:])  # Here can be an error
                    if not os.path.exists(os.path.abspath(filename)): # file isn't exist, so...:
                        print("Input file that exists!\n")
                    else:
                        self.send_message(f"{data} {os.path.getsize(filename)}".encode())
                        self.transfer(filename)
                        print("File is shared!\n")
                except IndexError:
                    print("Input name of file!\n")
                finally:
                    continue

            # else:
            self.send_message(data.encode())
            match data.lower().split()[0]:  # check for special commands
                case "/exit": break
                # just for understanding, that they aren't incorrect command
                case "/pm": pass
                case "/members": pass
                case "/transfer": pass
                case _:
                    if data[0] == '/':
                        print("The command is incorrect!\n")

        self._is_connected = False
        self.user.close()
        print("You successfully disconnected.")

    # send text message to the server
    def send_message(self, data):
        self.user.send(data)

    # checking version of client with version on the server
    def check_version(self):
        self.user.send(self.version.encode())  # send to compare versions
        print("мы отправили")
        answer = self.user.recv(1024).decode().split()
        print("получили ответ от сервера:", answer)
        if answer[0] == "OK":
            return True
        else:
            print(" ".join(answer[:-2])) # all data except filesize and version
            client_answer = input("Y/N >> ").lower()
            self.user.send(client_answer.encode())
            if client_answer == "y":
                self.get_new_client(int(answer[-2]), answer[-1])
                return True
            else:
                return False

    # listening message from server
    def check_message(self):
        while self._is_connected:
            try:
                data = self.user.recv(1024).decode()
            except:
                self._is_connected = False
                break
            decode_data = data.split()

            match decode_data[0].lower():
                case "members:": self.members(data)
                case "[transfering]":
                    filename = decode_data[-2][1:-1]
                    filesize = int(decode_data[-1])
                    print(filename, filesize)
                    print("[SERVER]", decode_data[1], "is sending file ", decode_data[-2], ". Waiting. You can abort this by press CTRL+C.")
                    self.get_file(decode_data[-2][1:-1], int(decode_data[-1])) # name of file, size of file
                    print("[SERVER] Sharing is done. Check downloads folder.")
                    continue
                case "[update]":
                    print(" ".join(decode_data[:-2]))
                    answer = input("Y/N >> ").lower()
                    if answer == "y":
                        self.user.send(f"[UPDATE] OK 200 {decode_data[-1]}".encode()) # to start server sends us new version of client
                        self.get_new_client(decode_data[-2], decode_data[-1])
                    else:
                        self.user.send("/exit".encode())
                        self._is_connected = False
                        self.user.close()
                case "[break]": # extra exit from the program, server doesn't work for some reason.
                    self.user.close()
                    self._is_connected = False
                    break
                case _: print(data)

    # get from server new version of client
    def get_new_client(self, filesize, new_version):
        with open(f"client {new_version}", 'wb') as f:
            data = self.user.recv(1024)
            f.write(data)
            i = filesize / 1024
            while i > 1:
                i -= 1
                data = self.user.recv(1024)
                f.write(data)


        os.system(f'python "client {new_version}" {self.nickname}') # start new version of client

        # stop this program
        self.user.close()
        print("bye bye")
        exit(0)
        # we delete old version in new client

    # ------------------ some useful functions ------------------

    # to print all members of chat+
    def members(self, data):
        print()
        for member in data.split():
            print(member)
        print()

    # to print all commands to user
    def help(self):
        for command, description in self.commands.items():
            print(command, "-", description)
        print()

    # transfer file to server
    def transfer(self, filename):
        # transfer all bytes of file to server
        with open(filename, 'rb') as f:
            data = f.read(1024)
            self.user.send(data)
            # self.user.send(f"{data} {file_size}".encode())
            while data:
                data = f.read(1024)
                self.user.send(data)

    # get file from server
    def get_file(self, filename, filesize):
        # create folder downloads for shared files
        if not os.path.exists("downloads"):
            os.mkdir("downloads")

        aborted = False

        # get file from user that sharing file
        with open(f"downloads/{filename}", 'wb') as f:
            try:
                part_of_data = self.user.recv(1024)
                f.write(part_of_data)
                i = filesize / 1024  # we get by 1024 bytes, so...
                while i > 1:
                    i -= 1
                    part_of_data = self.user.recv(1024)
                    f.write(part_of_data)
            except KeyboardInterrupt:
                aborted = True
                print("Aborted successfully.")
        if aborted: os.remove(f"downloads/{filename}")

try:
    nickname = argv[1]
except:
    nickname = None
user = Client(nickname)

# delete all old versions of client
def delete_old_client():
    for file in os.listdir():
        if "client" in file and file != f"client {user.version}":
            os.remove(file)

delete_old_client()

user.start()