import time
import datetime
import calendar
import hashlib
import zipfile
import base64
import json
from io import BytesIO
import argparse
import sys
from tkinter import *
from tkinter import scrolledtext
import os
import shlex
import re
import socket

ras = {}
files = {}
vfs_data = {}
vfs_hash = ""
curr_dir = "/"
vfs_name = "default"
command_history = []
start_time = time.time()

def remove_file(args): #Удаление файла
    if not args:
        return "rm: требуется аргумент"

    filename = args[0]
    try:
        if os.path.isdir(filename):
            return f"rm: {filename}: является директорией (используйте rmdir)"
        elif os.path.exists(filename):
            os.remove(filename)
            return f"Удален файл: {filename}"
        else:
            return f"rm: {filename}: файл не существует"
    except Exception as e:
        return f"rm: ошибка удаления: {e}"

def remove_directory(args): #Удаление директории
    if not args:
        return "rmdir: требуется аргумент"

    dirname = args[0]
    try:
        if os.path.exists(dirname) and os.path.isdir(dirname):
            if not os.listdir(dirname):  # Проверяем, пуста ли директория
                os.rmdir(dirname)
                return f"Удалена директория: {dirname}"
            else:
                return f"rmdir: {dirname}: директория не пуста"
        else:
            return f"rmdir: {dirname}: нет такой директории"
    except Exception as e:
        return f"rmdir: ошибка удаления: {e}"

def show_history(): #Вывод истории команд
    global command_history
    if command_history:
        result = []
        for i, cmd in enumerate(command_history[-10:], 1):  # Последние 10 команд
            result.append(f"{i}  {cmd}")
        return "\n".join(result)
    else:
        return "История команд пуста"


def show_uptime(): #Показ времени работы системы
    global start_time
    try:
        if os.name == 'posix':  # Linux/Unix
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
        else:  # Windows
            uptime_seconds = time.time() - start_time

        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        return f"up {hours} hours, {minutes} minutes, {seconds} seconds"
    except:
        return "Не удалось получить время работы"


def show_calendar(args): #Показ календаря
    now = datetime.datetime.now()
    year = now.year
    month = now.month

    if args:
        if len(args) == 1:
            try:
                month = int(args[0])
                if month < 1 or month > 12:
                    return "cal: месяц должен быть от 1 до 12"
            except ValueError:
                return "cal: неверный формат месяца"
        elif len(args) == 2:
            try:
                month = int(args[0])
                year = int(args[1])
                if month < 1 or month > 12:
                    return "cal: месяц должен быть от 1 до 12"
            except ValueError:
                return "cal: неверный формат даты"

    try:
        return calendar.month(year, month)
    except:
        return "Ошибка отображения календаря"


def rev_text(text): #Перевод текста
    return text[::-1]

def create_def_vfs(): #Создание стандартного vfs
    global vfs_data, vfs_name, vfs_hash
    vfs_data = {
        "/": {"type": "dir", "name": "/"},
        "/home": {"type": "dir", "name": "home"},
        "/home/user": {"type": "dir", "name": "user"},
        "/home/user/documents": {"type": "dir", "name": "documents"},
        "/home/user/file1.txt": {
            "type": "file",
            "name": "file1.txt",
            "content": "Hello from VFS!\nThis is a test file.",
            "encoding": "text"
        },
        "/home/user/readme.md": {
            "type": "file",
            "name": "readme.md",
            "content": "# Virtual File System\n\nThis is a virtual file system.",
            "encoding": "text"
        },
        "/bin": {"type": "dir", "name": "bin"},
        "/bin/app": {
            "type": "file",
            "name": "app",
            "content": base64.b64encode(b"fake_binary_content").decode('utf-8'),
            "encoding": "base64"
        },
        "/motd": {
            "type": "file",
            "name": "motd",
            "content": "Welcome to Shell Emulator!\nVFS loaded successfully.",
            "encoding": "text"
        }
    }
    vfs_name = "default_vfs"
    vfs_hash = hashlib.sha256(b"default_vfs_content").hexdigest()

    if "/motd" in vfs_data: # Вывод motd при старте
        motd_content = vfs_get_file_content("/motd")
        if motd_content:
            appout(f"{motd_content}\n\n")

