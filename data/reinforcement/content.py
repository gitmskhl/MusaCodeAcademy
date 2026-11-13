"""Авторские задания. Решения используются только для проверки и не попадают в БД."""
from textwrap import dedent

from .wording import FUNCTION_NOTE, WORDING

LESSONS = []


def lesson(title, reminder):
    item = dict(title=title, reminder=reminder, tasks=[])
    LESSONS.append(item)
    return item


def task(group, title, text, fields, body, cases, *, signature=None, helper=''):
    """cases: (значения полей, вручную рассчитанный вывод после ввода)."""
    prefix = []
    for name, prompt, kind in fields:
        prefix.append(f'print({prompt!r})')
        if kind == 'list':
            prefix.extend([f'{name} = []', '_n = int(input())', 'for _i in range(_n):',
                           '    print("Введите число")', f'    {name}.append(int(input()))'])
        else:
            read = 'int(input())' if kind == 'int' else 'input()'
            if kind == 'words':
                read += '.split()'
            prefix.append(f'{name} = {read}')
    prefix = '\n'.join(prefix) + ('\n' if prefix else '')
    body = dedent(body).strip() + '\n'
    if signature:
        implementation, calls = body.split('\n# вызов\n')
        reference = helper + implementation + '\n\n' + prefix + calls
        starter = helper + signature + '\n    pass\n\n' + prefix + calls
        text += '\n\n' + FUNCTION_NOTE
    else:
        reference = prefix + body
        starter = '# Напиши программу здесь\n'
    tests = []
    for values, expected in cases:
        assert len(values) == len(fields)
        inputs, prompts = [], []
        for (_, prompt, kind), value in zip(fields, values):
            prompts.append(prompt)
            if kind == 'list':
                inputs.append(str(len(value)))
                for number in value:
                    inputs.append(str(number))
                    prompts.append('Введите число')
            else:
                inputs.append(str(value))
        tests.append(dict(input='\n'.join(inputs) + ('\n' if inputs else ''),
                          expected_output='\n'.join(prompts) + ('\n' if prompts else '') + expected.rstrip('\n') + '\n'))
    group['tasks'].append(dict(title=title, text=text, input_description='',
                               starter_code=starter, reference=reference, tests=tests))


def raw(group, title, text, reference, cases):
    group['tasks'].append(dict(title=title, text=text, input_description='',
                               starter_code='# Напиши программу здесь\n', reference=dedent(reference).strip()+'\n',
                               tests=[dict(input=i, expected_output=o) for i, o in cases]))


I = lambda name, prompt: (name, prompt, 'int')
S = lambda name, prompt: (name, prompt, 'str')
W = lambda name, prompt: (name, prompt, 'words')
L = ('numbers', 'Сколько чисел?', 'list')

intro = lesson('Ввод, вывод и вычисления',
    'Вспомни: **input()** возвращает строку, а **int(input())** позволяет получить целое число. **print(a, b)** разделяет значения пробелом. Сначала получи данные, затем вычисли ответ. В этом уроке достаточно переменных, ввода, вывода и арифметики.')
task(intro, 'Карточка ученика', WORDING['Карточка ученика'],
 [S('name','Введите имя'),S('city','Введите город')], 'print("Ученик:", name)\nprint("Город:", city)',
 [(['Анна','Москва'],'Ученик: Анна\nГород: Москва'),(['Муса Али','Нижний Новгород'],'Ученик: Муса Али\nГород: Нижний Новгород'),(['Иван','Тула'],'Ученик: Иван\nГород: Тула')])
task(intro, 'До следующего уровня', WORDING['До следующего уровня'],
 [I('score','Введите очки')], 'print("Осталось:", 100 - score)', [([35],'Осталось: 65'),([0],'Осталось: 100'),([100],'Осталось: 0')])
task(intro, 'Двойная покупка', WORDING['Двойная покупка'],
 [I('price','Введите цену тетради')], 'print("К оплате:", price * 2)', [([45],'К оплате: 90'),([0],'К оплате: 0'),([10000],'К оплате: 20000')])
task(intro, 'Билеты для компании', WORDING['Билеты для компании'],
 [I('price','Введите цену билета'),I('people','Сколько человек?')], 'print("Стоимость:", price * people)', [([150,4],'Стоимость: 600'),([0,8],'Стоимость: 0'),([500,0],'Стоимость: 0')])
task(intro, 'Сдача на кассе', WORDING['Сдача на кассе'],
 [I('cost','Введите стоимость'),I('paid','Сколько заплатили?')], 'print("Сдача:", paid - cost)', [([340,500],'Сдача: 160'),([500,500],'Сдача: 0'),([0,100],'Сдача: 100')])
task(intro, 'Периметр площадки', WORDING['Периметр площадки'],
 [I('a','Введите длину'),I('b','Введите ширину')], 'print("Периметр:", (a + b) * 2)', [([3,7],'Периметр: 20'),([1,1],'Периметр: 4'),([1000,2],'Периметр: 2004')])
task(intro, 'Покупка с доставкой', WORDING['Покупка с доставкой'],
 [I('price','Введите цену'),I('count','Введите количество'),I('delivery','Введите стоимость доставки')], 'print("Итого:", price * count + delivery)', [([80,3,100],'Итого: 340'),([0,5,50],'Итого: 50'),([20,0,0],'Итого: 0')])
task(intro, 'Температура изменилась', WORDING['Температура изменилась'],
 [I('t','Введите температуру'),I('first','Введите первое изменение'),I('second','Введите второе изменение')], 'print("Температура:", t + first + second)', [([10,-4,2],'Температура: 8'),([-5,-3,-2],'Температура: -10'),([0,5,-5],'Температура: 0')])
