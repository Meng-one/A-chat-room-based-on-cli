import socket
import threading
import json
import curses
from curses import wrapper
import locale


class Client:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__id = None
        self.__nickname = None
        self.__isLogin = False
        self.input_window = None
        self.chat_window = None
        self.max_lines = 0
        self.current_line = 0

        # 添加以下行
        locale.setlocale(locale.LC_ALL, '')
        code = locale.getpreferredencoding()
        curses.start_color()
        curses.use_default_colors()

    def __receive_message_thread(self):
        while self.__isLogin:
            try:
                buffer = self.__socket.recv(1024).decode()
                obj = json.loads(buffer)
                self.display_message(
                    f"[{obj['sender_nickname']}({obj['sender_id']})] {obj['message']}")
            except Exception:
                self.display_message("[Client] 无法从服务器获取数据")

    def __send_message_thread(self, message):
        self.__socket.send(json.dumps({
            'type': 'broadcast',
            'sender_id': self.__id,
            'message': message
        }).encode())

    def start(self):
        self.__socket.connect(('127.0.0.1', 8888))
        self.setup_windows()
        self.main_loop()

    def setup_windows(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        self.chat_window = curses.newwin(height - 3, width, 0, 0)
        self.input_window = curses.newwin(3, width, height - 3, 0)
        self.max_lines = height - 4
        self.chat_window.scrollok(True)
        self.input_window.keypad(True)
        self.refresh_windows()

    def refresh_windows(self):
        self.chat_window.refresh()
        self.input_window.refresh()

    def display_message(self, message):
        self.chat_window.addstr(self.current_line, 0, message)
        if self.current_line < self.max_lines:
            self.current_line += 1
        else:
            self.chat_window.scroll(1)
        self.refresh_windows()

    def display_message(self, message):
        try:
            self.chat_window.addstr(self.current_line, 0, message)
            if self.current_line < self.max_lines:
                self.current_line += 1
            else:
                self.chat_window.scroll(1)
            self.refresh_windows()
        except curses.error:
            pass  # 忽略因窗口大小导致的错误

    def main_loop(self):
        curses.noecho()
        curses.cbreak()
        self.input_window.keypad(True)

        while True:
            self.input_window.clear()
            self.input_window.addstr(0, 0, "> ")
            self.input_window.refresh()

            command = ""
            cursor_x = 2

            while True:
                try:
                    char = self.input_window.get_wch()

                    if isinstance(char, str) and ord(char) == 10:  # Enter key
                        break
                    elif isinstance(char, int) and char in (10, curses.KEY_ENTER):  # Enter key
                        break
                    elif isinstance(char, str):
                        self.input_window.addstr(char)
                        command += char
                        cursor_x += 1
                    elif isinstance(char, int):
                        if char in (127, 8, curses.KEY_BACKSPACE):  # Backspace
                            if cursor_x > 2:
                                cursor_x -= 1
                                self.input_window.move(0, cursor_x)
                                self.input_window.delch()
                                command = command[:-1]
                        elif char == curses.KEY_LEFT:
                            if cursor_x > 2:
                                cursor_x -= 1
                                self.input_window.move(0, cursor_x)
                        elif char == curses.KEY_RIGHT:
                            if cursor_x < 2 + len(command):
                                cursor_x += 1
                                self.input_window.move(0, cursor_x)

                    self.input_window.refresh()
                except curses.error:
                    pass

            command = command.strip()

            if command.startswith("login "):
                self.login(command[6:])
            elif command.startswith("send "):
                self.send(command[5:])
            elif command == "logout":
                self.logout()
                break
            elif command == "help":
                self.display_help()
            else:
                self.display_message("[Client] 未知命令，请使用 'help' 查看可用命令")

    def login(self, nickname):
        self.__socket.send(json.dumps({
            'type': 'login',
            'nickname': nickname
        }).encode())
        try:
            buffer = self.__socket.recv(1024).decode()
            obj = json.loads(buffer)
            if obj['id']:
                self.__nickname = nickname
                self.__id = obj['id']
                self.__isLogin = True
                self.display_message("[Client] 成功登录到聊天室")

                thread = threading.Thread(target=self.__receive_message_thread)
                thread.daemon = True
                thread.start()
            else:
                self.display_message("[Client] 无法登录到聊天室")
        except Exception:
            self.display_message("[Client] 无法从服务器获取数据")

    def send(self, message):
        if not self.__isLogin:
            self.display_message("[Client] 请先登录")
            return
        self.display_message(f"[{self.__nickname}({self.__id})] {message}")
        thread = threading.Thread(
            target=self.__send_message_thread, args=(message,))
        thread.daemon = True
        thread.start()

    def logout(self):
        if self.__isLogin:
            self.__socket.send(json.dumps({
                'type': 'logout',
                'sender_id': self.__id
            }).encode())
            self.__isLogin = False
        self.display_message("[Client] 已退出聊天室")

    def display_help(self):
        self.display_message("[Help] login nickname - 登录到聊天室，nickname是你选择的昵称")
        self.display_message("[Help] send message - 发送消息，message是你输入的消息")
        self.display_message("[Help] logout - 退出聊天室")
        self.display_message("[Help] help - 显示帮助信息")


def main(stdscr):
    curses.curs_set(1)
    client = Client(stdscr)
    client.start()


if __name__ == "__main__":
    wrapper(main)
