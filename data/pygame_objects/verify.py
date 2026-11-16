"""Проверки поведения учебных программ, образцов и соответствия GIF."""
from copy import deepcopy
from PIL import Image

from .content import STATIC, TIMER, MOVING, CLICK, PREVIEW
from .render import Sample, SOURCES, frames, ROOT, pygame


def click(pos, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def verify():
    static = Sample(STATIC)
    for point, color in [((150, 180), (255, 80, 80)), ((400, 300), (80, 255, 120)), ((650, 420), (80, 160, 255))]:
        assert tuple(static.screen.get_at(point))[:3] == color
    timer = Sample(TIMER)
    for frame in range(2, 181):
        scope = timer.tick()
        assert scope['bright'] == (frame // 60 % 2 == 1)
        assert scope['timer'] == 60 - frame % 60
    moving = Sample(MOVING)
    for _ in range(19):
        moving.tick()
    assert [(p[0], p[1]) for p in moving.scope['circles']] == [(160, 150), (400, 120)]
    expected = pygame.Surface((800, 600))
    for p in moving.scope['circles']:
        pygame.draw.circle(expected, p[2], (p[0], p[1]), p[3])
    assert pygame.image.tostring(expected, 'RGB') == pygame.image.tostring(moving.screen, 'RGB')
    clicking = Sample(CLICK)
    clicking.tick(click((100, 100)), click((200, 200)), pos=(600, 500))
    assert clicking.scope['points'] == [[100, 100], [200, 200]]
    clicking.tick(click((300, 300), 3), held=True)
    assert len(clicking.scope['points']) == 2
    preview = Sample(PREVIEW)
    preview.tick(pos=(100, 100))
    assert tuple(preview.screen.get_at((100, 100)))[:3] == (255, 200, 80)
    assert tuple(preview.screen.get_at((110, 110)))[:3] == (100, 100, 100)
    preview.tick(pos=(300, 300))
    assert tuple(preview.screen.get_at((100, 100)))[:3] == (100, 100, 100)

    circles = Sample(SOURCES['circles.gif'])
    for frame in range(2, 361):
        circles.tick()
        assert len(circles.scope['particles']) == frame // 120
    old = deepcopy(circles.scope['particles'])
    circles.tick()
    assert old == circles.scope['particles']
    assert all(30 <= p[0] <= 770 and 30 <= p[1] <= 570 for p in old)
    assert len({tuple(p[2]) for p in old}) > 1

    rain = Sample(SOURCES['rain.gif'])
    for frame in range(2, 101):
        rain.tick()
        assert len(rain.scope['squares']) == frame // 10
    for p in rain.scope['squares']:
        assert 10 <= p[2] <= 30 and 2 <= p[3] <= 6 and 0 <= p[0] <= 800 - p[2]
    rain.scope['squares'] = [[50, 601, 20, 2, [255, 0, 0]], [60, 602, 20, 2, [0, 255, 0]], [100, 50, 20, 2, [0, 0, 255]]]
    rain.tick()
    assert len(rain.scope['squares']) == 1 and rain.scope['squares'][0][1] == 52

    fall = Sample(SOURCES['fall.gif'])
    for frame in range(2, 121):
        fall.tick()
        assert len(fall.scope['particles']) == frame // 60
    assert all(p[4] == 0 and 2 <= p[5] <= 6 for p in fall.scope['particles'])
    types = Sample(SOURCES['types.gif'])
    seen, last_creation = set(), 30
    for frame in range(2, 1001):
        types.tick()
        scope = types.scope
        if scope['timer'] >= 30 and any((p[6] == 'top' and p[1] == p[5]) or (p[6] == 'side' and p[0] == p[4]) for p in scope['particles']):
            if frame != 30:
                assert 30 <= frame - last_creation <= 60
            last_creation = frame
        for p in scope['particles']:
            seen.add(p[6])
            assert (p[6] == 'top' and p[4] == 0 and 2 <= p[5] <= 6) or (p[6] == 'side' and p[5] == 0 and 2 <= p[4] <= 6)
    assert seen == {'top', 'side'}

    dots = Sample(SOURCES['click.gif'])
    dots.tick(click((100, 100)), click((200, 100), 2), click((300, 100), 3), click((400, 100), 4), pos=(500, 400))
    assert dots.scope['points'] == [[100, 100], [200, 100], [300, 100]]
    dots.tick(held=True)
    assert len(dots.scope['points']) == 3
    up = Sample(SOURCES['up.gif'])
    up.tick(pos=(100, 400))
    up.tick(pos=(100, 400))
    p = up.scope['particles'][0]
    assert p[0] == 100 and 3 <= p[3] <= 12 and -5 <= p[5] <= -2
    before = p[1]
    up.tick(pos=(700, 500))
    assert p[0] == 100 and p[1] == before + p[5]
    for frame in range(5, 61):
        up.tick(pos=(700, 500))
    assert len(up.scope['particles']) == 20
    for _ in range(3):
        up.tick(pos=(-10, 200))
    assert len(up.scope['particles']) == 20

    balls = Sample(SOURCES['balls.gif'])
    for _ in range(60):
        balls.tick(held=True, pos=(400, 300))
    assert len(balls.scope['balls']) == 60
    assert all(2 <= p[2] <= 8 and (p[3] or p[4]) for p in balls.scope['balls'])
    positions = [(p[0], p[1]) for p in balls.scope['balls']]
    velocities = [(p[3], p[4]) for p in balls.scope['balls']]
    balls.tick(pos=(700, 500), held=False)
    assert len(balls.scope['balls']) == 60
    # Первый шарик сохраняет свое движение после отпускания.
    p = balls.scope['balls'][0]
    assert (p[0], p[1]) == (positions[0][0] + velocities[0][0], positions[0][1] + velocities[0][1])

    # Несколько соседних невидимых объектов удаляются без пропуска;
    # касающийся края круг остается до полного выхода.
    for name in ('fall.gif', 'types.gif', 'up.gif'):
        sample = Sample(SOURCES[name])
        sample.scope['particles'] = [[-30, 200, [255, 0, 0], 20, 0, 0, 'side'],
                                     [830, 200, [255, 0, 0], 20, 0, 0, 'side'],
                                     [400, -21, [255, 0, 0], 20, 0, 0, 'top'],
                                     [400, 621, [255, 0, 0], 20, 0, 0, 'top'],
                                     [400, -20, [255, 0, 0], 20, 0, 0, 'top']]
        sample.tick()
        assert len(sample.scope['particles']) == 1
    balls.scope['balls'] = [[-9, 100, 8, 0, 0, [255, 0, 0]], [809, 100, 8, 0, 0, [255, 0, 0]], [400, 300, 8, 0, -1, [255, 0, 0]]]
    balls.tick()
    assert len(balls.scope['balls']) == 1

    editor = Sample(SOURCES['editor.gif'])
    editor.tick(click((120, 180)), pos=(500, 400))
    editor.tick(pos=(600, 500), held=True)
    assert editor.scope['shapes'] == [[120, 180]]
    assert tuple(editor.screen.get_at((130, 190)))[:3] == (255, 200, 80)
    editor2 = Sample(SOURCES['editor2.gif'])
    editor2.tick(click((100, 100)), pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2), click((300, 300)))
    assert editor2.scope['shapes'] == [[100, 100, 1], [300, 300, 2]]
    editor2.tick(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1), pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), held=True)
    assert editor2.scope['current_type'] == 1 and editor2.scope['shapes'] == [[100, 100, 1], [300, 300, 2]]
    assert tuple(editor2.screen.get_at((300, 300)))[:3] == (255, 200, 80)
    assert tuple(editor2.screen.get_at((329, 329)))[:3] == (100, 100, 100)

    for source in [STATIC, TIMER, MOVING, CLICK, PREVIEW, *SOURCES.values()]:
        sample = Sample(source)
        try:
            sample.tick(pygame.event.Event(pygame.QUIT))
        except SystemExit:
            pass
        else:
            raise AssertionError('QUIT не завершил программу')

    total = 0
    for filename in SOURCES:
        with Image.open(ROOT / 'images' / filename) as saved:
            palette = Image.new('P', (1, 1))
            palette.putpalette(saved.getpalette())
            sequence = list(frames(filename))
            assert saved.n_frames == len(sequence)
            for index, (canvas, _) in enumerate(sequence):
                saved.seek(index)
                expected = canvas.quantize(palette=palette, dither=Image.Dither.NONE).convert('RGB')
                assert saved.convert('RGB').tobytes() == expected.tobytes(), (filename, index)
                assert saved.info['duration'] == 100
                total += 1
    pygame.quit()
    print(f'Проверены 5 учебных программ, 9 образцов: таймеры, движение, клики, удержание, типы, удаление, QUIT и {total} кадров GIF.')


if __name__ == '__main__':
    verify()
