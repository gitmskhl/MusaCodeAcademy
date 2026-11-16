"""Единое имя метода рисования учебных объектов."""
import re

STEP_TITLE_RENAMES = {
    'Метод draw и список объектов': 'Метод render и список объектов',
    'update изменяет, draw показывает': 'update изменяет, render показывает',
}


def use_render(value):
    if isinstance(value, str):
        # Имена функций самой библиотеки остаются pygame.draw.circle и т. п.
        value = re.sub(r'(?<![\w.])draw\.(circle|rect|polygon|ellipse|line)\b', r'pygame.draw.\1', value)
        value = re.sub(r'(?<!pygame\.)\bdraw\b', 'render', value)
        value = value.replace(
            'render — просто другое имя знакомого render. В этой игре используем render у обоих классов для рисования.',
            'render — название метода рисования. Используем его у игрока и монетки.')
        return value
    if isinstance(value, list):
        return [use_render(item) for item in value]
    if isinstance(value, dict):
        return {key: use_render(item) for key, item in value.items()}
    return value
