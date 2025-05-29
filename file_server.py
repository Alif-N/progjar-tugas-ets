import argparse
import socket
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from file_protocol import FileProtocol

HOST = '0.0.0.0'
PORT = 45000
BUFFER_SIZE = 65536  # 64KB

def handle_client(conn_data):
    conn_data, addr = conn_data
    logging.warning(f"[PROCESS] Connection from {addr} established")
    conn = conn_data

    data_received = ''
    while True:
        data = conn.recv(BUFFER_SIZE)
        if not data:
            break
        data_received += data.decode()
        if "\r\n\r\n" in data_received:
            break

    fp = FileProtocol()
    response = fp.proses_string(data_received.strip())
    response += "\r\n\r\n"
    conn.sendall(response.encode())
    conn.close()
    logging.warning(f"[PROCESS] Connection from {addr} closed")

def main(pool_sizes, executor):
    logging.basicConfig(level=logging.WARNING)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(100)
    logging.warning(f"[PROCESS] Server running on {HOST}:{PORT}")

    if executor == 'process' :
        with ProcessPoolExecutor(max_workers=pool_sizes) as executor:
            while True:
                conn, addr = server_socket.accept()
                executor.submit(handle_client, (conn, addr))
    else:
        with ThreadPoolExecutor(max_workers=pool_sizes) as executor:
            while True:
                conn, addr = server_socket.accept()
                executor.submit(handle_client, (conn, addr))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Number of Pool Server")
    parser.add_argument('--pool', type=int, default=1, help="Daftar ukuran server pool, contoh: 1,5,50")
    parser.add_argument('--operation', type=str, default='thread', help="Jenis operasi: thread atau process")
    args = parser.parse_args()
    main(args.pool, args.operation)