task(intro, 'Два вида товаров', WORDING['Два вида товаров'],
 [I('a','Введите цену тетради'),I('n','Сколько тетрадей?'),I('b','Введите цену ручки'),I('m','Сколько ручек?')], 'notebooks = a * n\npens = b * m\nprint("Тетради:", notebooks)\nprint("Ручки:", pens)\nprint("Итого:", notebooks + pens)', [([40,3,15,2],'Тетради: 120\nРучки: 30\nИтого: 150'),([0,0,10,1],'Тетради: 0\nРучки: 10\nИтого: 10'),([5,4,3,0],'Тетради: 20\nРучки: 0\nИтого: 20')])
task(intro, 'Обмен значениями', WORDING['Обмен значениями'],
 [I('a','Введите a'),I('b','Введите b')], 'temporary = a\na = b\nb = temporary\nprint("a:", a)\nprint("b:", b)', [([3,8],'a: 8\nb: 3'),([-2,0],'a: 0\nb: -2'),([5,5],'a: 5\nb: 5')])

conditions = lesson('Условия и сравнения', 'Вспомни **if / else**, сравнения и **and**. Проверяй, входят ли границы в условие. Для нескольких вариантов можно использовать вложенные условия. Начни с коротких проверок, затем переходи к задачам с несколькими правилами.')
task(conditions,'Заморозки',WORDING['Заморозки'], [I('t','Введите температуру')], 'if t < 0:\n    print("Заморозки")\nelse:\n    print("Без заморозков")', [([-1],'Заморозки'),([0],'Без заморозков'),([25],'Без заморозков')])
task(conditions,'Хватит ли денег',WORDING['Хватит ли денег'],[I('balance','Введите баланс'),I('price','Введите стоимость')], 'if balance >= price:\n    print("Покупка доступна")\nelse:\n    print("Недостаточно денег")', [([100,80],'Покупка доступна'),([80,80],'Покупка доступна'),([0,1],'Недостаточно денег')])
task(conditions,'Кодовое слово',WORDING['Кодовое слово'],[S('word','Введите кодовое слово')], 'if word == "ракета":\n    print("Проходи")\nelse:\n    print("Код не подходит")', [(['ракета'],'Проходи'),(['Ракета'],'Код не подходит'),(['ракета '],'Код не подходит')])
task(conditions,'Время библиотеки',WORDING['Время библиотеки'],[I('hour','Введите час')], 'if hour >= 10 and hour < 18:\n    print("Открыто")\nelse:\n    print("Закрыто")', [([10],'Открыто'),([17],'Открыто'),([18],'Закрыто'),([9],'Закрыто')])
task(conditions,'Команда на олимпиаду',WORDING['Команда на олимпиаду'],[I('a','Введите баллы первого'),I('b','Введите баллы второго')], 'if a >= 70 and b >= 70:\n    print("Команда прошла")\nelse:\n    print("Команда не прошла")', [([70,70],'Команда прошла'),([69,100],'Команда не прошла'),([100,69],'Команда не прошла')])
task(conditions,'Сравнение результатов',WORDING['Сравнение результатов'],[I('a','Введите первый результат'),I('b','Введите второй результат')], 'if a > b:\n    print("Первый")\nelse:\n    if b > a:\n        print("Второй")\n    else:\n        print("Ничья")', [([8,3],'Первый'),([-5,-2],'Второй'),([0,0],'Ничья')])
task(conditions,'Уровень подготовки',WORDING['Уровень подготовки'],[I('score','Введите балл')], 'if score < 40:\n    print("Начальный")\nelse:\n    if score < 80:\n        print("Средний")\n    else:\n        print("Высокий")', [([39],'Начальный'),([40],'Средний'),([79],'Средний'),([80],'Высокий'),([100],'Высокий')])
task(conditions,'Доставка по правилам',WORDING['Доставка по правилам'],[I('cost','Введите сумму заказа'),S('city','Введите город')], 'delivery = 0\nif cost < 1500:\n    if city == "Тула":\n        delivery = 100\n    else:\n        delivery = 300\nprint("Доставка:", delivery)\nprint("К оплате:", cost + delivery)', [([1500,'Омск'],'Доставка: 0\nК оплате: 1500'),([1499,'Тула'],'Доставка: 100\nК оплате: 1599'),([0,'Омск'],'Доставка: 300\nК оплате: 300')])
task(conditions,'Можно ли собрать треугольник',WORDING['Можно ли собрать треугольник'],[I('a','Введите первую сторону'),I('b','Введите вторую сторону'),I('c','Введите третью сторону')], 'if a < b + c and b < a + c and c < a + b:\n    print("Можно")\nelse:\n    print("Нельзя")', [([3,4,5],'Можно'),([1,2,3],'Нельзя'),([8,2,2],'Нельзя'),([2,8,2],'Нельзя'),([2,2,8],'Нельзя')])
task(conditions,'Две независимые скидки',WORDING['Две независимые скидки'],[I('price','Введите цену'),S('card','Есть карта?'),S('day','Введите день недели')], 'if card == "да":\n    price = price - 100\nif day == "среда":\n    price = price - 200\nprint("К оплате:", price)', [([1000,'да','среда'],'К оплате: 700'),([500,'нет','среда'],'К оплате: 300'),([500,'да','понедельник'],'К оплате: 400'),([500,'нет','пятница'],'К оплате: 500')])

