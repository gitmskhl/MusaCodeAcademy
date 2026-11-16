"""Сверка каждого отображаемого кадра GIF с повторным исполнением сцены."""
from hashlib import sha256
import json

from PIL import Image, ImageChops
from .render import ROOT, frames, check, palette, pygame, LENGTHS


def main():
    pygame.init()
    shared_palette = palette()
    report = {}
    for number in range(1, 17):
        path = ROOT / 'images' / f'task-{number:02}.gif'
        gif = Image.open(path)
        encoded, durations = [], []
        for index in range(gif.n_frames):
            gif.seek(index)
            assert gif.size == (800, 680) and gif.info['duration'] % 100 == 0
            frame = gif.convert('RGB')
            for _ in range(gif.info['duration'] // 100):
                encoded.append(frame)
            durations.append(gif.info['duration'])
        assert len(encoded) == LENGTHS[number] // 6
        count = 0
        held_ground = None
        for count, (image, scene) in enumerate(frames(number), 1):
            expected = image.quantize(palette=shared_palette, dither=Image.Dither.NONE).convert('RGB')
            assert ImageChops.difference(expected, encoded[count - 1]).getbbox() is None, (number, count)
            assert scene.on_ground != scene.carried
            if number == 16 and scene.phase in (2, 3):
                if held_ground is None:
                    held_ground = tuple(scene.crystal)
                assert tuple(scene.crystal) == held_ground
        check(number, scene)
        report[path.name] = dict(sha256=sha256(path.read_bytes()).hexdigest(),
                                decoded_frames=gif.n_frames, compared_time_samples=count,
                                total_duration_ms=sum(durations), state_checks=True)
        print(path.name, 'OK', count, flush=True)
    pygame.quit()
    (ROOT / 'media-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
