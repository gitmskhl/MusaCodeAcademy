import os

def count_python_lines(start_dir="."):
    # Папки, которые нужно пропустить
    ignored_dirs = {
        ".venv", "venv", "env", "virtualenv",  # Виртуальные окружения
        ".git", ".github",                    # Git-репозитории
        "__pycache__", ".pytest_cache",       # Кэш Python и тестов
        ".idea", ".vscode"                    # Настройки IDE
    }

    total_lines = 0
    total_code_lines = 0
    file_count = 0

    print("Анализ Python файлов...\n")
    print(f"{'Файл':<50} | {'Всего строк':<12} | {'Чистый код':<12}")
    print("-" * 80)

    for root, dirs, files in os.walk(start_dir):
        # Исключаем ненужные папки "на лету", чтобы os.walk в них не заходил
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                file_count += 1
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        
                        lines_count = len(lines)
                        code_lines_count = 0
                        
                        for line in lines:
                            stripped = line.strip()
                            # Пропускаем пустые строки и комментарии
                            if stripped and not stripped.startswith("#"):
                                code_lines_count += 1
                                
                        total_lines += lines_count
                        total_code_lines += code_lines_count
                        
                        # Выводим относительный путь для красоты
                        rel_path = os.path.relpath(file_path, start_dir)
                        # Ограничиваем длину строки в выводе, если путь слишком длинный
                        if len(rel_path) > 47:
                            rel_path = "..." + rel_path[-44:]
                        print(f"{rel_path:<50} | {lines_count:<12} | {code_lines_count:<12}")
                        
                except (UnicodeDecodeError, PermissionError):
                    # На случай, если файл поврежден или нет прав доступа
                    print(f"[Ошибка чтения] {os.path.relpath(file_path, start_dir)}")

    print("-" * 80)
    print(f"Всего найдено .py файлов: {file_count}")
    print(f"Суммарно строк (с комментариями и пустыми): {total_lines}")
    print(f"Чистого кода (без пустых строк и #): {total_code_lines}")

if __name__ == "__main__":
    # Запуск в текущей директории
    count_python_lines()