def load_vfs(vfs_p): #Загрузка vfs из архива
    global vfs_data, vfs_hash, vfs_name
    try:
        if not os.path.exists(vfs_p):
            raise FileNotFoundError(f"VFS файл не найден: {vfs_p}")

        with zipfile.ZipFile(vfs_p, 'r') as zipf:
            vfs_data = {"/": {"type": "dir", "name": "/"}}

            for file_i in zipf.infolist():
                path = "/" + file_i.filename

                if file_i.is_dir():
                    vfs_data[path] = {"type": "dir", "name": os.path.basename(path.rstrip("/"))}
                else:
                    content = zipf.read(file_i.filename)
                    vfs_data[path] = {
                        "type": "file",
                        "name": os.path.basename(path),
                        "content": base64.b64encode(content).decode("utf-8"),
                        "encoding": "base64"
                    }

            with open(vfs_p, "rb") as f: #Вычисление хеша
                vfs_fdata = f.read()
                vfs_hash = hashlib.sha256(vfs_fdata).hexdigest()
                vfs_name = os.path.basename(vfs_p)

            if "/motd" in vfs_data: #Показ modt при старте
                modt_cont = vfs_get_cont("/motd")
                if modt_cont:
                    appout(f"{modt_cont}\n\n")

            return True

    except zipfile.BadZipfile:
        raise ValueError(f"Неверный формат ZIP-архива: {vfs_p}")
    except Exception as e:
        raise ValueError(f"Ошибка загрузки VFS: {e}")

def get_vfs_info(): #Информация о VFS

    files_count = len([f for f in vfs_data.values() if f["type"] == "file"])
    dirs_count = len([f for f in vfs_data.values() if f["type"] == "dir"])

    return {
        "name": vfs_name,
        "hash": vfs_hash,
        "files_count": files_count,
        "dirs_count": dirs_count,
        "current_dir": curr_dir
    }


def vfs_list_directory(path=None): #Список содержимого директории VFS
    if path is None:
        path = curr_dir

    if path not in vfs_data or vfs_data[path]["type"] != "dir":
        return None

    result = []
    for file_path in vfs_data:
        if file_path != path and file_path.startswith(path): # Получаем следующий элемент после path
            remaining = file_path[len(path):].lstrip('/')
            if not remaining:
                continue

            next_part = remaining.split('/')[0]
            full_next_path = path + '/' + next_part if path != "/" else '/' + next_part

            if full_next_path not in result:
                result.append(full_next_path)

    return sorted(result)


def vfs_change_directory(path): #Смена текущей директории VFS
    global curr_dir

    if path == "..": # Переход на уровень выше
        if curr_dir != "/":
            parts = curr_dir.rstrip('/').split('/')
            curr_dir = '/' + '/'.join(parts[:-1]) if len(parts) > 1 else "/"
        return True
    elif path == ".":
        return True
    elif path.startswith("/"): # Абсолютный путь
        target = path
    else: # Относительный путь
        target = os.path.join(curr_dir, path).replace('\\', '/')
        if target == "":
            target = "/"

    if target in vfs_data and vfs_data[target]["type"] == "dir":
        curr_dir = target
        return True

    return False


def vfs_get_file_content(path): #Получение содержимого файла VFS
    if path in vfs_data and vfs_data[path]["type"] == "file":
        file_i = vfs_data[path]
        if file_i["encoding"] == "base64":
            try:
                return base64.b64decode(file_i["content"]).decode('utf-8', errors='ignore')
            except:
                return "[Binary content]"
        else:
            return file_i["content"]
    return None


def vfs_init_command(): #Команда vfs-init - сброс к VFS по умолчанию
    global vfs_data, curr_dir
    create_def_vfs()
    curr_dir = "/"
    return "VFS инициализирована по умолчанию"

