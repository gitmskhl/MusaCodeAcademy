"""Function exercises use direct calls, matching the reviewed Google Docs examples."""
import hashlib
import json

FUNCTION_TEST_PREFIX = '# mca:function-test:v1\n'
PASSWORD_HASH = 'e9d36981609f2623858def80258e2e627ec3fe4c54deeee3bab480deba7a801e'
PASSWORD_CHECKER = '''import hashlib


def check_password(your_password):
    hash_ = "e9d36981609f2623858def80258e2e627ec3fe4c54deeee3bab480deba7a801e"
    hash_object = hashlib.sha256(your_password.encode('utf-8'))
    hash_result = hash_object.hexdigest()
    return hash_ == hash_result
'''
PASSWORD_STARTER = PASSWORD_CHECKER + '''

def find_password():
    # Перебери варианты и верни строку, для которой check_password() даёт True.
    pass
'''
PASSWORD_REFERENCE = PASSWORD_CHECKER + '''

def find_password():
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    for a in alphabet:
        if check_password(a):
            return a
    for a in alphabet:
        for b in alphabet:
            candidate = a + b
            if check_password(candidate):
                return candidate
    for a in alphabet:
        for b in alphabet:
            for c in alphabet:
                candidate = a + b + c
                if check_password(candidate):
                    return candidate
    for a in alphabet:
        for b in alphabet:
            for c in alphabet:
                for d in alphabet:
                    candidate = a + b + c + d
                    if check_password(candidate):
                        return candidate
'''


def text(value):
    return {'type': 'text', 'data': {'text': value}}


def code(value):
    return {'type': 'code', 'data': {'language': 'python', 'code': value}}


def console(value):
    return {'type': 'console', 'data': {'lines': [
        {'type': 'output', 'text': line} for line in value.splitlines()]}}


