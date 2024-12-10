import socket
import threading
import tkinter as tk
from tkinter import simpledialog, ttk
import os
import time

# Константы
BROADCAST_IP = "255.255.255.255"
PORT = 12345
BUFFER_SIZE = 1024
CHAT_DIRECTORY = "chats"  # Папка для хранения переписок
STATUS_FILE = "user_status.txt"  # Файл для хранения статуса пользователя
USERNAME_FILE = "username.txt"  # Файл для хранения имени пользователя

# Убедитесь, что папка для переписок существует
if not os.path.exists(CHAT_DIRECTORY):
    os.makedirs(CHAT_DIRECTORY)

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat")
        
        # Загружаем имя пользователя
        self.username = self.load_username()

        # Основные фреймы
        self.left_frame = tk.Frame(root, width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        self.right_frame = tk.Frame(root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Список пользователей с их статусами
        tk.Label(self.left_frame, text="Пользователи:", anchor="w").pack(fill=tk.X, padx=5, pady=5)

        # Используем Treeview для отображения пользователей и их статусов
        self.user_tree = ttk.Treeview(self.left_frame, columns=("Status", "Username"), show="headings", height=20)
        self.user_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Добавляем столбцы для отображения статусов
        self.user_tree.heading("Status", text="Статус")
        self.user_tree.heading("Username", text="Имя пользователя")
        self.user_tree.column("Status", width=100)
        self.user_tree.column("Username", width=150)

        # Окно сообщений
        self.chat_window = tk.Text(self.right_frame, state="disabled", wrap="word", height=15)
        self.chat_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Ввод сообщения
        self.message_entry = tk.Entry(self.right_frame)
        self.message_entry.pack(fill=tk.X, padx=5, pady=5)
        self.message_entry.bind("<Return>", self.send_message)

        # Сокеты
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", PORT))

        # Статус пользователя
        self.user_status = {}
        self.user_status[self.username] = "online"  # Статус текущего пользователя

        # Потоки
        threading.Thread(target=self.receive_messages, daemon=True).start()
        threading.Thread(target=self.broadcast_presence, daemon=True).start()

        # Таймер для обновления статусов
        self.root.after(5000, self.update_user_list)  # Каждые 5 секунд обновляем статус

    def load_username(self):
        """Загружаем имя пользователя из файла или запрашиваем его, если файла нет."""
        if os.path.exists(USERNAME_FILE):
            with open(USERNAME_FILE, "r") as f:
                return f.read().strip()
        else:
            username = simpledialog.askstring("Имя пользователя", "Введите ваше имя:")
            if username:
                with open(USERNAME_FILE, "w") as f:
                    f.write(username)
                return username
            else:
                return "Аноним"

    def broadcast_presence(self):
        """Отправка широковещательного сообщения для обнаружения пользователей."""
        while True:
            # Отправка актуального статуса с именем пользователя
            presence_message = f"PRESENCE:{self.username}:{self.user_status[self.username]}"
            self.sock.sendto(presence_message.encode("utf-8"), (BROADCAST_IP, PORT))
            print(f"Sent broadcast: {presence_message}")  # Отладочный вывод
            time.sleep(2)  # Обновление каждые 2 секунды

    def receive_messages(self):
        """Обработка входящих сообщений."""
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8")
                
                # Для отладки: выведите сообщение и адрес
                print(f"Received message: {message} from {addr}")

                # Обработка разных типов сообщений
                if message.startswith("PRESENCE:"):
                    parts = message.split(":")
                    username = parts[1]
                    status = parts[2]
                    self.user_status[username] = status
                    self.update_user_list()
                else:
                    self.add_message(message)
            except Exception as e:
                self.add_message(f"Ошибка: {e}")

    def update_user_list(self):
        """Обновление списка пользователей в интерфейсе."""
        # Очищаем текущий список пользователей
        for row in self.user_tree.get_children():
            try:
                self.user_tree.delete(row)
            except tk.TclError:
                # Игнорируем ошибку, если строка уже удалена
                pass

        # Добавляем новых пользователей и их статусы
        for user, status in self.user_status.items():
            # Заменяем изображения на текст
            status_text = self.get_status_text(status)

            # Вставляем статус перед именем пользователя
            self.user_tree.insert("", "end", values=(status_text, user))

        # Повторный запуск после 5 секунд
        self.root.after(5000, self.update_user_list)

    def get_status_text(self, status):
        """Возвращает текстовый статус для отображения."""
        if status == "online":
            return "Онлайн"
        elif status == "away":
            return "Отошел"
        elif status == "offline":
            return "Отключен"
        else:
            return "Неизвестен"

    def select_user(self, event):
        """Выбор пользователя для общения."""
        selected_item = self.user_tree.selection()
        if selected_item:
            selected_user = self.user_tree.item(selected_item)["values"][1]  # Имя пользователя
            self.load_chat(selected_user)

    def send_message(self, event=None):
        """Отправка сообщения выбранному пользователю."""
        if not self.selected_user:
            self.add_message("Выберите пользователя для отправки сообщения.")
            return

        message = self.message_entry.get().strip()
        if message:
            self.message_entry.delete(0, tk.END)
            full_message = f"{self.username}: {message}"
            
            # Отправка сообщения выбранному пользователю
            user_ip, user_port = self.users[self.selected_user]
            self.sock.sendto(full_message.encode("utf-8"), (user_ip, user_port))
            
            self.add_message(f"Вы -> {self.selected_user}: {message}")

    def add_message(self, message):
        """Добавление сообщения в окно чата."""
        self.chat_window.config(state="normal")
        self.chat_window.insert(tk.END, f"{message}\n")
        self.chat_window.config(state="disabled")
        self.chat_window.see(tk.END)

    def load_chat(self, user):
        """Загрузка переписки с выбранным пользователем."""
        chat_file = self.get_chat_file(user)
        if os.path.exists(chat_file):
            with open(chat_file, "r", encoding="utf-8") as f:
                chat_history = f.read()
            self.chat_window.config(state="normal")
            self.chat_window.delete(1.0, tk.END)  # Очистить текущее окно чата
            self.chat_window.insert(tk.END, chat_history)
            self.chat_window.config(state="disabled")

    def save_chat(self, user, message):
        """Сохранение сообщения в файл переписки."""
        chat_file = self.get_chat_file(user)
        with open(chat_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def get_chat_file(self, user):
        """Получение пути к файлу переписки с выбранным пользователем."""
        chat_file = os.path.join(CHAT_DIRECTORY, f"{min(self.username, user)}_{max(self.username, user)}.txt")
        return chat_file

    def update_status(self, status):
        """Обновление статуса пользователя."""
        self.user_status[self.username] = status
        self.update_user_list()

# Запуск приложения
root = tk.Tk()
app = ChatApp(root)
root.mainloop()
