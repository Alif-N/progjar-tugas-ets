import argparse
import os
import time
import socket
import base64
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool
import csv

BUFFER_SIZE = 65536  # buffer 64KB
SERVER_ADDRESS = ('localhost', 45000)

# Daftar file untuk pengujian
TEST_FILES = {
    '10MB': 'file_10mb.dat',
    '50MB': 'file_50mb.dat',
    '100MB': 'file_100mb.dat'
}

def send_command(command_str):
    try:
        with socket.create_connection(SERVER_ADDRESS) as sock:
            sock.sendall((command_str + "\r\n\r\n").encode())
            response_data = ""
            while True:
                chunk = sock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                response_data += chunk.decode()
                if "\r\n\r\n" in response_data:
                    break
            return json.loads(response_data)
    except Exception as e:
        return {'status': 'ERROR', 'data': str(e)}

    
def remote_get(filename=""):
    start = time.time()
    command = f"GET {filename}\r\n"
    result = send_command(command)
    duration = time.time() - start

    if result and result.get('status') == 'OK':
        try:
            filename = result['data_namafile']
            content = base64.b64decode(result['data_file'])
            with open(filename, 'wb') as f:
                f.write(content)
            print(f"File '{filename}' berhasil di-download.")
            return {
                'status': 'OK', 'filename': filename,
                'bytes': len(content), 'time': duration, 'error': None
            }
        except Exception as e:
            print(f"Gagal menulis file: {e}")
            return {'status': 'ERROR', 'filename': filename, 'bytes': 0, 'time': duration, 'error': str(e)}
    else:
        print("Gagal mendapatkan file")
        return {
            'status': 'ERROR', 'filename': filename,
            'bytes': 0, 'time': duration,
            'error': result.get('data', 'Unknown error') if result else 'No response'
        }


def remote_upload(filepath):
    start = time.time()
    try:
        with open(filepath, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        filename = os.path.basename(filepath)
        command = f"UPLOAD {filename}||{encoded}\r\n\r\n"
        result = send_command(command)
        duration = time.time() - start

        if result and result.get('status') == 'OK':
            print(f"Berhasil upload file: {filename}")
            return {'status': 'OK', 'filename': filename, 'bytes': len(encoded), 'time': duration, 'error': None}
        else:
            print(f"Gagal upload file: {result.get('data', 'Unknown error')}")
            return {'status': 'ERROR', 'filename': filename, 'bytes': 0, 'time': duration, 'error': result.get('data', 'Unknown error')}
    except Exception as e:
        print(f"Gagal upload file: {e}")
        return {'status': 'ERROR', 'filename': filepath, 'bytes': 0, 'time': time.time() - start, 'error': str(e)}


def run_stress_test(operation, size, client_pool_size):
    filename = TEST_FILES[size]
    task_func = remote_upload if operation == 'UPLOAD' else remote_get
    file_target = filename if operation == 'UPLOAD' else os.path.basename(filename)

    results = []
    with ThreadPoolExecutor(max_workers=client_pool_size) as executor:
        tasks = [executor.submit(task_func, file_target) for _ in range(client_pool_size)]
        for future in as_completed(tasks):
            try:
                res = future.result()
                if not isinstance(res, dict):
                    res = {'status': 'ERROR', 'filename': file_target, 'bytes': 0, 'time': 0, 'error': 'Invalid result format'}
            except Exception as e:
                res = {'status': 'ERROR', 'filename': file_target, 'bytes': 0, 'time': 0, 'error': str(e)}
            results.append(res)
    return results


def run_single_test(args):
    test_no, op, size, client_pools, server_pools = args
    results = run_stress_test(op, size, client_pools)
    success = sum(1 for r in results if r.get('status') == 'OK')
    fail = len(results) - success
    total_bytes = sum(r.get('bytes', 0) for r in results)
    total_time = sum(r.get('time', 0) for r in results if r.get('time', 0) > 0)
    throughput = total_bytes / total_time if total_time > 0 else 0

    print(f"Total bytes: {total_bytes}, Total time: {total_time}")
    print(f"Done test #{test_no} - {op} {size} C:{client_pools} S:{server_pools}")

    return [
        test_no, op, size, client_pools, server_pools,
        round(total_time, 2), int(throughput),
        success, fail, success, fail
    ]


def main(client_pools, server_pools):
    operations = ['UPLOAD', 'DOWNLOAD']
    sizes = ['10MB', '50MB', '100MB']

    if not os.path.exists('stress_test_results.csv'):
        with open('stress_test_results.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Test No', 'Operation', 'Size', 'Client Pool',
                'Server Pool', 'Total Time (s)', 'Throughput (B/s)',
                'Success Client', 'Fail Client', 'Success Server', 'Fail Server'
            ])

    test_no = 1
    task_args = [(test_no + i, op, size, client_pools, server_pools)
                 for i, (op, size) in enumerate((op, size) for size in sizes for op in operations)]

    for args in task_args:
        row = run_single_test(args)
        with open('stress_test_results.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
            f.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stress test client-server file transfer")
    parser.add_argument('--client-pool', type=int, default=1, help="Jumlah client pool")
    parser.add_argument('--server-pool', type=int, default=1, help="Jumlah server pool")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    main(args.client_pool, args.server_pool)
