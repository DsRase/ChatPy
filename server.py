import socket
import sys
from threading import Thread

connections = []

count_of_connections = 2

sock = socket.socket()
sock.bind(('', 8080))
sock.listen(count_of_connections)

try:
    for _ in range(count_of_connections):
        connections.append(sock.accept())
        print(f"Connected: {connections[-1][1]}")
except KeyboardInterrupt:
    sys.stderr.write("SERVER WAS INTERRUPTED")

# В отдельном потоке слушает данные от клиентов
# А после отправляет эти данные всем оставшимся клиентам
def listen_data(client):
    while True:
        data = client.recv(1024)
        if data.decode() == "stop": break
        for connection in connections:
            if connection[0] is client: continue
            connection[0].send(data)

threads = [Thread(target=listen_data, args=(connection[0], ), daemon=True) for connection in connections] # Создаём потоки
[thread.start() for thread in threads]
[thread.join() for thread in threads]

# Закрытие соединений
for connection in connections:
    connection[0].close()
sock.close()