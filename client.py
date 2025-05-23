import socket
from tkinter import *
from tkinter import ttk
from threading import Thread

root = Tk()
root.geometry('300x250')
root.title("CHAT NO NE GPT!")

# Серверная часть
IP = "127.0.0.1"
PORT = 8080

client = socket.socket()
client.connect((IP, PORT))


# Слушает сообщения от пользователей на фоне
def listen_server():
    while True:
        data = client.recv(1024).decode()
        if data == "stop":
            print("Собеседник отключился")
            break
        other_text["text"] = data


# Отправляет сообщение в чат
def send():
    data = t.get()
    client_text["text"] = data
    client.send(data.encode())
    t.delete(0, END)  # Очищаем поле ввода


send_btn = ttk.Button(text="Send", command=send)
send_btn.place(x=220, y=8)

# Графическая часть
t = ttk.Entry(width=270)
t.place(width=215, y=10, x=5)

info = ttk.Label(text="RED - YOU | BLUE - YOUR OPPONENT")
info.place(relx=.3, rely=.2)

client_text = ttk.Label(text='user1', font='Arial 13', foreground='blue')
client_text.place(rely=.3)

other_text = ttk.Label(text="user2", font="Arial 13", foreground='red')
other_text.place(rely=.5)

listening = Thread(target=listen_server, daemon=True)
listening.start()


def exit():
    client.close()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", exit)

root.mainloop()