loops = lesson('Цикл for и накопление результата', 'Когда количество повторений известно, используй **for** и **range**. Сумму и счётчики создай до цикла. Для поиска максимума начни с первого введенного значения. В этом уроке решай задачи без списков, **sum()**, **min()** и **max()**.')
task(loops,'Повторяем сообщение',WORDING['Повторяем сообщение'],[I('n','Сколько повторений?')], 'for i in range(n):\n    print("Я тренируюсь")', [([2],'Я тренируюсь\nЯ тренируюсь'),([0],''),([1],'Я тренируюсь')])
task(loops,'Номера шкафчиков',WORDING['Номера шкафчиков'],[I('n','Сколько шкафчиков?')], 'number = 1\nfor i in range(n):\n    print(number)\n    number = number + 1', [([3],'1\n2\n3'),([0],''),([1],'1')])
task(loops,'Ступеньки по два',WORDING['Ступеньки по два'],[I('n','Сколько ступенек?')], 'number = 2\nfor i in range(n):\n    print(number)\n    number = number + 2', [([4],'2\n4\n6\n8'),([0],''),([1],'2')])
task(loops,'Сумма номеров',WORDING['Сумма номеров'],[I('n','Введите n')], 'total = 0\nnumber = 1\nfor i in range(n):\n    total = total + number\n    number = number + 1\nprint("Сумма:", total)', [([4],'Сумма: 10'),([0],'Сумма: 0'),([1],'Сумма: 1'),([100],'Сумма: 5050')])
raw(loops,'Сумма взносов',WORDING['Сумма взносов'], '''
print("Сколько взносов?")
n = int(input())
total = 0
for i in range(n):
    print("Введите взнос")
    total = total + int(input())
print("Всего:", total)
''', [('3\n10\n0\n20\n','Сколько взносов?\nВведите взнос\nВведите взнос\nВведите взнос\nВсего: 30\n'),('0\n','Сколько взносов?\nВсего: 0\n'),('1\n7\n','Сколько взносов?\nВведите взнос\nВсего: 7\n')])
raw(loops,'Дни выше нормы',WORDING['Дни выше нормы'], '''
print("Сколько дней?")
n = int(input())
count = 0
for i in range(n):
    print("Введите температуру")
    t = int(input())
    if t > 25:
        count = count + 1
print("Жарких дней:", count)
''', [('4\n25\n26\n30\n-2\n','Сколько дней?\nВведите температуру\nВведите температуру\nВведите температуру\nВведите температуру\nЖарких дней: 2\n'),('0\n','Сколько дней?\nЖарких дней: 0\n'),('1\n25\n','Сколько дней?\nВведите температуру\nЖарких дней: 0\n')])
task(loops,'Рост накоплений',WORDING['Рост накоплений'],[I('amount','Введите начальную сумму'),I('n','Сколько удвоений?')], 'for i in range(n):\n    amount = amount * 2\nprint("Накоплено:", amount)', [([3,4],'Накоплено: 48'),([5,0],'Накоплено: 5'),([0,10],'Накоплено: 0')])
raw(loops,'Лучший результат',WORDING['Лучший результат'], '''
print("Сколько результатов?")
n = int(input())
print("Введите результат")
best = int(input())
for i in range(n - 1):
    print("Введите результат")
    value = int(input())
    if value > best:
        best = value
print("Лучший:", best)
''', [('3\n-8\n-2\n-5\n','Сколько результатов?\nВведите результат\nВведите результат\nВведите результат\nЛучший: -2\n'),('1\n-7\n','Сколько результатов?\nВведите результат\nЛучший: -7\n'),('2\n4\n4\n','Сколько результатов?\nВведите результат\nВведите результат\nЛучший: 4\n')])
raw(loops,'Рекорды по ходу игры',WORDING['Рекорды по ходу игры'], '''
print("Сколько результатов?")
n = int(input())
print("Введите результат")
best = int(input())
count = 1
for i in range(n - 1):
    print("Введите результат")
    value = int(input())
    if value > best:
        best = value
        count = count + 1
print("Рекордов:", count)
''', [('5\n3\n3\n5\n4\n8\n','Сколько результатов?\n'+'Введите результат\n'*5+'Рекордов: 3\n'),('1\n-5\n','Сколько результатов?\nВведите результат\nРекордов: 1\n'),('3\n5\n4\n3\n','Сколько результатов?\n'+'Введите результат\n'*3+'Рекордов: 1\n')])
raw(loops,'Самая длинная серия успехов',WORDING['Самая длинная серия успехов'], '''
print("Сколько попыток?")
n = int(input())
current = 0
best = 0
for i in range(n):
    print("Введите результат")
    value = int(input())
    if value == 1:
        current = current + 1
        if current > best:
            best = current
    else:
        current = 0
print("Лучшая серия:", best)
''', [('7\n1\n1\n0\n1\n1\n1\n0\n','Сколько попыток?\n'+'Введите результат\n'*7+'Лучшая серия: 3\n'),('0\n','Сколько попыток?\nЛучшая серия: 0\n'),('3\n0\n0\n0\n','Сколько попыток?\n'+'Введите результат\n'*3+'Лучшая серия: 0\n'),('2\n1\n1\n','Сколько попыток?\n'+'Введите результат\n'*2+'Лучшая серия: 2\n')])

