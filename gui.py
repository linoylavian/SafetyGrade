#!/usr/bin/python
import socket
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
import PIL.Image, PIL.ImageTk
import time
import cv2
import pickle
import struct
import threading
from instabot import Bot
import ctypes

class MyVideoCapture:
    def __init__(self, video_source, socket):
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            print('close')
            socket.send('quit'.encode())
            raise ValueError("Unable to open video source", video_source)
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        self.s = socket
        self.mutex = threading.Lock()

    def get_frame(self):
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                frame = cv2.resize(frame, (640, 480))
                result, image = cv2.imencode('.jpg', frame, self.encode_param)
                data = pickle.dumps(image, 0)
                size = len(data)
                self.mutex.acquire()
                self.s.setblocking(True)
                self.s.sendall(struct.pack(">L", size) + data)
                self.s.setblocking(False)
                self.mutex.release()
                try:
                    sign = self.s.recv(1024).decode()
                except BlockingIOError:
                    sign = ''
                return ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), sign
            else:
                return ret, None, None
        else:
            return False, None, None

    # Release the video source when the object is destroyed
    def delete(self):
        if self.vid.isOpened():
            self.vid.release()
        self.s.setblocking(True)
        self.mutex.acquire()
        self.s.send('finish'.encode())
        self.mutex.release()


class ThreadWithException(threading.Thread):
    def __init__(self, username, password, bot, grade):
        threading.Thread.__init__(self)
        self.username = username
        self.password = password
        self.bot = bot
        self.grade = grade

    def run(self):
        self.bot.login(username=self.username, password=self.password)
        self.bot.upload_photo("Picture2.png", caption="My Grade on SafetyGrade is " + self.grade +
                                                      "!\nGet your garde too in SafetyGrade")

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
                                                         ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')

class Instagram:
    def __init__(self, grade):
        self.bot = Bot()
        self.grade = grade
        self.insta_screen = Tk()
        self.insta_screen.title("Instagram")
        self.insta_screen.iconbitmap('picture1_ZzW_icon.ico')
        self.insta_screen.geometry("450x300")
        self.login()

    def login(self):
        Label(self.insta_screen, text="\nLogIn To Instagram\n", font=("bold", 16)).pack()
        Label(self.insta_screen, text="Username", font=("normal", 12)).pack()
        self.username_login_entry = Entry(self.insta_screen, textvariable="username", font=("normal", 12))
        self.username_login_entry.delete(0, END)
        self.username_login_entry.pack()
        Label(self.insta_screen, text="").pack()
        Label(self.insta_screen, text="Password", font=("normal", 12)).pack()
        self.password__login_entry = Entry(self.insta_screen, textvariable="password", show='*', font=("normal", 12))
        self.password__login_entry.delete(0, END)
        self.password__login_entry.pack()
        Label(self.insta_screen, text="").pack()
        button1 = Button(self.insta_screen, text="Login", width=10, height=2, font=("normal", 10), command=self.upload)
        button1.pack()

    def upload(self):
        username = self.username_login_entry.get()
        password = self.password__login_entry.get()
        t1 = ThreadWithException(username, password, self.bot, self.grade)
        t1.start()
        start = time.time()
        while True:
            now = time.time()
            if (now - start) > 2:
                break
        if t1.isAlive():
            t1.raise_exception()
            Label(self.insta_screen, text="error", font=('bold', 18), fg='red').pack()
            time.sleep(5)
        self.insta_screen.destroy()

    def botaction(self, username, password):
        self.bot.login(username=username, password=password)
        self.bot.upload_photo("Picture2.png", caption="My Grade on SafetyGrade is " + self.grade +
                                                      "!\nGet your garde too in SafetyGrade")
        self.insta_screen.destroy()

    def manage_time(self):
        start = time.time()
        while True:
            now = time.time()
            if (now - start) > 2:
                break

