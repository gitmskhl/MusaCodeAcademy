"""Read-only проверка API и страниц новых разделов (Chrome CDP на 9227)."""
import asyncio
import base64
from datetime import datetime, timedelta, UTC
import json
from hashlib import sha256
from pathlib import Path

import docker
import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import websockets

from app.enums import UserRole
from app.models import User, Task, Step, Lesson
from .build import ROOT, SLUG, snapshot
from .content import illustrated_sections
from .naming import STEP_TITLE_RENAMES


class Browser:
    def __init__(self, socket):
        self.socket, self.number = socket, 0

    async def command(self, method, params=None):
        self.number += 1
        await self.socket.send(json.dumps(dict(id=self.number, method=method, params=params or {})))
        while True:
            reply = json.loads(await self.socket.recv())
            if reply.get('id') == self.number:
                if 'error' in reply:
                    raise RuntimeError(reply['error'])
                return reply.get('result', {})

    async def evaluate(self, expression):
        result = await self.command('Runtime.evaluate', dict(expression=expression, awaitPromise=True, returnByValue=True))
        if result.get('exceptionDetails'):
            raise RuntimeError(result['exceptionDetails'])
        return result.get('result', {}).get('value')

    async def visit(self, path, expected, step=False):
        await self.command('Page.navigate', dict(url='http://127.0.0.1:8000' + path))
        for _ in range(100):
            await asyncio.sleep(.1)
            try:
                title_ready = await self.evaluate('document.body.innerText.includes(' + json.dumps(expected) + ')')
                if title_ready and (not step or await self.evaluate("document.querySelector('[data-step-content]')?.getAttribute('aria-busy')==='false'")):
                    return
            except RuntimeError:
                pass
        raise RuntimeError('Не загрузилась страница: ' + expected)

    async def screenshot(self, name):
        result = await self.command('Page.captureScreenshot', dict(format='png', captureBeyondViewport=True))
        Path('.codex', name + '.png').write_bytes(base64.b64decode(result['data']))