whiles = lesson('Цикл while и команды пользователя', 'Используй **while**, если количество повторений заранее неизвестно. Не забудь менять переменные, от которых зависит условие. **break** завершает цикл. Команда остановки не должна попадать в подсчёты. В задачах с командами регистр и пробелы имеют значение; команда завершения обязательно встретится.')
task(whiles,'Обратный отсчёт',WORDING['Обратный отсчёт'],[I('n','Введите начало отсчёта')], 'while n > 0:\n    print(n)\n    n = n - 1\nprint("Старт!")', [([3],'3\n2\n1\nСтарт!'),([0],'Старт!'),([1],'1\nСтарт!')])
task(whiles,'Растём до цели',WORDING['Растём до цели'],[I('value','Введите начало'),I('target','Введите цель')], 'steps = 0\nwhile value < target:\n    value = value + 3\n    steps = steps + 1\nprint("Итог:", value)\nprint("Шагов:", steps)', [([2,10],'Итог: 11\nШагов: 3'),([10,10],'Итог: 10\nШагов: 0'),([10,2],'Итог: 10\nШагов: 0')])
raw(whiles,'Считаем сообщения',WORDING['Считаем сообщения'], '''
count = 0
while True:
    print("Введите сообщение или стоп")
    message = input()
    if message == "стоп":
        break
    count = count + 1
print("Сообщений:", count)
''', [('привет\nкак дела\nстоп\n','Введите сообщение или стоп\n'*3+'Сообщений: 2\n'),('стоп\n','Введите сообщение или стоп\nСообщений: 0\n'),('\nСтоп\nстоп\n','Введите сообщение или стоп\n'*3+'Сообщений: 2\n')])
raw(whiles,'Сумма до отрицательного',WORDING['Сумма до отрицательного'], '''
total = 0
while True:
    print("Введите число")
    value = int(input())
    if value < 0:
        break
    total = total + value
print("Сумма:", total)
''', [('5\n0\n7\n-1\n','Введите число\n'*4+'Сумма: 12\n'),('-5\n','Введите число\nСумма: 0\n'),('0\n-1\n','Введите число\n'*2+'Сумма: 0\n')])
raw(whiles,'Копилка до 300',WORDING['Копилка до 300'], '''
total = 0
count = 0
while total < 300:
    print("Введите взнос")
    total = total + int(input())
    count = count + 1
print("Накоплено:", total)
print("Взносов:", count)
''', [('100\n200\n','Введите взнос\n'*2+'Накоплено: 300\nВзносов: 2\n'),('400\n','Введите взнос\nНакоплено: 400\nВзносов: 1\n'),('299\n1\n','Введите взнос\n'*2+'Накоплено: 300\nВзносов: 2\n')])
task(whiles,'Сколько удвоений',WORDING['Сколько удвоений'],[I('value','Введите число'),I('target','Введите цель')], 'count = 0\nwhile value < target:\n    value = value * 2\n    count = count + 1\nprint("Удвоений:", count)\nprint("Получилось:", value)', [([3,20],'Удвоений: 3\nПолучилось: 24'),([10,10],'Удвоений: 0\nПолучилось: 10'),([5,2],'Удвоений: 0\nПолучилось: 5')])
raw(whiles,'Четыре попытки',WORDING['Четыре попытки'], '''
attempt = 0
success = 0
while attempt < 4:
    print("Введите код")
    code = input()
    attempt = attempt + 1
    if code == "731":
        print("Верно")
        success = 1
        break
    print("Ошибка")
if success == 0:
    print("Вход закрыт")
''', [('731\n','Введите код\nВерно\n'),('1\n2\n3\n4\n',('Введите код\nОшибка\n')*4+'Вход закрыт\n'),('1\n2\n3\n731\n',('Введите код\nОшибка\n')*3+'Введите код\nВерно\n')])
raw(whiles,'Склад коробок',WORDING['Склад коробок'], '''
stock = 10
while True:
    print("Сколько забрать?")
    amount = int(input())
    if amount == 0:
        break
    if amount <= stock:
        stock = stock - amount
        print("Выдано")
    else:
        print("Не хватает")
print("Осталось:", stock)
''', [('6\n5\n4\n0\n','Сколько забрать?\nВыдано\nСколько забрать?\nНе хватает\nСколько забрать?\nВыдано\nСколько забрать?\nОсталось: 0\n'),('0\n','Сколько забрать?\nОсталось: 10\n'),('11\n0\n','Сколько забрать?\nНе хватает\nСколько забрать?\nОсталось: 10\n')])
raw(whiles,'Счётчик с отменой',WORDING['Счётчик с отменой'], '''
value = 0
while True:
    print("Введите команду")
    command = input()
    if command == "стоп":
        break
    if command == "плюс":
        value = value + 1
    if command == "минус" and value > 0:
        value = value - 1
    if command == "счёт":
        print(value)
print("Итог:", value)
''', [('минус\nсчёт\nплюс\nплюс\nминус\nстоп\n','Введите команду\nВведите команду\n0\n'+'Введите команду\n'*4+'Итог: 1\n'),('стоп\n','Введите команду\nИтог: 0\n'),('плюс\nсчёт\nстоп\n','Введите команду\nВведите команду\n1\nВведите команду\nИтог: 1\n')])
raw(whiles,'Кошелёк с отчётом',WORDING['Кошелёк с отчётом'], '''
balance = 500
count = 0
while True:
    print("Введите команду")
    command = input()
    if command == "стоп":
        break
    if command == "пополнить":
        print("Введите сумму")
        balance = balance + int(input())
    if command == "купить":
        print("Введите стоимость")
        price = int(input())
        if balance >= price:
            balance = balance - price
            count = count + 1
            print("Куплено")
        else:
            print("Недостаточно денег")
print("Баланс:", balance)
print("Покупок:", count)
''', [('купить\n600\nпополнить\n100\nкупить\n600\nстоп\n','Введите команду\nВведите стоимость\nНедостаточно денег\nВведите команду\nВведите сумму\nВведите команду\nВведите стоимость\nКуплено\nВведите команду\nБаланс: 0\nПокупок: 1\n'),('стоп\n','Введите команду\nБаланс: 500\nПокупок: 0\n'),('купить\n500\nстоп\n','Введите команду\nВведите стоимость\nКуплено\nВведите команду\nБаланс: 0\nПокупок: 1\n')])

