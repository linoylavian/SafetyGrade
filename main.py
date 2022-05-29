import cv2
import numpy as np
import torch
import threading
import socket
import select
import pandas as pd
import csv
import struct
import pickle
import hashlib
from opticalflow import OpticalFlowModel
from speeds import SpeedModel
from detection import RoadSigns

class Request(socket.socket):
    def __init__(self, state="initial", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = state  # the exepted data from the client
        self.name = ''
        self.password = ''
        self.data = []

    @classmethod
    def copy(client_sock, sock, *args, **kwargs):
        """copies the socket.socket object into a new Request"""
        fd = socket.dup(sock.fileno())
        copy = client_sock(sock.type, sock.family, sock.proto, fileno=fd)
        copy.settimeout(sock.gettimeout())
        # sets the state
        copy.state = 'initial'
        # return the socket.socket object as a Request object
        return copy

class CsvDataBase:
    def __init__(self, filename):
        self.file = filename

    def write_row(self, username, password):
        """
        write new row in the file for new users
        :param username: username
        :param password: password
        """
        import csv
        file = open(self.file, 'a')
        csv = csv.writer(file, delimiter=',')
        csv.writerow([username, password])
        file.close()

    def add_grade(self, r, grade):
        """
        update the user grades when he get new grade
        :param r: user from Request type
        :param grade: the grade to update
        """
        if grade != 'not enough data':
            import csv
            from tempfile import NamedTemporaryFile
            import shutil
            tempfile = NamedTemporaryFile(mode='w', delete=False)
            fields = ['username', 'password', 'grades']
            with open(self.file, 'r') as csvfile, tempfile:
                reader = csv.DictReader(csvfile, fieldnames=fields)
                writer = csv.DictWriter(tempfile, fieldnames=fields)
                for row in reader:
                    if row['username'] == r.name:
                        if row['grades'] is not None:
                            row['grades'] = str(grade) + ', ' + row['grades']
                        else:
                            row['grades'] = str(grade)
                    row = {'username': row['username'], 'password': row['password'], 'grades': row['grades']}
                    writer.writerow(row)
            shutil.move(tempfile.name, self.file)

    def get_grades(self, r):
        """
        :param r: user from Request type
        :return: grades of the user
        """
        with open(self.file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['username'] == r.name:
                    grades = row['grades']
                    return grades if grades is not None else ''

    def check_new_user(self, name):
        """
        check if the name is already exist in file
        :param name: name to check
        :return: True if not exist, False if exist
        """
        df = pd.read_csv(self.file)
        for x in df.username:
            if x == name:
                return False
        return True

    @staticmethod
    def strtomd5(st):
        """
        encode the password with md5
        :param st: string to encode
        :return: encoded string
        """
        hash_object = hashlib.md5(st.encode())
        return hash_object.hexdigest()

class Video:
    def __init__(self):
        # video
        self.DEVICE = 'cpu'
        self.flowmodel = OpticalFlowModel.getmodel()
        self.speedmodel = SpeedModel()
        self.signsmodel = RoadSigns()
        self.mutex = threading.Lock()
        self.database = CsvDataBase('users.csv')
        self.sign = ''
        # network
        self.SERVER_PORT = 1234
        # self.SERVER_IP = '192.168.1.109'
        self.SERVER_IP = '0.0.0.0'
        self.server = Request(state='server')
        self.server.setblocking(False)
        self.server.bind((self.SERVER_IP, self.SERVER_PORT))
        self.server.listen()
        self.server_mutex = threading.Lock()
        self.read = [self.server]
        self.messages = []
        print('listening...')
        self.listen()

    def listen(self):
        """accept clients and handle data"""
        while self.read:
            readable, writeable, exceptional = select.select(self.read, self.messages, self.read)
            for r in readable:
                if r is self.server:
                    client, address = r.accept()
                    print('connected to ' + str(address))
                    self.read.append(Request.copy(client))
                    self.messages.append((self.read[-1], 'ok'))
                else:
                    if r.state != 'sending video':
                        try:
                            data = r.recv(1024).decode()
                            print(data)
                        except ConnectionAbortedError:
                            r.close()
                            readable.remove(r)
                            self.read.remove(r)
                            continue
                    else:
                        self.get_video(r)
                        continue
                    if data:
                        if data == 'quit':
                            r.close()
                            readable.remove(r)
                            self.read.remove(r)
                        elif r.state == 'initial':
                            self.initial(r, data)
            self.send_messages()

    def initial(self, r, data):
        """handle initial clients"""
        if data == 'video':
            r.state = 'sending video'
            if self.mutex.locked():
                self.mutex.release()
        else:
            mode, name, password = data.split('/')
            if mode == 'login':
                self.login(r, name, password)
            elif mode == 'register':
                self.register(r, name, password)

    def send_messages(self):
        """send all messages in self.messages"""
        for message in self.messages:
            current_socket, data = message
            if current_socket in self.read:
                if isinstance(data, int) or isinstance(data, float):
                    current_socket.send(str(data).encode())
                else:
                    current_socket.send(data.encode())
            self.messages.remove(message)

    def register(self, r, name, password):
        """handle new users
        :return: True if the register succeed, False if not"""
        if self.database.check_new_user(name):
            self.database.write_row(name, CsvDataBase.strtomd5(password))
            r.name = name
            r.password = password
            r.state = 'sending video'
            self.messages.append((r, 'upload video'))
            return True
        r.state = 'initial'
        self.messages.append((r, 'wrong'))
        return False

    def login(self, r, name, password):
        """handle user for logging in
        :return: True if the logging succeed, False if not"""
        df = pd.read_csv('users.csv')
        for x in range(df.shape[0]):
            if df.username[x] == name:
                if df.password[x] == CsvDataBase.strtomd5(password):
                    r.name = name
                    r.password = password
                    r.state = 'sending video'
                    self.messages.append((r, 'upload video'))
                    return True
        r.state = 'initial'
        self.messages.append((r, 'wrong'))
        return False

    def get_frame(self, data, payload_size, r):
        """
        :param data: recieved data
        :param payload_size: expected size of the frame
        :param r: user
        :return: received frame and data, None if video stopped
        """
        while len(data) < payload_size:
            rec = r.recv(4096)
            # if (b'finish' in rec) or (b'quit' in rec):
            if rec.endswith(b'finish') or rec.endswith(b'quit'):
                return None, None
            data += rec
        # receive image row data form client socket
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack(">L", packed_msg_size)[0]
        while len(data) < msg_size:
            rec = r.recv(4096)
            # if (b'finish' in rec) or (b'quit' in rec):
            if rec.endswith(b'finish') or rec.endswith(b'quit'):
                return None, None
            data += rec
        frame_data = data[:msg_size]
        data = data[msg_size:]
        # unpack image using pickle
        frame = pickle.loads(frame_data, fix_imports=True, encoding="bytes")
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        return frame, data

    def get_video(self, r):
        """get the video frame by frame, and handle every frame
        :param r: user"""
        self.server_mutex.acquire()
        self.sign = ''
        flag = False
        cur = None
        prev = None
        count = 0
        data = b""
        payload_size = struct.calcsize(">L")
        while True:
            frame, data = self.get_frame(data, payload_size, r)
            if self.sign != '':
                r.send(self.imdata.encode())
                self.sign = ''
            else:
                r.send(''.encode())
            if frame is not None:
                if (not self.mutex.locked()) and (len(r.data) > 0) and (count != 0):
                    cur = self.load_image(frame)
                    if flag is True:
                        t1 = threading.Thread(target=self.analyzespeed, args=(prev, cur, count, r))
                        t1.start()
                        flag = False
                    prev = cur
                    flag = True
                t2 = threading.Thread(target=self.analyzesigns, args=(frame, count, r))
                t2.start()
                count += 1
            else:
                break
        try:
            if t1.is_alive():
                t1.join()
        except UnboundLocalError:  # thread did not open
            print()
        finally:
            self.calcgrade(r)
            self.server_mutex.release()

    def load_image(self, nparr):
        img = nparr.astype(np.uint8)
        img = torch.from_numpy(img).permute(2, 0, 1).float()
        return img[None].to(self.DEVICE)

    def analyzespeed(self, prev, cur, count, r):
        self.mutex.acquire()
        flow = OpticalFlowModel.run2(prev, cur, self.flowmodel)
        speed = self.speedmodel.item(flow)
        print(speed)
        r.data.append((count, speed))
        self.mutex.release()

    def analyzesigns(self, frame, count, r):
        sign, x, y, w, h = self.signsmodel.single_image(frame)
        if sign is not None:
            print(sign)
            self.sign = sign
            self.imdata = sign + '*' + str(x) + '*' + str(y) + '*' + str(w) + '*' + str(h) + '*'
            if (not r.data) or (r.data[-1][1] != sign):
                r.data.append((count, sign))

    def calcgrade(self, r):
        """calculate the user's grade and send it"""
        speed = 0
        cur = []
        grade = []
        r.data.sort(key=lambda x: x[0])
        print(r.data)
        for f, d in r.data:
            if isinstance(d, float) and speed != 0:
                cur.append(d)
            elif isinstance(d, str):
                grade = self.update_grade(cur, grade, speed)
                cur = []
                t = d.split('(')[1]
                speed = int(t.split('k')[0])
        grade = self.update_grade(cur, grade, speed)
        print(grade)
        finalgrade = self.list_to_grade(grade)
        print(finalgrade)
        r.state = 'initial'
        r.data = []
        if finalgrade != 'not enough data':
            self.database.add_grade(r, str(finalgrade))
            self.messages.append((r, self.database.get_grades(r)))
        else:
            self.messages.append((r, ('not enough data, ' + self.database.get_grades(r))))

    def update_grade(self, cur, grade, speed):
        if cur:
            avg = sum(cur) / float(len(cur))
            if (avg - speed) > 15:
                grade.append(1)
            else:
                grade.append(0)
        return grade

    def list_to_grade(self, grade):
        try:
            point = 100 / len(grade)
            fail = sum(grade) * point
            return int(100 - fail)
        except:
            return 'not enough data'


if __name__ == '__main__':
    vid = Video()
