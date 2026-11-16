"""Проверка установленного раздела через API и headless Chrome (порт 9226)."""
import asyncio
import base64
from datetime import datetime, timedelta, UTC
from hashlib import sha256
import json
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
from .build import ROOT, illustrated_section, snapshot


class Browser:
    def __init__(self, websocket):
        self.websocket, self.number = websocket, 0

    async def command(self, method, params=None):
        self.number += 1
        identifier = self.number
        await self.websocket.send(json.dumps({'id': identifier, 'method': method, 'params': params or {}}))
        while True:
            reply = json.loads(await self.websocket.recv())
            if reply.get('id') == identifier:
                if 'error' in reply:
                    raise RuntimeError(reply['error'])
                return reply.get('result', {})

    async def evaluate(self, expression):
        result = await self.command('Runtime.evaluate', {'expression': expression, 'awaitPromise': True, 'returnByValue': True})
        if result.get('exceptionDetails'):
            raise RuntimeError(result['exceptionDetails'])
        return result.get('result', {}).get('value')

    async def visit(self, path, expected):
        await self.command('Page.navigate', {'url': 'http://127.0.0.1:8000' + path})
        for _ in range(100):
            await asyncio.sleep(.1)
            try:
                if await self.evaluate('document.body.innerText.includes(' + json.dumps(expected) + ')'):
                    return
            except RuntimeError:
                pass
        raise RuntimeError('Страница не загрузилась: ' + expected)

    async def screenshot(self, name):
        result = await self.command('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True})
        Path('.codex', name).write_bytes(base64.b64decode(result['data']))


async def main():
    client = docker.from_env()
    cfg = dict(x.split('=', 1) for x in client.containers.get('musacodeacademy-app-1').attrs['Config']['Env'] if '=' in x)
    ip = next(iter(client.containers.get('mca-postgres').attrs['NetworkSettings']['Networks'].values()))['IPAddress']
    engine = create_async_engine(make_url(cfg['SQLALCHEMY_DATABASE_URL']).set(host=ip))
    imported = json.loads((ROOT / 'import-result.json').read_text())
    desired = illustrated_section()
    async with async_sessionmaker(engine)() as db:
        admin_id = await db.scalar(select(User.id).where(User.role == UserRole.ADMIN, User.blocked_at.is_(None)).order_by(User.id).limit(1))
        assert await snapshot(db, imported['course_id'], imported['section_id']) == json.loads((ROOT / 'before-import.json').read_text())
        assert not (await db.scalars(select(Task).join(Step).join(Lesson).where(Lesson.section_id == imported['section_id']))).all()
    await engine.dispose()
    token = jwt.encode({'sub': str(admin_id), 'exp': datetime.now(UTC) + timedelta(minutes=15)}, cfg['SECRET_KEY'], algorithm=cfg['ALGORITHM'])
    auth = {'Authorization': 'Bearer ' + token}
    manifest = json.loads((ROOT / 'images.json').read_text())
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000') as http:
        for lesson, saved_lesson in zip(desired['lessons'], imported['lessons'], strict=True):
            for item, saved in zip(lesson['steps'], saved_lesson['steps'], strict=True):
                response = await http.get('/api/steps/' + str(saved['id']) + '/admin', headers=auth)
                response.raise_for_status()
                assert response.json()['title'] == item['title']
                assert response.json()['content'] == item['content']
            entry = await http.get('/python-gamedev-basics/lessons/' + str(saved_lesson['id']) + '/steps')
            assert entry.status_code == 307 and entry.headers['location'].endswith('/' + str(saved_lesson['steps'][0]['id']))
        for filename, record in manifest.items():
            response = await http.get('/uploads/' + record['storage_path'])
            response.raise_for_status()
            assert response.headers['content-type'].startswith('image/gif')
            assert sha256(response.content).hexdigest() == record['sha256']
    target = httpx.put('http://127.0.0.1:9226/json/new?about:blank').json()
    results = []
    try:
        async with websockets.connect(target['webSocketDebuggerUrl'], max_size=20_000_000) as socket:
            browser = Browser(socket)
            await browser.command('Page.enable')
            await browser.command('Runtime.enable')
            await browser.command('Page.addScriptToEvaluateOnNewDocument', {'source': "localStorage.setItem('musa_code_academy_token'," + json.dumps(token) + ');'})
            for width, height, mobile, label in [(1440, 1100, False, 'desktop'), (390, 844, True, 'mobile')]:
                await browser.command('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': mobile})
                await browser.visit('/python-gamedev-basics/sections/' + str(imported['section_id']) + '/lessons', desired['lessons'][-1]['title'])
                assert not await browser.evaluate('document.documentElement.scrollWidth > innerWidth')
                for lesson in desired['lessons']:
                    assert await browser.evaluate('document.body.innerText.includes(' + json.dumps(lesson['title']) + ')')
                await browser.screenshot('pygame-objects-section-' + label + '.png')
                for lesson, saved_lesson in zip(desired['lessons'], imported['lessons'], strict=True):
                    for item, saved in zip(lesson['steps'], saved_lesson['steps'], strict=True):
                        await browser.visit('/python-gamedev-basics/steps/' + str(saved['id']), item['title'])
                        for _ in range(100):
                            ready = await browser.evaluate("document.querySelector('[data-step-content]')?.getAttribute('aria-busy')==='false' && [...document.querySelectorAll('[data-step-content] img')].every(i=>i.complete&&i.naturalWidth>0)")
                            if ready:
                                break
                            await asyncio.sleep(.1)
                        assert ready
                        await browser.evaluate("document.querySelector('[data-step-drawer-close]')?.click()")
                        await asyncio.sleep(.1)
                        details = await browser.evaluate("""(()=>{
                            const c=document.querySelector('[data-step-content]');
                            return {title:document.querySelector('[data-step-title]').textContent,
                                overflow:document.documentElement.scrollWidth>innerWidth,
                                images:[...c.querySelectorAll('img')].map(i=>({loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight})),
                                code:c.querySelectorAll('.rendered-code .cm-editor').length,
                                navigation:document.querySelectorAll('[data-step-drawer-list] a').length,
                                task_visible:!document.querySelector('[data-task-viewer]').hidden};
                        })()""")
                        assert details['title'] == item['title'] and not details['overflow'], details
                        assert len(details['images']) == sum(b['type'] == 'image' for b in item['content']['blocks']), details
                        assert details['code'] == sum(b['type'] == 'code' for b in item['content']['blocks']), details
                        assert details['navigation'] == len(lesson['steps']) and not details['task_visible'], details
                        results.append({'step_id': saved['id'], 'viewport': label, **details})
                        if saved['id'] in (565, 584):
                            await browser.screenshot('pygame-objects-' + str(saved['id']) + '-' + label + '.png')
    finally:
        httpx.get('http://127.0.0.1:9226/json/close/' + target['id'])
    report = {'previous_materials_unchanged': imported['preserved'], 'api_steps_verified': 22,
              'uploaded_gifs_verified': len(manifest), 'lesson_redirects_verified': 5, 'pages': results}
    (ROOT / 'browser-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: (len(v) if k == 'pages' else v) for k, v in report.items()}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
