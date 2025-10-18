import argparse
import sys
from tkinter import *
from tkinter import scrolledtext
import os
import shlex
import re
import socket

ras = {}

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
exit - выход из программы
help - эта справка"""
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