def function_tasks(ns):
    """Replace stdin adapters with independently checked function contracts."""
    add, key = ns['add'], ns['key']

    def task(doc, number, title, signature, statement, solution, cases, example, *,
             prints=False, unchanged=False, explanation=None):
        name = signature.split('(')[0]
        test_rows = []
        for args, expected in cases:
            payload = {'function': name, 'args': args, 'mode': 'print' if prints else 'return',
                       'expected': expected, 'unchanged_args': unchanged}
            rendered = expected if prints else str(expected) + '\n'
            test_rows.append((FUNCTION_TEST_PREFIX + json.dumps(payload, ensure_ascii=False), rendered))
        add(doc, number, title, statement, '', '', solution, test_rows)
        exercise = ns['EXERCISES'][key(doc, number)]
        blocks = [text(statement), text('### Пример работы 1'), code(example),
                  text('На экране появится:'), console(test_rows[0][1])]
        if explanation:
            blocks.append(text(explanation))
        blocks.append({'type': 'callout', 'data': {
            'variant': 'info', 'title': 'Как отправить решение',
            'content': 'Напиши определение функции' + (' и вспомогательных функций' if name == 'first_a_last_c' else '') +
                       '. Проверка сама вызовет её с разными аргументами. Пример вызова нужен для самостоятельной проверки; в решение его добавлять не требуется.'}})
        exercise['content']['blocks'] = blocks

    task(35, 1, 'Функция, которая выводит максимум', 'max2(a, b)',
         'Создай функцию `max2(a, b)`, которая принимает два числа и выводит на экран большее из них.\n\nЕсли числа равны, выведи это число один раз.',
         'def max2(a, b):\n    print(max(a, b))',
         [([5,12],'12\n'), ([-5,-2],'-2\n'), ([7,7],'7\n'), ([0,-1],'0\n')],
         'max2(5, 12)', prints=True)
    task(35, 2, 'Функция для вывода положительных чисел', 'show_positive(numbers)',
         'Создай функцию `show_positive(numbers)`, которая принимает список чисел и выводит только положительные числа — те, которые больше нуля.\n\nВыводи каждое число с новой строки, сохраняя их порядок. Если положительных чисел нет, функция ничего не выводит.',
         '''def show_positive(numbers):
    for number in numbers:
        if number > 0:
            print(number)''',
         [([[3,-2,6,0,-5,8]],'3\n6\n8\n'), ([[-1,0]],''), ([[]],''), ([[1,1]],'1\n1\n')],
         'numbers = [3, -2, 6, 0, -5, 8]\nshow_positive(numbers)', prints=True)
    task(36, 1, 'Возвращаем максимум двух чисел', 'max2(a, b)',
         'Создай функцию `max2(a, b)`, которая принимает два числа и возвращает большее из них. Если числа равны, верни любое из них.\n\nРезультат нужно вернуть с помощью `return`.',
         'def max2(a, b):\n    return max(a, b)',
         [([4,12],12), ([5,-5],5), ([-9,-3],-3), ([0,0],0)],
         'result = max2(4, 12)\nprint(result)')
    task(36, 2, 'Разворот строки или списка', 'reverse(value)',
         'Создай функцию `reverse(value)`, которая принимает строку или список и возвращает их в обратном порядке.\n\nДля строки верни строку, для списка — новый список. Исходный список не изменяй. Строка или список могут быть пустыми.',
         'def reverse(value):\n    return value[::-1]',
         [(['hello'],'olleh'), ([[1,2,3]],[3,2,1]), ([''],''), ([[]],[]), (['а б'],'б а')],
         'result = reverse("hello")\nprint(result)', unchanged=True,
         explanation='Так же можно передать список: `reverse([1, 2, 3])` вернёт `[3, 2, 1]`.\n\nПодсказка: срез `value[::-1]` создаёт перевёрнутую копию последовательности.')
    task(36, 3, 'Новый список положительных чисел', 'make_positive(numbers)',
         'Создай функцию `make_positive(numbers)`, которая принимает список чисел и возвращает новый список только с положительными числами — теми, которые больше нуля.\n\nСохрани порядок и повторы чисел. Исходный список не изменяй. Если подходящих чисел нет, верни пустой список.',
         '''def make_positive(numbers):
    result = []
    for number in numbers:
        if number > 0:
            result.append(number)
    return result''',
         [([[3,-1,6,-34,8]],[3,6,8]), ([[-1,0]],[]), ([[]],[]), ([[2,2,1]],[2,2,1])],
         'old_list = [3, -1, 6, -34, 8]\nnew_list = make_positive(old_list)\nprint(new_list)', unchanged=True)
    task(37, 1, 'Минимум трёх чисел', 'min3(a, b, c)',
         'Создай функцию `min3(a, b, c)`, которая принимает три числа и возвращает наименьшее из них.',
         'def min3(a, b, c):\n    return min(a, b, c)',
         [([5,2,8],2), ([-5,-2,-8],-8), ([0,0,0],0), ([1,2,3],1)],
         'result = min3(5, 2, 8)\nprint(result)')
    task(37, 2, 'Функция подсчёта буквы', 'count_letter(text, letter)',
         'Создай функцию `count_letter(text, letter)`, которая принимает строку и одну букву и возвращает, сколько раз эта буква встречается в строке.\n\nУчитывай регистр: «А» и «а» — разные буквы. Текст может быть пустым.',
         'def count_letter(text, letter):\n    return text.count(letter)',
         [(['на улице хорошая погода','о'],4), (['АаА','а'],1), (['','я'],0), (['кот','в'],0), (['аааа','а'],4)],
         'result = count_letter("на улице хорошая погода", "о")\nprint(result)',
         explanation='Буква «о» встречается четыре раза: дважды в слове «хорошая» и дважды в слове «погода».')
    task(37, 3, 'Склеиваем части двух слов', 'concat2(first, second)',
         'Создай функцию `concat2(first, second)`, которая принимает два слова и возвращает новое слово из первых двух букв первого слова и последних двух букв второго.\n\nВ каждом слове не меньше двух букв.',
         'def concat2(first, second):\n    return first[:2] + second[-2:]',
         [(['полиция','штукатурка'],'пока'), (['аб','вг'],'абвг'), (['Python','code'],'Pyde'), (['море','небо'],'мобо')],
         'word = concat2("полиция", "штукатурка")\nprint(word)',
         explanation='Первые две буквы слова «полиция» — «по», последние две буквы слова «штукатурка» — «ка». Получается «пока».')
    task(38, 1, 'Ровно две буквы «а»', 'count_2(text)',
         'Создай функцию `count_2(text)`, которая принимает текст и возвращает:\n\n- `True`, если в тексте ровно две строчные русские буквы «а»;\n- `False` во всех остальных случаях.\n\nЗаглавную «А» и латинскую `a` не учитывай. Текст может быть пустым.',
         'def count_2(text):\n    return text.count("а") == 2',
         [(['Привет как дела?'],True), (['ааа'],False), (['Ааа'],True), ([''],False), (['aa'],False)],
         'result = count_2("Привет как дела?")\nprint(result)')
    task(38, 2, 'Среднее арифметическое в функции', 'average(numbers)',
         'Создай функцию `average(numbers)`, которая принимает непустой список чисел и возвращает их среднее арифметическое: сумму чисел, делённую на их количество.\n\nДля подсчёта суммы используй встроенную функцию `sum()`.',
         'def average(numbers):\n    return sum(numbers) / len(numbers)',
         [([[5,1,7,2]],3.75), ([[4]],4.0), ([[-4,4]],0.0), ([[-3,-6]],-4.5)],
         'numbers = [5, 1, 7, 2]\nresult = average(numbers)\nprint(result)',
         explanation='Сумма чисел: 5 + 1 + 7 + 2 = 15. В списке четыре числа, поэтому среднее равно 15 / 4 = 3.75.')
    task(38, 3, 'Числа выше среднего', 'above_average(numbers)',
         'Создай функцию `above_average(numbers)`, которая принимает непустой список чисел и возвращает новый список с числами, которые строго больше среднего арифметического исходного списка.\n\nСохрани порядок и повторы чисел. Исходный список не изменяй. Если подходящих чисел нет, верни пустой список.',
         '''def above_average(numbers):
    average = sum(numbers) / len(numbers)
    result = []
    for number in numbers:
        if number > average:
            result.append(number)
    return result''',
         [([[2,1,6,9,3]],[6,9]), ([[4,4]],[]), ([[-5,-3,-1]],[-1]), ([[0,2,2]],[2,2]), ([[7]],[])],
         'numbers = [2, 1, 6, 9, 3]\nnew_list = above_average(numbers)\nprint(new_list)', unchanged=True,
         explanation='Среднее равно (2 + 1 + 6 + 9 + 3) / 5 = 4.2. Только 6 и 9 больше 4.2, поэтому они попали в новый список.')
    first = '''def first_letter_a(text):
    result = []
    for word in text.split():
        if word.startswith("а"):
            result.append(word)
    return result'''
    last = '''def last_letter_c(words):
    result = []
    for word in words:
        if word.endswith("с"):
            result.append(word)
    return result'''
    common = '\n\nСохрани порядок и повторы слов. Учитывай регистр: нужны строчные русские буквы. Знаки препинания считай частью слова.'
    task(39, 1, 'Слова на букву «а»', 'first_letter_a(text)',
         'Создай функцию `first_letter_a(text)`, которая принимает текст и возвращает список слов, начинающихся на букву «а». Разделяй текст на слова по пробельным символам.' + common,
         first,
         [(['На столе лежит абрикос и ароматный кофе.'],['абрикос','ароматный']), (['Аист ананас арбуз'],['ананас','арбуз']), ([''],[]), (['кот дом'],[]), (['а а'],['а','а'])],
         'words = first_letter_a("На столе лежит абрикос и ароматный кофе.")\nprint(words)')
    task(39, 2, 'Слова с последней буквой «с»', 'last_letter_c(words)',
         'Создай функцию `last_letter_c(words)`, которая принимает список слов и возвращает новый список тех слов, которые оканчиваются на букву «с».' + common,
         last,
         [(['алекс очень любит кушать абрикос и ананас'.split()],['алекс','абрикос','ананас']), ([['с','С','c']],['с']), ([['лес,','лес']],['лес']), ([[]],[]), ([['кот']],[])],
         'words = ["алекс", "очень", "любит", "кушать", "абрикос", "и", "ананас"]\nnew_words = last_letter_c(words)\nprint(new_words)')
    task(39, 3, 'Объединяем две функции', 'first_a_last_c(text)',
         'Создай функцию `first_a_last_c(text)`, которая принимает текст и возвращает список слов, начинающихся на «а» и оканчивающихся на «с».\n\nВоспользуйся функциями `first_letter_a(text)` и `last_letter_c(words)` из предыдущих задач: добавь их определения в решение и вызови обе внутри `first_a_last_c()`. Разделяй текст на слова по пробельным символам.' + common,
         first + '\n\n' + last + '\n\ndef first_a_last_c(text):\n    return last_letter_c(first_letter_a(text))',
         [(['атлас показывает страны, а абакус упрощает подсчеты в уме'],['атлас','абакус']), (['Атлас ананас абрикос,'],['ананас']), ([''],[]), (['а с ас ас'],['ас','ас']), (['кот'],[])],
         'text = "атлас показывает страны, а абакус упрощает подсчеты в уме"\nwords = first_a_last_c(text)\nprint(words)')

    if len(ns['DOCS']) > 39:
        password_task(ns)


