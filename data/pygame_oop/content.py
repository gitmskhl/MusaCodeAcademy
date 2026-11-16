"""Школьная редакция уроков и вставка GIF в задания."""
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {s['version']: s for s in json.loads((ROOT / 'sources.json').read_text())}
SECTIONS = json.loads((ROOT / 'curriculum.json').read_text())
MEDIA = {m['version']: m for m in json.loads((ROOT / 'source-media.json').read_text())}
TASK_TITLES = [item['title'] for section in SECTIONS for lesson in section['lessons']
               for item in lesson['steps'] if item['title'].startswith('Задание ')]
MAPPING = []
for number, (source, title) in enumerate(zip(SOURCES.values(), TASK_TITLES, strict=True), 1):
    MAPPING.append(dict(version=source['version'], source=source['url'], task=title,
                        gif=f'task-{number:02}.gif',
                        video=next((u for u in MEDIA[source['version']]['urls'] if 'kinescope.io/' in u), None)))
DEMOS = {m['task']: f'task-{i:02}.gif' for i, m in enumerate(MAPPING, 1)}


def illustrated_sections(manifest=None):
    if manifest is None:
        path = ROOT / 'images.json'
        manifest = json.loads(path.read_text()) if path.exists() else {}
    result = deepcopy(SECTIONS)
    for section in result:
        for lesson in section['lessons']:
            for item in lesson['steps']:
                filename = DEMOS.get(item['title'])
                if filename and filename in manifest:
                    item['content']['blocks'].insert(2, {'type': 'image', 'data': {
                        'file_id': manifest[filename]['file_id'], 'width': 100,
                        'caption': 'Пример результата. Белый указатель и плашка показывают действия — в своей игре их рисовать не нужно. При повторе анимация начинается заново.',
                    }})
    return result