lists = lesson('Списки, срезы и перебор', 'Список хранит несколько значений. Вспомни индексы, **len**, срезы, **append**, **remove** и **in**. Не удаляй элементы из списка, пока перебираешь его для поиска. В заданиях сохраняй порядок и повторы, если условие не говорит иначе. В этом уроке все вводимые числа целые от -10000 до 10000.')
task(lists,'Размер списка',WORDING['Размер списка'],[L], 'print("Элементов:", len(numbers))', [([[4,4,1]],'Элементов: 3'),([[]],'Элементов: 0'),([[0]],'Элементов: 1')])
task(lists,'Начало или пустота',WORDING['Начало или пустота'],[L], 'if len(numbers) == 0:\n    print("Пусто")\nelse:\n    print("Первый:", numbers[0])', [([[8,3]],'Первый: 8'),([[]],'Пусто'),([[-5]],'Первый: -5')])
task(lists,'Первые три',WORDING['Первые три'],[L], 'print(numbers[:3])', [([[1,2,3,4]],'[1, 2, 3]'),([[]],'[]'),([[9,9]],'[9, 9]')])
task(lists,'Без двух последних',WORDING['Без двух последних'],[L], 'print(numbers[:-2])', [([[1,2,3,4]],'[1, 2]'),([[1,2]],'[]'),([[1]],'[]'),([[]],'[]')])
task(lists,'Заменяем первое значение',WORDING['Заменяем первое значение'],[L], 'if len(numbers) > 0:\n    numbers[0] = 0\nprint(numbers)', [([[4,5,4]],'[0, 5, 4]'),([[]],'[]'),([[-1]],'[0]')])
task(lists,'Есть ли нужное число',WORDING['Есть ли нужное число'],[L,I('target','Какое число ищем?')], 'if target in numbers:\n    print("Есть")\nelse:\n    print("Нет")', [([[1,4,4],4],'Есть'),([[],0],'Нет'),([[-2,0],3],'Нет')])
task(lists,'Не ниже порога',WORDING['Не ниже порога'],[L,I('threshold','Введите порог')], 'result = []\nfor number in numbers:\n    if number >= threshold:\n        result.append(number)\nprint(result)', [([[5,1,5,3],3],'[5, 5, 3]'),([[],0],'[]'),([[-5,-2],0],'[]'),([[-3,-2],-3],'[-3, -2]')])
task(lists,'Удаляем одно совпадение',WORDING['Удаляем одно совпадение'],[L,I('target','Что удалить?')], 'if target in numbers:\n    numbers.remove(target)\nprint(numbers)', [([[2,3,2],2],'[3, 2]'),([[1],9],'[1]'),([[],4],'[]'),([[7],7],'[]')])
task(lists,'Второе различное место',WORDING['Второе различное место'],[L], 'best = numbers[0]\nfor number in numbers:\n    if number > best:\n        best = number\nsmaller = []\nfor number in numbers:\n    if number < best:\n        smaller.append(number)\nif len(smaller) == 0:\n    print("Нет второго места")\nelse:\n    second = smaller[0]\n    for number in smaller:\n        if number > second:\n            second = number\n    print("Второе место:", second)', [([[9,9,4]],'Второе место: 4'),([[5,5]],'Нет второго места'),([[-2,-8,-4,-2]],'Второе место: -4'),([[1,2]],'Второе место: 1')])
task(lists,'Сдвигаем очередь чисел',WORDING['Сдвигаем очередь чисел'],[L,I('k','Сколько переносов?')], 'result = numbers[:]\nfor i in range(k):\n    first = result[0]\n    result = result[1:]\n    result.append(first)\nprint("Исходный:", numbers)\nprint("После переносов:", result)', [([[1,2,3],1],'Исходный: [1, 2, 3]\nПосле переносов: [2, 3, 1]'),([[7],5],'Исходный: [7]\nПосле переносов: [7]'),([[1,2],0],'Исходный: [1, 2]\nПосле переносов: [1, 2]'),([[1,2],3],'Исходный: [1, 2]\nПосле переносов: [2, 1]')])