async def main():
    client = docker.from_env()
    cfg = dict(x.split('=', 1) for x in client.containers.get('musacodeacademy-app-1').attrs['Config']['Env'] if '=' in x)
    ip = next(iter(client.containers.get('mca-postgres').attrs['NetworkSettings']['Networks'].values()))['IPAddress']
    engine = create_async_engine(make_url(cfg['SQLALCHEMY_DATABASE_URL']).set(host=ip))
    imported = json.loads((ROOT / 'import-result.json').read_text())
    SECTIONS = illustrated_sections()
    manifest = json.loads((ROOT / 'images.json').read_text())
    section_ids = [s['id'] for s in imported['sections']]
    async with async_sessionmaker(engine)() as db:
        admin_id = await db.scalar(select(User.id).where(User.role == UserRole.ADMIN, User.blocked_at.is_(None)).order_by(User.id).limit(1))
        assert admin_id is not None
        assert await snapshot(db, imported['course_id'], section_ids) == json.loads((ROOT / 'before-import.json').read_text())
        assert not (await db.scalars(select(Task).join(Step).join(Lesson).where(Lesson.section_id.in_(section_ids)))).all()
        backup = json.loads((ROOT / 'revisions/before-school-update.json').read_text())
        current = await snapshot(db, imported['course_id'])
        new_by_id = {s['id']: s for s in current['steps']}
        old_lesson_ids = {l['id'] for l in backup['lessons'] if l['section_id'] in section_ids}
        old_oop = [s for s in backup['steps'] if s['lesson_id'] in old_lesson_ids]
        for old_step in old_oop:
            saved = new_by_id[old_step['id']]
            assert (saved['title'], saved['lesson_id']) == (STEP_TITLE_RENAMES.get(old_step['title'], old_step['title']), old_step['lesson_id'])
    await engine.dispose()
    token = jwt.encode(dict(sub=str(admin_id), exp=datetime.now(UTC) + timedelta(minutes=15)), cfg['SECRET_KEY'], algorithm=cfg['ALGORITHM'])
    auth = {'Authorization': 'Bearer ' + token}
    api_steps = redirects = 0
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000') as http:
        for filename, record in manifest.items():
            response = await http.get('/uploads/' + record['storage_path'])
            response.raise_for_status()
            assert response.headers['content-type'].startswith('image/gif')
            assert sha256(response.content).hexdigest() == record['sha256']
        response = await http.get('/api/courses/3/sections/admin', headers=auth)
        response.raise_for_status()
        assert [(s['order'], s['title']) for s in response.json()][-2:] == [(i + 2, s['title']) for i, s in enumerate(SECTIONS)]
        for source, saved in zip(SECTIONS, imported['sections'], strict=True):
            for lesson, saved_lesson in zip(source['lessons'], saved['lessons'], strict=True):
                response = await http.get(f'/{SLUG}/lessons/{saved_lesson["id"]}/steps')
                assert response.status_code == 307 and response.headers['location'].endswith('/' + str(saved_lesson['steps'][0]['id']))
                redirects += 1
                for item, saved_step in zip(lesson['steps'], saved_lesson['steps'], strict=True):
                    response = await http.get(f'/api/steps/{saved_step["id"]}/admin', headers=auth)
                    response.raise_for_status()
                    assert response.json()['title'] == item['title'] and response.json()['content'] == item['content']
                    api_steps += 1
    target = httpx.put('http://127.0.0.1:9227/json/new?about:blank').json()
    pages = []
    try:
        async with websockets.connect(target['webSocketDebuggerUrl'], max_size=30_000_000) as socket:
            browser = Browser(socket)
            await browser.command('Page.enable')
            await browser.command('Runtime.enable')
            await browser.command('Page.addScriptToEvaluateOnNewDocument', dict(source="localStorage.setItem('musa_code_academy_token'," + json.dumps(token) + ');'))
            for width, height, mobile, label in [(1440, 1100, False, 'desktop'), (390, 844, True, 'mobile')]:
                await browser.command('Emulation.setDeviceMetricsOverride', dict(width=width, height=height, deviceScaleFactor=1, mobile=mobile))
                await browser.visit(f'/{SLUG}/sections', SECTIONS[-1]['title'])
                assert not await browser.evaluate('document.documentElement.scrollWidth > innerWidth')
                await browser.screenshot('pygame-oop-sections-' + label)
                for section, saved in zip(SECTIONS, imported['sections'], strict=True):
                    await browser.visit(f'/{SLUG}/sections/{saved["id"]}/lessons', section['lessons'][-1]['title'])
                    assert not await browser.evaluate('document.documentElement.scrollWidth > innerWidth')
                    for lesson in section['lessons']:
                        assert await browser.evaluate('document.body.innerText.includes(' + json.dumps(lesson['title']) + ')')
                    for lesson, saved_lesson in zip(section['lessons'], saved['lessons'], strict=True):
                        for item, saved_step in zip(lesson['steps'], saved_lesson['steps'], strict=True):
                            await browser.visit(f'/{SLUG}/steps/{saved_step["id"]}', item['title'], step=True)
                            for _ in range(100):
                                ready = await browser.evaluate("[...document.querySelectorAll('[data-step-content] img')].every(i=>i.complete&&i.naturalWidth===800&&i.naturalHeight===680)")
                                if ready:
                                    break
                                await asyncio.sleep(.1)
                            assert ready
                            await browser.evaluate("document.querySelector('[data-step-drawer-close]')?.click()")
                            details = await browser.evaluate("""(()=>{
                                const c=document.querySelector('[data-step-content]');
                                return {title:document.querySelector('[data-step-title]').textContent,
                                    overflow:document.documentElement.scrollWidth>innerWidth,
                                    code:c.querySelectorAll('.rendered-code .cm-editor').length,
                                    images:c.querySelectorAll('img').length,
                                    videos:[...c.querySelectorAll('a[href*="kinescope.io/"]')].map(a=>a.href),
                                    navigation:document.querySelectorAll('[data-step-drawer-list] a').length,
                                    task_visible:!document.querySelector('[data-task-viewer]').hidden};
                            })()""")
                            assert details['title'] == item['title'] and not details['overflow'], details
                            assert details['code'] == sum(b['type'] == 'code' for b in item['content']['blocks']), details
                            assert details['images'] == (1 if item['title'].startswith('Задание ') else 0), details
                            assert details['navigation'] == len(lesson['steps']) and not details['task_visible'], details
                            pages.append(dict(step_id=saved_step['id'], viewport=label, **details))
                            if saved_step['id'] in (585, 588, 602, 626, 642, 644, 645):
                                if details['images']:
                                    await asyncio.sleep(1.3)
                                await browser.screenshot(f'pygame-oop-{saved_step["id"]}-{label}')
    finally:
        httpx.get('http://127.0.0.1:9227/json/close/' + target['id'])
    report = dict(api_steps_verified=api_steps, lesson_redirects_verified=redirects,
                  gifs_verified=len(manifest), preserved_oop_step_ids=len(old_oop),
                  video_links=sum(len(p['videos']) for p in pages if p['viewport']=='desktop'),
                  previous_materials_unchanged=imported['preserved'], pages=pages)
    (ROOT / 'browser-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(api_steps=api_steps, redirects=redirects, pages=len(pages), previous_materials_unchanged=True)))


if __name__ == '__main__':
    asyncio.run(main())
