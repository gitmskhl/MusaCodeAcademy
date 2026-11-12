"""Привязка настоящих снимков окон к степам и бережное добавление в БД."""
import argparse
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .content import LESSON

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "images.json"
# Номер степа, имя файла, подпись. Картинки идут после объяснения соответствующего опыта.
IMAGES = [
    (2, "window-800x600.png", "Окно 800×600 после добавления while True: программа продолжает работать. Рамка окна в размер области для рисования не входит."),
    (3, "window-1000x400.png", "После замены размера на (1000, 400) окно стало шире и ниже. Сравни с окном из предыдущего степа."),
    (8, "blue-background.png", "Результат опыта с screen.fill((30, 60, 120)) и pygame.display.update(): вся область окна заполнена синим цветом."),
    (10, "practice-result.png", "Ожидаемый вид окна из практики: область 960×540 и фон RGB (40, 100, 160)."),
]


def illustrated_lesson(manifest=None):
    lesson = deepcopy(LESSON)
    if manifest is None:
        manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for number, filename, caption in IMAGES:
        if filename in manifest:
            lesson["steps"][number - 1]["content"]["blocks"].append({
                "type": "image", "data": {"file_id": manifest[filename]["file_id"], "width": 100, "caption": caption}})
    return lesson


async def apply(lesson_id):
    from fastapi import UploadFile
    from starlette.datastructures import Headers
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, File, Lesson, Section, Step
    from app.services.storage import storage_service

    manifest = {}
    created_paths = []
    committed = False
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).join(Section).join(Lesson).where(
                Lesson.id == lesson_id).with_for_update(of=Course))
            if course is None or course.slug != "python-gamedev-basics":
                raise ValueError("Урок не принадлежит курсу разработки игр")
            saved = (await session.scalars(select(Step).where(Step.lesson_id == lesson_id).order_by(Step.order).with_for_update())).all()
            previous = illustrated_lesson()
            base = [(s["title"], i, s["content"]) for i, s in enumerate(LESSON["steps"])]
            existing = [(s.title, s.order, s.content) for s in saved]
            last_export = [(s["title"], i, s["content"]) for i, s in enumerate(previous["steps"])]
            if existing != base and existing != last_export:
                raise ValueError("Урок изменен после подготовки материала; автоматическое добавление остановлено")
            for _, filename, _ in IMAGES:
                source = ROOT / "images" / filename
                digest = sha256(source.read_bytes()).hexdigest()
                original = "pygame-intro-" + source.stem + "-" + digest[:16] + ".png"
                file = await session.scalar(select(File).where(File.original_filename == original))
                if file is None:
                    with source.open("rb") as stream:
                        upload = UploadFile(file=stream, filename=original, headers=Headers({"content-type": "image/png"}))
                        stored = await storage_service.save_image(upload)
                    created_paths.append(stored.storage_path)
                    file = File(file_type=stored.file_type, original_filename=stored.original_filename,
                                storage_path=stored.storage_path, mime_type=stored.mime_type, size=stored.size)
                    session.add(file)
                    await session.flush()
                stored_path = storage_service.upload_dir / file.storage_path
                if not stored_path.is_file() or sha256(stored_path.read_bytes()).hexdigest() != digest:
                    raise ValueError("Содержимое загруженного файла не совпадает со снимком")
                manifest[filename] = {"file_id": file.id, "storage_path": file.storage_path, "sha256": digest}
            desired = illustrated_lesson(manifest)
            for target, source in zip(saved, desired["steps"], strict=True):
                if target.content != source["content"]:
                    target.content = source["content"]
        committed = True
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Урок {lesson_id}: прикреплены {len(IMAGES)} скриншота, остальной материал сохранен.")
    except Exception:
        if not committed:
            for path in created_paths:
                await storage_service.delete(path)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", required=True)
    parser.add_argument("--lesson-id", type=int, required=True)
    args = parser.parse_args()
    asyncio.run(apply(args.lesson_id))