strings = lesson('Строки, слова и поиск фрагментов', 'Строку можно перебирать, получать ее длину и делать срезы. **split()** без аргументов разбивает текст на слова и пропускает лишние пробелы. **in** ищет точный фрагмент. Во всем уроке регистр учитывается, знаки препинания остаются при словах. Текст — одна строка длиной до 1000 символов; пустая строка допустима.')
task(strings,'Длина сообщения',WORDING['Длина сообщения'],[S('text','Введите текст')], 'print("Символов:", len(text))', [(['кот'],'Символов: 3'),([''],'Символов: 0'),(['а б!'],'Символов: 4')])
task(strings,'Безопасный первый символ',WORDING['Безопасный первый символ'],[S('text','Введите текст')], 'if len(text) == 0:\n    print("Пусто")\nelse:\n    print("Первый:", text[0])', [(['кот'],'Первый: к'),([''],'Пусто'),(['Я'],'Первый: Я')])
task(strings,'Короткое начало',WORDING['Короткое начало'],[S('text','Введите текст')], 'print(text[:4])', [(['программа'],'прог'),(['кот'],'кот'),([''],''),(['а б в'],'а б ')])
task(strings,'Сколько букв а',WORDING['Сколько букв а'],[S('text','Введите текст')], 'count = 0\nfor letter in text:\n    if letter == "а":\n        count = count + 1\nprint("Букв а:", count)', [(['мама'],'Букв а: 2'),(['Аа'],'Букв а: 1'),([''],'Букв а: 0')])
task(strings,'Подходит ли фрагмент',WORDING['Подходит ли фрагмент'],[S('text','Введите текст'),S('fragment','Введите фрагмент')], 'if fragment in text:\n    print("Найдено")\nelse:\n    print("Не найдено")', [(['котик','кот'],'Найдено'),(['Кот','кот'],'Не найдено'),(['','а'],'Не найдено')])
task(strings,'Слова по одному',WORDING['Слова по одному'],[W('words','Введите текст')], 'for word in words:\n    print(word)', [(['кот  дом'],'кот\nдом'),(['   '],''),(['привет, мир!'],'привет,\nмир!')])
task(strings,'Слова заданной длины',WORDING['Слова заданной длины'],[W('words','Введите текст'),I('size','Введите длину')], 'result = []\nfor word in words:\n    if len(word) == size:\n        result.append(word)\nprint(result)', [(['кот дом кот леса',3],"['кот', 'дом', 'кот']"),(['',2],'[]'),(['да, да',3],"['да,']")])
task(strings,'Без запрещенного слова',WORDING['Без запрещенного слова'],[W('words','Введите текст'),S('banned','Введите запрещенное слово')], 'result = []\nfor word in words:\n    if word != banned:\n        result.append(word)\nprint(result)', [(['кот котик кот, кот','кот'],"['котик', 'кот,']"),(['','кот'],'[]'),(['дом дом','дом'],'[]'),(['Кот кот','кот'],"['Кот']")])
task(strings,'Самое короткое слово',WORDING['Самое короткое слово'],[W('words','Введите текст')], 'if len(words) == 0:\n    print("Нет слов")\nelse:\n    shortest = words[0]\n    for word in words:\n        if len(word) < len(shortest):\n            shortest = word\n    print("Короткое слово:", shortest)', [(['собака кот дом'],'Короткое слово: кот'),(['  '],'Нет слов'),(['я дома'],'Короткое слово: я'),(['да! ну'],'Короткое слово: ну')])
task(strings,'Слова, встречавшиеся повторно',WORDING['Слова, встречавшиеся повторно'],[W('words','Введите текст')], 'seen = []\nrepeated = []\nfor word in words:\n    if word in seen:\n        if word not in repeated:\n            repeated.append(word)\n    else:\n        seen.append(word)\nprint(repeated)', [(['а б б а'],"['б', 'а']"),(['кот кот кот'],"['кот']"),(['кот Кот кот,'],'[]'),([''],'[]')])

functions = lesson('Функции и возвращаемые значения', 'Функция получает параметры, а **return** возвращает результат и завершает вызов. **print** и **return** делают разные вещи. В заготовках уже есть ввод и вызовы: заполняй тела функций. Сначала идут вычисления, затем работа со списками и сочетание нескольких функций. Все числовые значения целые от -10000 до 10000, если условие не задает другой диапазон.')
task(functions,'Увеличиваем число',WORDING['Увеличиваем число'],[I('number','Введите число')], 'def add_one(number):\n    return number + 1\n# вызов\nprint("Ответ:", add_one(number))', [([5],'Ответ: 6'),([-1],'Ответ: 0'),([0],'Ответ: 1')], signature='def add_one(number):')
task(functions,'Стоимость набора',WORDING['Стоимость набора'],[I('price','Введите цену'),I('count','Введите количество')], 'def set_cost(price, count):\n    return price * count\n# вызов\nprint("Стоимость:", set_cost(price, count))', [([30,4],'Стоимость: 120'),([0,4],'Стоимость: 0'),([9,0],'Стоимость: 0')], signature='def set_cost(price, count):')
task(functions,'Расстояние между числами',WORDING['Расстояние между числами'],[I('a','Введите первое число'),I('b','Введите второе число')], 'def distance(a, b):\n    if a > b:\n        return a - b\n    return b - a\n# вызов\nprint("Расстояние:", distance(a, b))', [([3,8],'Расстояние: 5'),([-5,-2],'Расстояние: 3'),([7,7],'Расстояние: 0'),([5,-2],'Расстояние: 7')], signature='def distance(a, b):')
task(functions,'Категория числа',WORDING['Категория числа'],[I('number','Введите число')], 'def sign_name(number):\n    if number > 0:\n        return "Плюс"\n    if number < 0:\n        return "Минус"\n    return "Ноль"\n# вызов\nprint(sign_name(number))', [([3],'Плюс'),([-3],'Минус'),([0],'Ноль')], signature='def sign_name(number):')
task(functions,'Сколько значений выше порога',WORDING['Сколько значений выше порога'],[L,I('threshold','Введите порог')], 'def count_above(numbers, threshold):\n    count = 0\n    for number in numbers:\n        if number > threshold:\n            count = count + 1\n    return count\n# вызов\nprint("Выше порога:", count_above(numbers, threshold))', [([[5,5,3,8],5],'Выше порога: 1'),([[],0],'Выше порога: 0'),([[-1,-1],-2],'Выше порога: 2')], signature='def count_above(numbers, threshold):')
task(functions,'Отрицательные в новом списке',WORDING['Отрицательные в новом списке'],[L], 'def negative_only(numbers):\n    result = []\n    for number in numbers:\n        if number < 0:\n            result.append(number)\n    return result\n# вызов\nresult = negative_only(numbers)\nprint("Исходный:", numbers)\nprint("Отрицательные:", result)', [([[2,-1,0,-1]],'Исходный: [2, -1, 0, -1]\nОтрицательные: [-1, -1]'),([[]],'Исходный: []\nОтрицательные: []'),([[1,0]],'Исходный: [1, 0]\nОтрицательные: []')], signature='def negative_only(numbers):')
task(functions,'Сумма длин слов',WORDING['Сумма длин слов'],[S('message','Введите текст')], 'def letters_total(message):\n    total = 0\n    for word in message.split():\n        total = total + len(word)\n    return total\n# вызов\nprint("Символов в словах:", letters_total(message))', [(['кот  дом'],'Символов в словах: 6'),(['   '],'Символов в словах: 0'),(['да, нет!'],'Символов в словах: 7')], signature='def letters_total(message):')
task(functions,'Все в диапазоне',WORDING['Все в диапазоне'],[L,I('low','Введите нижнюю границу'),I('high','Введите верхнюю границу')], 'def all_inside(numbers, low, high):\n    for number in numbers:\n        if number < low:\n            return "Не подходят"\n        if number > high:\n            return "Не подходят"\n    return "Подходят"\n# вызов\nprint(all_inside(numbers, low, high))', [([[2,4,3],2,4],'Подходят'),([[2,5],2,4],'Не подходят'),([[],0,0],'Подходят'),([[1,3],2,4],'Не подходят')], signature='def all_inside(numbers, low, high):')
task(functions,'Размах через две функции',WORDING['Размах через две функции'],[L], 'def max_value(numbers):\n    best = numbers[0]\n    for number in numbers:\n        if number > best:\n            best = number\n    return best\n\ndef spread(numbers):\n    return max_value(numbers) - min_value(numbers)\n# вызов\nprint("Размах:", spread(numbers))', [([[3,9,4]],'Размах: 6'),([[-8,-2,-5]],'Размах: 6'),([[7]],'Размах: 0'),([[4,4]],'Размах: 0')], signature='def max_value(numbers):\n    pass\n\ndef spread(numbers):', helper='def min_value(numbers):\n    best = numbers[0]\n    for number in numbers:\n        if number < best:\n            best = number\n    return best\n\n')
task(functions,'Отбираем короткие слова',WORDING['Отбираем короткие слова'],[S('message','Введите текст'),I('limit','Введите предел длины')], 'def is_short(word, limit):\n    if len(word) <= limit:\n        return 1\n    return 0\n\ndef short_words(message, limit):\n    result = []\n    for word in message.split():\n        if is_short(word, limit) == 1:\n            result.append(word)\n    return result\n# вызов\nprint(short_words(message, limit))', [(['я люблю код код',3],"['я', 'код', 'код']"),(['кот дом',0],'[]'),(['',5],'[]'),(['да, нет',3],"['да,', 'нет']")], signature='def is_short(word, limit):\n    pass\n\ndef short_words(message, limit):')