def password_task(ns):
    statement = ('Создай функцию `find_password()`, которая перебирает варианты учебного пароля и возвращает найденный пароль строкой. '
                 'Для проверки каждого варианта вызывай готовую функцию `check_password(candidate)`: она возвращает `True` для правильного пароля и `False` для остальных.\n\n'
                 '1. Пароль содержит от одного до четырёх символов. Каждый символ — строчная латинская буква `a–z` или цифра `0–9`. Символы могут повторяться.\n\n'
                 '2. Проверь варианты всех четырёх длин. Как только найдёшь подходящий, верни его с помощью `return`.\n\n'
                 '3. Используй функцию `check_password()` из заготовки без изменений. В проверке пароль может быть другим, но всегда соответствует этим правилам.')
    cases = []
    for digest in [PASSWORD_HASH] + [hashlib.sha256(s.encode()).hexdigest() for s in ['7','az','00a','9999']]:
        payload = {'function': 'find_password', 'args': [], 'mode': 'password', 'hash': digest}
        cases.append((FUNCTION_TEST_PREFIX + json.dumps(payload), 'Пароль найден.\n'))
    ns['add'](40, 1, 'Угадай учебный пароль', statement, '', '', PASSWORD_REFERENCE, cases)
    ex = ns['EXERCISES'][ns['key'](40,1)]
    ex['task'].update(starter_code=PASSWORD_STARTER, time_limit_ms=30000)
    ex['content']['blocks'] = [text(statement), text('### Готовая функция проверки'), code(PASSWORD_CHECKER),
        text('### Пример работы 1'),
        text('Для примера представь отдельную проверку, в которой загадан пароль `b2`. Твоя функция должна работать и с ним:'),
        code('result = find_password()\nprint(result)'), text('На экране появится:'), console('b2\n'),
        text('Настоящий пароль в заготовке другой. Проверка сама вызовет `find_password()` и убедится, что возвращённая строка подходит. При успехе в результате проверки появится «Пароль найден.». Результат примера `b2` не подставляй в решение.'),
        {'type':'callout','data':{'variant':'tip','title':'С чего начать',
         'content':'Сохрани алфавит в строке `abcdefghijklmnopqrstuvwxyz0123456789`. Один цикл перебирает односимвольные варианты. Два вложенных цикла позволяют составить двухсимвольные варианты через `a + b`. Продолжи для трёх и четырёх символов.'}}]
    ns['LESSON_TITLES'].append('Специальное использование функций: угадай пароль')
    ns['REMINDERS'][40] = ('Готовая функция как инструмент',
        'Научимся вызывать готовую функцию проверки и использовать её логический результат в алгоритме поиска.',
        'Полный перебор (brute force) — это проверка всех допустимых вариантов. В этом уроке всё происходит локально: алгоритм передаёт строку учебной функции и получает `True` или `False`. Знать внутреннее устройство функции для её использования не обязательно.\n\n'
        'SHA-256 превращает строку в хэш. Хэш нельзя просто «расшифровать», но можно вычислять хэши вариантов и сравнивать их с заданным. Короткий пароль с известным алфавитом можно подобрать таким перебором. Для алфавита из 36 символов и длины от 1 до 4 существует 36 + 36² + 36³ + 36⁴ = 1 727 604 варианта.',
        'def check_code(candidate):\n    return candidate == "b2"\n\nfor letter in "ab":\n    for digit in "12":\n        candidate = letter + digit\n        if check_code(candidate):\n            print("Код найден:", candidate)  # Код найден: b2',
        'Внешний цикл выбирает букву, внутренний — цифру. Получаются `a1`, `a2`, `b1`, `b2`. Для последнего варианта функция возвращает `True`. В следующем шаге вместо `check_code()` будет готовая `check_password()`, а вариантов станет больше. Внутри функции поиска `return` сразу завершит поиск, включая все вложенные циклы.',
        'Если перебирать только четырёхсимвольные строки, пароль длиной 1, 2 или 3 останется непроверенным. Проверять нужно все допустимые длины.',
        'Какие варианты проверит пример, если заменить строку "12" на "123"? Почему достаточно изменить аргумент готовой функции, чтобы проверить новый вариант?')