class GUI:
    def __init__(self):
        self.username = ''
        self.password = ''
        self.file = None
        self.port = 1234
        self.ip = '127.0.0.1'
        self.s = socket.socket()
        try:
            self.s.connect((self.ip, self.port))
        except:
            messagebox.showerror("Error", "Error message")
        while True:
            data = self.s.recv(1024).decode()
            if data:
                break
        self.color = '#B07DA3'
        self.screen = Tk()
        self.login_screen = None
        self.register_screen = None
        self.welcomePage()

    def loginPage(self, wrong_mes=False, busy_mes=False, event=None):
        if self.login_screen is not None:
            self.login_screen.destroy()
        if self.register_screen is not None:
            self.register_screen.destroy()
        self.login_screen = Frame(self.screen, bg=self.color)
        self.login_screen.pack(side="top", expand=True, fill="both")
        Label(self.login_screen, text="", bg=self.color).pack()
        Label(self.login_screen, text="Please enter login details", font=("normal", 18), bg=self.color).pack()
        Label(self.login_screen, text="", bg=self.color).pack()
        Label(self.login_screen, text="Username", font=("normal", 12), bg=self.color).pack()
        self.username_login_entry = Entry(self.login_screen, textvariable="username", font=("normal", 12))
        self.username_login_entry.delete(0, END)
        self.username_login_entry.pack()
        Label(self.login_screen, text="", bg=self.color).pack()
        Label(self.login_screen, text="Password", font=("normal", 12), bg=self.color).pack()
        self.password__login_entry = Entry(self.login_screen, textvariable="password", show='*', font=("normal", 12))
        self.password__login_entry.delete(0, END)
        self.password__login_entry.pack()
        Label(self.login_screen, text="", bg=self.color).pack()
        button1 = Button(self.login_screen, text="Login", width=10, height=2, font=("normal", 10))
        button1.bind("<Button-1>", self.handle_login)
        button1.pack()
        if wrong_mes is True:
            Label(self.login_screen, text="wrong username or password").pack()
        if busy_mes is True:
            print(22)
            Label(self.login_screen, text="our server is busy, please try again later").pack()
        self.login_screen.mainloop()

    def handle_login(self, event):
        self.username = self.username_login_entry.get()
        self.password = self.password__login_entry.get()
        self.s.send(('login/' + self.username + '/' + self.password).encode())
        before = time.time()
        while True:
            data = self.s.recv(1024).decode()
            if not data:
                after = time.time()
                if (after - before) > 2:
                    self.loginPage(busy_mes=True)
            else:
                break
        if data == 'upload video':
            self.login_screen.destroy()
            self.video()
        elif data == 'wrong':
            self.loginPage(wrong_mes=True)

    def handle_register(self, event):
        self.username = self.username_register_entry.get()
        self.password = self.password__register_entry.get()
        self.s.send(('register/' + self.username + '/' + self.password).encode())
        before = time.time()
        while True:
            data = self.s.recv(1024).decode()
            if not data:
                after = time.time()
                if (after - before) > 2:
                    self.registerPage(busy_mes=True)
            else:
                break
        if data == 'upload video':
            self.register_screen.destroy()
            self.video()
        elif data == 'wrong':
            self.registerPage(wrong_mes=True)

    def registerPage(self, wrong_mes=False, busy_mes=False, event=None):
        if self.register_screen is not None:
            self.register_screen.destroy()
        if self.login_screen is not None:
            self.login_screen.destroy()
        self.register_screen = Frame(self.screen, bg=self.color)
        self.register_screen.pack(side="top", expand=True, fill="both")
        Label(self.register_screen, text="", bg=self.color).pack()
        Label(self.register_screen, text="Please enter register details", font=("normal", 18), bg=self.color).pack()
        Label(self.register_screen, text="", bg=self.color).pack()
        Label(self.register_screen, text="Username", font=("normal", 12), bg=self.color).pack()
        self.username_register_entry = Entry(self.register_screen, textvariable="username", font=("normal", 12))
        self.username_register_entry.delete(0, END)
        self.username_register_entry.pack()
        Label(self.register_screen, text="", bg=self.color).pack()
        Label(self.register_screen, text="Password", font=("normal", 12), bg=self.color).pack()
        self.password__register_entry = Entry(self.register_screen, textvariable="password", show='*', font=("normal", 12))
        self.password__register_entry.delete(0, END)
        self.password__register_entry.pack()
        Label(self.register_screen, text="", bg=self.color).pack()
        button1 = Button(self.register_screen, text="Regiser", width=10, height=2, font=("normal", 10))
        button1.bind("<Button-1>", self.handle_register)
        button1.pack()
        if wrong_mes is True:
            Label(self.register_screen, text="this username is taken").pack()
        if busy_mes is True:
            Label(self.register_screen, text="our server is busy, please try again later").pack()
        self.register_screen.mainloop()

    def welcomePage(self):
        for widget in self.screen.winfo_children():
            widget.destroy()
        self.screen.title("SafetyGrade")
        self.screen.iconbitmap('picture1_ZzW_icon.ico')
        self.screen.geometry("1100x800")
        self.screen.configure(bg=self.color)
        Label(self.screen, text="\n\nWelcome to Safety Grade", font=("bold", 30), bg=self.color).pack()
        Label(self.screen, text="Choose your option\n", font=("normal", 20), bg=self.color).pack()
        button1 = Button(text="login", height=2, width=15, bg='#567', fg='White', font=("normal", 18))
        button1.bind("<Button-1>", self.loginPage)
        button1.pack()
        button2 = Button(text="register", height=2, width=15, bg='#567', fg='White', font=("normal", 18))
        button2.bind("<Button-1>", self.registerPage)
        button2.pack(pady=10)
        self.screen.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.screen.mainloop()

    def on_closing(self):
        print('close')
        self.s.send('quit'.encode())
        self.screen.destroy()

    def video(self, event=None):
        if event is not None:
            self.s.send('video'.encode())
        for widget in self.screen.winfo_children():
            widget.destroy()
        Label(self.screen, text=("\n\nWelcome " + self.username + '\n'), font=('normal', 28), bg=self.color).pack()
        self.uploadbtn = Button(text="upload video", width=15, height=1, bg='#567', fg='White', font=("normal", 18))
        self.uploadbtn.bind("<Button-1>", self.upload_action)
        self.uploadbtn.pack()

    def upload_action(self, event=None):
        filename = filedialog.askopenfilename(title='select', filetypes=[
                    ("all video format", ".mp4"),
                    ("all video format", ".flv"),
                    ("all video format", ".avi"), ])
        print('Selected:', filename)
        self.file = filename
        self.uploadbtn.destroy()
        self.destroyobjects = []
        self.vid = MyVideoCapture(self.file, self.s)
        self.canvas = Canvas(self.screen, width=self.vid.width, height=self.vid.height, bg=self.color)
        stop_btn = Button(self.screen, text="Stop Video", width=15, height=1, bg='#567', fg='White', font=("normal", 18))
        stop_btn.pack()
        stop_btn.bind("<Button-1>", self.finish)
        self.destroyobjects.append(stop_btn)
        l = Label(self.screen, text="\nSpeed: ", font=('normal', 15), bg=self.color)
        l.pack()
        self.destroyobjects.append(l)
        self.buttons = Frame(self.screen, bg=self.color, width=300, height=300)
        self.buttons.pack(side="top", expand=True, fill="both")
        self.destroyobjects.append(self.buttons)
        b05 = Button(self.buttons, text="0.5", width=10, height=1, bg='#567', fg='White', font=("normal", 12),
                     command=self.speed05)
        b1 = Button(self.buttons, text="1", width=10, height=1, bg='#567', fg='White', font=("normal", 12),
                    command=self.speed1)
        b15 = Button(self.buttons, text="1.5", width=10, height=1, bg='#567', fg='White', font=("normal", 12),
                     command=self.speed15)
        l = Label(self.buttons, text=('                '*3), bg=self.color, font=('normal', 20))
        l.grid(row=0, column=0)
        b05.grid(row=0, column=1)
        b1.grid(row=0, column=2)
        b15.grid(row=0, column=3)
        self.destroyobjects.append(l)
        self.destroyobjects.append(b05)
        self.destroyobjects.append(b1)
        self.destroyobjects.append(b15)
        self.sign = StringVar()
        self.sign.set('')
        self.signlabel = Label(self.screen, textvariable=self.sign, font=("normal", 18), fg='red', bg=self.color)
        self.signlabel.pack()
        self.destroyobjects.append(self.signlabel)
        self.canvas.pack()
        self.destroyobjects.append(self.canvas)
        self.sec = 10
        self.screen.after(self.sec, self.update)

    def speed05(self):
        self.sec = 30

    def speed1(self):
        self.sec = 10

    def speed15(self):
        self.sec = 3

    def finish(self, event):
        for w in self.destroyobjects:
            w.destroy()
        self.vid.delete()
        self.screen.after_cancel(self.after)
        self.s.setblocking(True)
        self.grade = self.s.recv(1024).decode()
        self.gradePage()

    def gradePage(self):
        print(self.grade)
        if ',' in self.grade:
            self.current, previous = self.grade.split(',', 1)
        else:
            self.current = int(self.grade)
            previous = ''
        Label(self.screen, text="Your Grade:", font=('normal', 20), bg=self.color).pack(side=TOP)
        gradelbl = Label(self.screen, text=str(self.current), fg='red', font=("Courier", 30), bg=self.color)
        gradelbl.pack(side=TOP)
        if previous != '':
            Label(self.screen, text="Your previous grades:", font=('normal', 18), bg=self.color).pack()
            gradelbl = Label(self.screen, text=previous, fg='red', font=("normal", 16), bg=self.color)
            gradelbl.pack(side=TOP)
        Label(self.screen, text='', font=("normal", 16), bg=self.color).pack(side=TOP)
        button1 = Button(self.screen, text="Logout", width=20, height=2, command=self.welcomePage, bg='#567', fg='White'
                         , font=("normal", 14))
        button1.pack(side=TOP)
        button1 = Button(self.screen, text="Upload Another video", width=20, height=2, bg='#567', fg='White',
                         font=("normal", 14))
        button1.bind("<Button-1>", self.video)
        button1.pack(side=TOP)
        button1 = Button(self.screen, text="Share On Instagram", width=20, height=2, bg='#567', fg='White',
                         font=("normal", 14))
        button1.bind("<Button-1>", self.instagram)
        button1.pack(side=TOP)
        self.screen.mainloop()

    def instagram(self, event):
        instagram = Instagram(str(self.current))

    def update(self):
        ret, frame, sign = self.vid.get_frame()
        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            self.canvas.create_image(self.vid.width/2.5, self.vid.height/4, anchor=CENTER, image=self.photo)
            if sign != '':
                if len(sign) > 21:
                    sign = sign.split(')')[0]
                self.sign.set(sign)
                self.screen.update_idletasks()
        self.after = self.screen.after(self.sec, self.update)


if __name__ == '__main__':
    GUI()
