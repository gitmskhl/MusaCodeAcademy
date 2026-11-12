"""Бережно добавить практику с GIF к уже установленным 12 степам урока."""
import argparse
import asyncio
from hashlib import sha256
import json
from .content import LESSON
from .illustrations import ROOT, MANIFEST, illustrated_lesson


async def apply(lesson_id):
    from fastapi import UploadFile
    from starlette.datastructures import Headers
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, File, Lesson, Section, Step
    from app.services.storage import storage_service

    manifest = json.loads(MANIFEST.read_text())
    created_paths = []
    committed = False
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).join(Section).join(Lesson).where(
                Lesson.id == lesson_id).with_for_update(of=Course))
            lesson = await session.get(Lesson, lesson_id)
            if course is None or course.slug != 'python-gamedev-basics' or lesson.title != LESSON['title'] or lesson.order != 2:
                raise ValueError('Нужен третий урок Pygame о движении')
            saved = (await session.scalars(select(Step).where(
                Step.lesson_id == lesson_id).order_by(Step.order).with_for_update())).all()
            expected = illustrated_lesson()
            def rows(items):
                return [(s['title'], i, s['content']) for i, s in enumerate(items)]
            existing = [(s.title, s.order, s.content) for s in saved]
            if len(saved) not in (12, 13) or existing[:12] != rows(expected['steps'][:12]):
                raise ValueError('Материал урока отличается от экспорта; добавление остановлено')
            source = ROOT / 'images' / 'jump.gif'
            digest = sha256(source.read_bytes()).hexdigest()
            original = 'pygame-movement-jump-' + digest[:16] + '.gif'
            file = await session.scalar(select(File).where(File.original_filename == original))
            if file is None:
                with source.open('rb') as stream:
                    stored = await storage_service.save_image(UploadFile(
                        file=stream, filename=original, headers=Headers({'content-type': 'image/gif'})))
                created_paths.append(stored.storage_path)
                file = File(file_type=stored.file_type, original_filename=stored.original_filename,
                            storage_path=stored.storage_path, mime_type=stored.mime_type, size=stored.size)
                session.add(file)
                await session.flush()
            path = storage_service.upload_dir / file.storage_path
            if not path.is_file() or sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Загруженный GIF отличается от исходника')
            manifest['jump.gif'] = {'file_id': file.id, 'storage_path': file.storage_path, 'sha256': digest}
            desired = illustrated_lesson(manifest)['steps'][-1]
            if len(saved) == 13:
                if existing[-1] != (desired['title'], 12, desired['content']):
                    raise ValueError('Последний степ отличается; перезапись остановлена')
                target = saved[-1]
                print(f'Степ {target.id}: практика уже совпадает, изменений нет.')
            else:
                target = Step(lesson_id=lesson_id, order=12, **desired)
                session.add(target)
                await session.flush()
                print(f'Урок {lesson_id}: добавлен степ {target.id} с заданием и GIF; прежние 12 степов сохранены.')
        committed = True
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    except Exception:
        if not committed:
            for path in created_paths:
                await storage_service.delete(path)
        raise
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', required=True, action='store_true')
    parser.add_argument('--lesson-id', required=True, type=int)
    args = parser.parse_args()
    asyncio.run(apply(args.lesson_id))