def begin(scr_p):
    try:
        with open(scr_p, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines: #Пропуск пустых строк и комментариев
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            appout(f"$ {line}\n")
            try: #Проверка на ошибки
                result = emulate(line)
                if result:
                    appout(result + "\n")
            except Exception as e:
                appout(f"Ошибка выполнения скрипта: {e} \n")
                break

    except FileNotFoundError:
        appout(f"Ошибка: скрипт {scr_p} не найден\n")
    except Exception as e:
        appout(f"Ошибка чтения скрипта: {e} \n")

def parse(commline):  # Парсер
    if not commline.strip():
        return []
    newline = opentilde(commline)  # Раскрытие тильды (~)

    newline = openvars(newline)  # Раскрытие переменных

    el = split(newline)  # Разбиение строки

    return el


def opentilde(text):  # Раскрытие тильды (~)
    return re.sub(r'(\\?)(~)', reptilde, text)


def reptilde(match):  # Экранирование тильды (~)
    if match.group(1):
        return match.group(0)[1:]
    return ras.get('HOME', '~')


def openvars(text):  # Раскрытие переменных
    pattern = r'(\\?)(\$([A-Za-z_][A-Za-z0-9_]*)|\$\{([^}]*)\})'
    return re.sub(pattern, repvars, text)


def repvars(match):  # Если не экранировано - убираем $
    if match.group(1):
        return match.group(0)[1:]  # Убираем /
    vname = match.group(2) or match.group(3)

    # Спец случаи
    if vname == "$":
        return str(os.getpid())
    elif vname == "?":
        return "0"

    return ras.get(vname, "")  # Поиск среди переменных окружения


def split(text):  # Разбиение строки
    try:
        return shlex.split(text)
    except ValueError as e:
        raise ValueError(f"Ошибка парсинга: {e}")


def setras(name, value):  # установка переменной окружения
    ras[name] = value


def unsetras(name):  # снос переменной окуржения
    if name in ras:
        del ras[name]


def execute(event):
    comm = inpt.get()
    inpt.delete(0, END)
    appout(f"$ {comm}\n")
    try:
        res = emulate(comm)
        appout(res + "\n")
    except Exception as e:
        appout(f"Error: {e}\n")


def emulate(comm):  # Эмуляция выполнения команд
    global command_history
    command_history.append(comm)

    try:  # Раскрытие переменных
        args = parse(comm)

        if not args:
            return ""
        command = args[0]
        arguments = args[1:]

        # выполнение команд
        if command == "echo":
            return " ".join(arguments)
        elif command == "pwd":
            return os.getcwd()
        elif command == "whoami":
            return os.getlogin()
        elif command == "hostname":
            return socket.gethostname()
        elif command == "env":
            return "\n".join([f"{k}={v}" for k, v in ras.items()])
        elif command == "export":
            if arguments and '=' in arguments[0]:
                var, value = arguments[0].split('=', 1)
                setras(var, value)
                return f"Exported {var}={value}"
            else:
                return "Usage: export VAR=value"
        elif command == "unset":
            if arguments:
                unsetras(arguments[0])
                return f"Unset {arguments[0]}"
            else:
                return "Usage: unset VAR"
        elif command == "cd":
            return changedir(arguments)
        elif command == "ls":
            return listdir(arguments)
        elif command == "vfs-info":
            info = get_vfs_info()
            return f"VFS: {info['name']}\nSHA-256: {info['hash']}\nФайлов: {info['files_count']}\nПапок: {info['dirs_count']}\nТекущая директория: {info['current_dir']}"
        elif command == "vfs-ls":
            path = None
            if arguments:
                path = arguments[0]
            items = vfs_list_directory(path)
            if items is None:
                return f"vfs-ls: {path if path else curr_dir}: Нет такой директории"
            result = []
            for item in items:
                name = item.split('/')[-1]
                if vfs_data[item]["type"] == "dir":
                    result.append(f"{name}/")
                else:
                    result.append(name)
            return "  ".join(result) if result else "Директория пуста"
        elif command == "vfs-cd":
            if not arguments:
                return "vfs-cd: требуется аргумент"

            if vfs_change_directory(arguments[0]):
                return f"Текущая VFS директория: {curr_dir}"
            else:
                return f"vfs-cd: {arguments[0]}: Нет такой директории"
        elif command == "vfs-cat":
            if not arguments:
                return "vfs-cat: требуется аргумент"
            content = vfs_get_file_content(arguments[0])
            if content is not None:
                return content
            else:
                return f"vfs-cat: {arguments[0]}: Нет такого файла"
        elif command == "vfs-init":
            return vfs_init_command()
        elif command == "history":
            return show_history()
        elif command == "uptime":
            return show_uptime()
        elif command == "cal":
            return show_calendar(arguments)
        elif command == "rev":
            if arguments:
                return rev_text(" ".join(arguments))
            else:
                return "rev: требуется аргумент"
        elif command == "rm":
            return remove_file(arguments)
        elif command == "rmdir":
            return remove_directory(arguments)
        elif command == "exit":
            return exitem(arguments)
        elif command == "help":
            return """Доступные команды:
echo [text] - вывод текста
pwd - текущая директория
whoami - текущий пользователь
hostname - имя хоста
env - переменные окружения
export VAR=value - установка переменной
unset VAR - удаление переменной
cd [dir] - сменить директорию
ls [dir] - список файлов и папок
vfs-info - информация о VFS
vfs-ls [dir] - список файлов в VFS
vfs-cd [dir] - сменить директорию в VFS
vfs-cat [file] - показать содержимое файла VFS
vfs-init - сбросить VFS к состоянию по умолчанию
history - история команд
uptime - время работы системы
cal [month] [year] - календарь
rev [text] - перевернуть текст
rm [file] - удалить файл
rmdir [dir] - удалить директорию
exit - выход из программы
help - эта справка
"""
        else:
            return f"Команда '{command}' не найдена. Введите 'help' для списка команд."
    except Exception as e:
        return f"Ошибка выполнения: {e}"


def openpath(dir):  # Раскрытие тильды и переменных
    if dir == "~":
        return ras.get('HOME', os.getcwd())
    elif dir.startswith("~/"):
        return os.path.join(ras.get('HOME', os.getcwd()), dir[2:])
    return dir


def changedir(args):  # Реализация cd
    try:
        if not args:  # Если cd без аргумента
            newdir = ras.get('HOME', os.getcwd())
        else:
            newdir = args[0]

        newdir = openpath(newdir)

        # Смена директории
        os.chdir(newdir)

        # Обновление PWD
        ras['PWD'] = os.getcwd()

        return f"Новая директория: {os.getcwd()}"

    except FileNotFoundError:
        return f"cd: {newdir}: Нет данного файла или директории"
    except PermissionError:
        return f"cd: {newdir}: В доступе отказано"
    except Exception as e:
        return f"cd: {str(e)}"


def listdir(args):  # Реализация ls
    try:
        if not args:
            target = "."
        else:
            target = args[0]

        target = openpath(target)

        things = os.listdir(target)  # список файлов и директорий

        # Формирования вывода
        result = []
        for thing in sorted(things):
            fpath = os.path.join(target, thing)
            if os.path.isdir(fpath):
                result.append(f"{thing}/")
            else:
                result.append(thing)

        return "  ".join(result) if result else "Директория пуста"
    except FileNotFoundError:
        return f"ls: невозможно получить доступ '{args[0]}': Нет данного файла или директории"
    except PermissionError:
        return f"ls: невозможно открыть директорию '{args[0]}': В доступе отказано"
    except Exception as e:
        return f"ls: {str(e)}"


def exitem(args):  # Реализация exit
    try:
        excode = 0
        if args:  # Попытка получить код выхода
            excode = int(args[0])

        appout(f"Выход из эмулятора с кодом {excode}\n")

        window.after(1000, lambda: window.destroy())  # время на чтение сообщения
        return None
    except ValueError:
        return "Необхожим численный аргумент"

def run(vfs_p, scr_p):
    global ras
    ras = dict(os.environ)  # Словарь переменных окружения
    ras["PWD"] = os.getcwd()  # Добавляем текущую директорию

    print("=== >Параметры эмулятора< ===")
    print(f"Путь к VFS: {vfs_p}")
    print(f"Путь к скрипту: {scr_p}\n")
    print("===============================")

    if vfs_p:
        try:
            load_vfs(vfs_p)
            appout(f"VFS загружена из: {vfs_p}\n\n")
        except Exception as e:
            appout(f"Ошибка загрузки VFS: {e}\n")
            create_def_vfs()
            appout("Используется VFS по умолчанию\n\n")
    else:
        create_def_vfs()
        appout("Используется VFS по умолчанию\n\n")

    if scr_p:
        begin(scr_p)

def appout(text):
    outpt.config(state=NORMAL)
    outpt.insert(END, text)
    outpt.see(END)
    outpt.config(state=DISABLED)

def main():
    parser = argparse.ArgumentParser(description="Эмулятор командной оболочки")
    parser.add_argument("--vfs", help="Путь к физическому расположению VFS")
    parser.add_argument("--script", help="Путь к стартовому скрипту")

    args = parser.parse_args()

    run(vfs_p = args.vfs, scr_p = args.script)

window = Tk()  # имя и размер окна
window.title("Эмулятор - " + os.getlogin() + "@" + socket.gethostname())
window.geometry("800x600")

outpt = scrolledtext.ScrolledText(window, wrap=WORD, bg='black', fg='white',
                                  font=('Courier', 12))  # оформление окна
outpt.pack(expand=True, fill='both')
outpt.config(state=DISABLED)

inpt = Entry(window, bg='black', fg='white', font=('Arial', 14), insertbackground='white')  # оформление ввода
inpt.pack(fill='x')
inpt.bind('<Return>', execute)
inpt.focus()

if __name__ == "__main__":
    main()
    window.mainloop()