mixed = lesson('Итоговая практика: задачи вперемешку', 'Теперь темы перемешаны. Сначала сам выбери нужные инструменты: условия, циклы, списки, строки или функции. Здесь меньше подсказок. Внимательно прочитай формат ввода и вывода, проверь границы и пустые данные. Задачи постепенно усложняются. Все строки занимают одну строку ввода, все числа целые от -10000 до 10000, если не указан другой диапазон.')
task(mixed,'Бейдж участника',WORDING['Бейдж участника'],[S('name','Введите имя'),I('number','Введите номер')], 'print("Участник", number, "-", name)', [(['Анна',3],'Участник 3 - Анна'),(['Муса Али',1],'Участник 1 - Муса Али'),(['Иван',100],'Участник 100 - Иван')])
task(mixed,'Проверка заголовка',WORDING['Проверка заголовка'],[S('title','Введите заголовок')], 'if len(title) >= 1 and len(title) <= 20:\n    print("Подходит")\nelse:\n    print("Не подходит")', [(['Мой день'],'Подходит'),([''],'Не подходит'),(['а'*20],'Подходит'),(['а'*21],'Не подходит')])
task(mixed,'Открытки для друзей',WORDING['Открытки для друзей'],[S('message','Введите текст открытки'),I('n','Сколько копий?')], 'for i in range(n):\n    print(message)', [(['Удачи!',2],'Удачи!\nУдачи!'),(['Привет',0],''),(['С днем рождения!',1],'С днем рождения!')])
task(mixed,'Последние записи',WORDING['Последние записи'],[L,I('k','Сколько последних записей?')], 'print(numbers[-k:])', [([[1,2,3,4],2],'[3, 4]'),([[5],3],'[5]'),([[],1],'[]')])
task(mixed,'Есть ли обращение',WORDING['Есть ли обращение'],[W('words','Введите текст'),S('name','Введите имя')], 'if name in words:\n    print("Есть обращение")\nelse:\n    print("Нет обращения")', [(['привет Анна','Анна'],'Есть обращение'),(['привет Анна,','Анна'],'Нет обращения'),(['Аннабель','Анна'],'Нет обращения'),(['','Анна'],'Нет обращения')])
task(mixed,'Расходы без возвратов',WORDING['Расходы без возвратов'],[L], 'count = 0\ntotal = 0\nfor number in numbers:\n    if number > 0:\n        count = count + 1\n        total = total + number\nprint("Расходов:", count)\nprint("Потрачено:", total)', [([[20,-5,0,10]],'Расходов: 2\nПотрачено: 30'),([[]],'Расходов: 0\nПотрачено: 0'),([[-3,0]],'Расходов: 0\nПотрачено: 0')])
task(mixed,'Короткие заявки без повторов',WORDING['Короткие заявки без повторов'],[W('words','Введите текст')], 'result = []\nfor word in words:\n    if len(word) <= 4 and word not in result:\n        result.append(word)\nprint(result)', [(['кот дом собака кот лес'],"['кот', 'дом', 'лес']"),([''],'[]'),(['Кот кот кот,'],"['Кот', 'кот', 'кот,']")])
raw(mixed,'Заявки до закрытия',WORDING['Заявки до закрытия'], '''
accepted = 0
rejected = 0
while True:
    print("Введите заявку или стоп")
    message = input()
    if message == "стоп":
        break
    if len(message) <= 10:
        accepted = accepted + 1
    else:
        rejected = rejected + 1
print("Принято:", accepted)
print("Отклонено:", rejected)
''', [('кот\n12345678901\nстоп\n','Введите заявку или стоп\n'*3+'Принято: 1\nОтклонено: 1\n'),('стоп\n','Введите заявку или стоп\nПринято: 0\nОтклонено: 0\n'),('\n1234567890\nстоп\n','Введите заявку или стоп\n'*3+'Принято: 2\nОтклонено: 0\n')])
task(mixed,'Сколько изменений',WORDING['Сколько изменений'],[L], 'count = 0\nfor i in range(len(numbers) - 1):\n    if numbers[i] != numbers[i + 1]:\n        count = count + 1\nprint("Изменений:", count)', [([[2,2,5,3]],'Изменений: 2'),([[]],'Изменений: 0'),([[7]],'Изменений: 0'),([[1,1,1]],'Изменений: 0')])
task(mixed,'Сравниваем тексты функцией',WORDING['Сравниваем тексты функцией'],[S('first','Введите первый текст'),S('second','Введите второй текст')], 'def more_words(first, second):\n    a = len(first.split())\n    b = len(second.split())\n    if a > b:\n        return "Первый"\n    if b > a:\n        return "Второй"\n    return "Поровну"\n# вызов\nprint(more_words(first, second))', [(['кот дом','лес'],'Первый'),(['','  '],'Поровну'),(['я','мы идем'],'Второй'),(['кот','оченьдлинноеслово'],'Поровну')], signature='def more_words(first, second):')
raw(mixed,'Очередь с командами',WORDING['Очередь с командами'], '''
queue = []
while True:
    print("Введите команду")
    command = input()
    if command == "стоп":
        break
    if command == "добавить":
        print("Введите имя")
        queue.append(input())
    if command == "следующий":
        if len(queue) == 0:
            print("Очередь пуста")
        else:
            print("Приглашён:", queue[0])
            queue = queue[1:]
print("Остались:", queue)
''', [('следующий\nдобавить\nАнна\nдобавить\nИван\nследующий\nстоп\n','Введите команду\nОчередь пуста\nВведите команду\nВведите имя\nВведите команду\nВведите имя\nВведите команду\nПриглашён: Анна\nВведите команду\nОстались: [\'Иван\']\n'),('стоп\n','Введите команду\nОстались: []\n'),('добавить\nАня\nдобавить\nАня\nследующий\nстоп\n','Введите команду\nВведите имя\nВведите команду\nВведите имя\nВведите команду\nПриглашён: Аня\nВведите команду\nОстались: [\'Аня\']\n')])
task(mixed,'Скидка для подходящих покупок',WORDING['Скидка для подходящих покупок'],[L], 'def sale_price(price):\n    if price >= 1000:\n        return price - 100\n    return price\n\ndef total_cost(prices):\n    total = 0\n    for price in prices:\n        total = total + sale_price(price)\n    return total\n# вызов\nresult = total_cost(numbers)\nprint("Цены:", numbers)\nprint("К оплате:", result)', [([[999,1000,1000]],'Цены: [999, 1000, 1000]\nК оплате: 2799'),([[]],'Цены: []\nК оплате: 0'),([[0,10]],'Цены: [0, 10]\nК оплате: 10')], signature='def sale_price(price):\n    pass\n\ndef total_cost(prices):')
task(mixed,'Лучшее слово без запретного фрагмента',WORDING['Лучшее слово без запретного фрагмента'],[W('words','Введите текст'),S('banned','Введите запретный фрагмент')], 'best = ""\nfor word in words:\n    if banned not in word:\n        if len(word) > len(best):\n            best = word\nif best == "":\n    print("Нет подходящих слов")\nelse:\n    print("Выбрано:", best)', [(['дом антиспам собака береза','спам'],'Выбрано: собака'),(['котик кот','кот'],'Нет подходящих слов'),(['','а'],'Нет подходящих слов'),(['Спам дом','спам'],'Выбрано: Спам')])
task(mixed,'Сохраняем первую встречу каждого числа',WORDING['Сохраняем первую встречу каждого числа'],[L,I('k','Сколько оставить?')], 'def unique_numbers(numbers):\n    result = []\n    for number in numbers:\n        if number not in result:\n            result.append(number)\n    return result\n\ndef first_unique(numbers, k):\n    return unique_numbers(numbers)[:k]\n# вызов\nresult = first_unique(numbers, k)\nprint("Исходный:", numbers)\nprint("Результат:", result)', [([[4,4,2,4,3],2],'Исходный: [4, 4, 2, 4, 3]\nРезультат: [4, 2]'),([[1,1],0],'Исходный: [1, 1]\nРезультат: []'),([[],5],'Исходный: []\nРезультат: []'),([[-1,2,-1],5],'Исходный: [-1, 2, -1]\nРезультат: [-1, 2]')], signature='def unique_numbers(numbers):\n    pass\n\ndef first_unique(numbers, k):')
task(mixed,'Финал: победители в исходном порядке',WORDING['Финал: победители в исходном порядке'],[W('names','Введите имена через пробел'),L], 'def best_score(scores):\n    best = scores[0]\n    for score in scores:\n        if score > best:\n            best = score\n    return best\n\ndef winner_names(names, scores):\n    best = best_score(scores)\n    result = []\n    for i in range(len(scores)):\n        if scores[i] == best:\n            result.append(names[i])\n    return result\n# вызов\nresult = winner_names(names, numbers)\nprint("Победители:", result)\nprint("Результаты:", numbers)', [(['Аня Боря Вера',[8,3,8]],"Победители: ['Аня', 'Вера']\nРезультаты: [8, 3, 8]"),(['Муса',[-5]],"Победители: ['Муса']\nРезультаты: [-5]"),(['Аня Аня',[0,0]],"Победители: ['Аня', 'Аня']\nРезультаты: [0, 0]"),(['А Б В',[-8,-2,-2]],"Победители: ['Б', 'В']\nРезультаты: [-8, -2, -2]")], signature='def best_score(scores):\n    pass\n\ndef winner_names(names, scores):')
