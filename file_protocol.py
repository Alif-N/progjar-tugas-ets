import json
import logging
import shlex
import base64

from file_interface import FileInterface

"""
Kelas FileProtocol berfungsi untuk menangani data yang diterima dari client 
dan memastikan apakah data tersebut sesuai dengan format protokol yang ditentukan.

Data yang diterima dari client berupa bytes dan diubah ke dalam bentuk string 
untuk diproses.

Pemrosesan dilakukan berdasarkan perintah yang dikirimkan, seperti: LIST, GET, UPLOAD, DELETE.
"""

class FileProtocol:
    def __init__(self):
        # Inisialisasi objek dari FileInterface untuk akses ke operasi file
        self.file = FileInterface()

    def proses_string(self, string_datamasuk=''):
        # Penanganan khusus untuk perintah UPLOAD
        if string_datamasuk.upper().startswith("UPLOAD "):
            try:
                # Bersihkan karakter tidak penting di akhir dan hapus kata "UPLOAD "
                cleaned = string_datamasuk.strip()[7:]

                # Cek apakah format upload mengandung pemisah "||"
                if "||" not in cleaned:
                    return json.dumps(dict(status='ERROR', data='Format upload tidak valid'))

                # Pisahkan nama file dan data base64
                filename, base64_data = cleaned.split("||", 1)
                filename = filename.strip()
                base64_data = base64_data.strip()

                # Simpan isi file hasil decode base64
                with open(f'files/{filename}', 'wb') as f:
                    f.write(base64.b64decode(base64_data))

                return json.dumps(dict(status='OK', data=f'File {filename} berhasil diupload'))
            except Exception as e:
                return json.dumps(dict(status='ERROR', data=f'Gagal upload file: {str(e)}'))
        
        # Penanganan perintah lainnya: LIST, GET, DELETE
        try:
            # Parsing string perintah menggunakan shlex agar lebih aman
            c = shlex.split(string_datamasuk)
            c_request = c[0].strip().upper()
            params = [x for x in c[1:]]

            # Pastikan metode tersedia di FileInterface sebelum dipanggil
            if hasattr(self.file, c_request.lower()):
                cl = getattr(self.file, c_request.lower())(params)
                return json.dumps(cl)
            else:
                return json.dumps(dict(status='ERROR', data='request tidak dikenali'))
        except Exception as e:
            return json.dumps(dict(status='ERROR', data=f'Exception: {str(e)}'))


if __name__ == '__main__':
    # Contoh penggunaan kelas FileProtocol
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET pokijan.jpg"))
