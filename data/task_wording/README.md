# Переписанные условия задач

Обновлены 40 задач курса «Python. Основы»: 15 в разделе «Циклы», 9 в разделе
«Списки», 8 в разделе «Строки» и 8 в разделе «Функции». Выбраны все задачи
первого раздела и задачи следующих разделов, где длинные объяснения, несколько
этапов или неочевидные правила мешали понять ожидаемый результат.

Условия начинаются с действия пользователя и результата программы. В задачах
про рекорды, перенос очереди, турнир, удаление повторов и фильтры есть короткие
примеры преобразования данных. Формат ввода и вывода указан отдельно от сути
задачи. Сохранены требования к изучаемым приёмам, границам, повторам, регистру
и пустым данным. Три звёздочки в фильтрах записаны как `***`, чтобы Markdown
не воспринимал их как разметку.

Заготовки, открытые и скрытые тесты, примеры, порядок уроков и задач не меняются.
Исправляется только текст первого блока выбранных степов. В функциях сохранён
готовый ввод и вывод, а инструкция про `pass` сформулирована одинаково.

Правила из новых условий независимо сверены с ожидаемым выводом на всех 323
существующих тестах выбранных задач. Проверены схема всех 40 степов и Markdown,
включая буквальное отображение звёздочек и шаблонов вывода. После применения
прочитаны обратно все 250 задач курса: изменены ровно 40 условий, остальные
210 задач, все заготовки и все тесты совпадают с исходными. Повторное применение
не внесло изменений. Сервисы платформы успешно отдают все 40 обновлённых степов.

## Образцы с Google Drive

Изучены документы из всех четырёх переданных папок, включая вложенные разделы.
За образец взяты прямые короткие условия: что вводится, какое действие нужно
выполнить и что должно появиться на экране. Примеры использованы как образец
подачи; сами задачи платформы не заменялись заданиями с Диска.

- [Циклы](https://drive.google.com/drive/folders/1yIl9H8JBZYJ8oqd84n4UsbqM1PXgA3xw):
  [первые упражнения](https://docs.google.com/document/d/17OZe0jIkWOnLXUC5Mdw5BfPGK76w2-jeuza4ySW7rDM),
  [подсчёт слов](https://docs.google.com/document/d/1TjMSby1F6OWnPUCaBrCuLFNCmWlozqC0jwCE5sKEbEo),
  [диапазоны](https://docs.google.com/document/d/1_4g11nWpwgvMo48CxoWzKADJA7baVU8-OrGbBHdKhzU),
  [ввод до остановки](https://docs.google.com/document/d/1CxpcMyQ6Fcp7M38iTu4sT8UPBEPo5DzqeSpmyetLE0U),
  [игра с накоплением суммы](https://docs.google.com/document/d/1HwMpVGdrVIWBPWSwiQ3Uf6uWgGfqjXpnMW9xDa0hla4).
- [Списки](https://drive.google.com/drive/folders/1fEYdJImBWMRNHNBHHWoYps5TXCF3DLaB):
  [введение](https://docs.google.com/document/d/1JDRBZsrckMT0TmXXgkHPfXboGIgTXveVVrkgK0X0yYI),
  [перебор и поиск](https://docs.google.com/document/d/1TCI-hkguT1baBXZLozrpmo2C7FQ2Obla2nSYKf9sJcw),
  [числовые упражнения](https://docs.google.com/document/d/1IPtbodiECevLbtfGe0-z7alUlAbnC--jpYNnDMRAvT0),
  [индексы и связанные списки](https://docs.google.com/document/d/1iFJ4zfa8UiWDcfDyGA8zIjOhCJ6_clOPiJirQ5iylzk).
- [Строки](https://drive.google.com/drive/folders/1Mym2h4OIh5x55DbArUZ5hq-8pQsqiti-):
  [слова и порядок](https://docs.google.com/document/d/1n1uIP8CNTkFENY9DhdJGzaNglHuJrtknJF_2sbs5xkA),
  [перебор символов](https://docs.google.com/document/d/1OylrMMaYmf1oTzkPZIhZp0yI-7bSTGAlw3Txlnrm1rs),
  [анализ текста](https://docs.google.com/document/d/1Nx9a9qZQhuPpB3QuHE0Ke_EQWxl3RN3VckTZ8xUkKrQ).
- [Функции](https://drive.google.com/drive/folders/1vlXTfounIUWgAz45pLInljXrA7v3SfNW):
  [параметры и вызовы](https://docs.google.com/document/d/1ytPMOY70ZdFe-XZxgr8edamaWPMpDU0UljmzxUCxEDQ),
  [возврат результата](https://docs.google.com/document/d/1dZfgn-r3K1fjfRNGnkiV_Htxr76-tYfp7trZTKwzjWE),
  [примеры с пояснениями](https://docs.google.com/document/d/1rKanXYyXC4KaNrGROVW8U7akcl74nERPl_EvV2O0kns).

В образцах встречаются опечатки: в задании про города показаны три города,
но количество 4; в упражнении на список условие говорит о четырёх числах,
а приглашение — о пяти. Поэтому количество вводов и ответы в новых условиях
сверяются с проверкой платформы.

## Файлы

- `content.py` — новые условия и общая инструкция к функциям.
- `originals.json` — прежние условия с открытыми примерами и контрольными
  суммами заготовок и тестов. Скрытые тесты и решения сюда не включены.
- `materials.md` — все новые условия с прежними открытыми примерами для чтения.
- `build.py` — проверка схемы, экспорт, применение и возврат прежнего текста.

## Проверка и применение

Из корня проекта:

```bash
.venv/bin/python -m data.task_wording.build --check --export
```

В работающем Docker Compose:

```bash
docker compose exec -T app mkdir -p /app/data/task_wording
docker compose cp data/task_wording/. app:/app/data/task_wording/
docker compose exec -T app python -m data.task_wording.build --apply --course-id 1
```

Запись выполняется одной транзакцией с блокировками. Перед записью проверяются
курс, степы, прежнее содержимое и контрольные суммы заготовок и всех тестов.
При несовпадении запись отменяется. Повторное применение совпадающей редакции
не меняет данные. Перед изменением сохраняется копия условий в `backups/task_wording`.

Чтобы вернуть прежние формулировки, когда после применения их никто не менял:

```bash
docker compose exec -T app python -m data.task_wording.build --restore --course-id 1
```
