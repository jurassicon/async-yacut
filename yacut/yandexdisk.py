import asyncio
import os
import uuid
from typing import List, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

API_HOST = 'https://cloud-api.yandex.net/'
API_VERSION = 'v1'
REQUEST_UPLOAD_URL = f'{API_HOST}{API_VERSION}/disk/resources/upload'
RESOURCES_URL = f'{API_HOST}{API_VERSION}/disk/resources'
PUBLISH_URL = f'{API_HOST}{API_VERSION}/disk/resources/publish'
DOWNLOAD_URL = f'{API_HOST}{API_VERSION}/disk/resources/download'

load_dotenv()
DISK_TOKEN = os.environ.get('DISK_TOKEN')
AUTH_HEADER = {'Authorization': f'OAuth {DISK_TOKEN}'}

_CONCURRENCY = int(os.getenv('YA_CONCURRENCY', '4'))
_SEM = asyncio.Semaphore(_CONCURRENCY)


def _ensure_token():
    if not DISK_TOKEN:
        raise RuntimeError('DISK_TOKEN не задан. Добавьте его в .env')


def _safe_remote_path(original_filename: str) -> str:
    name = secure_filename(original_filename) or 'file'
    stem, dot, ext = name.partition('.')
    unique = uuid.uuid4().hex
    final_name = f'{stem[:40]}_{unique}' + (f'.{ext}' if dot else '')
    return f'app:/{final_name}'


async def _get_upload_href(session: ClientSession, remote_path: str) -> str:
    async with session.get(
            REQUEST_UPLOAD_URL,
            params={'path': remote_path, 'overwrite': 'true'},
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
        return data['href']


async def _publish_and_get_public_url(session: ClientSession,
                                      remote_path: str) -> str:
    async with session.put(PUBLISH_URL, params={'path': remote_path}) as pub:
        if pub.status not in (200, 202, 409):
            pub.raise_for_status()

    async with session.get(RESOURCES_URL,
                           params={'path': remote_path}) as meta:
        meta.raise_for_status()
        data = await meta.json()
        public_url = data.get('public_url')
        if not public_url:
            raise RuntimeError(
                'Не удалось получить public_url после публикации.')
        return public_url


async def _iter_file_async(stream, chunk_size: int = 1 << 20):
    loop = asyncio.get_running_loop()
    while True:
        chunk = await loop.run_in_executor(None, stream.read, chunk_size)
        if not chunk:
            break
        yield chunk


async def _upload_one(session: ClientSession, file_storage) -> Optional[str]:
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None

    remote_path = _safe_remote_path(file_storage.filename)

    async with _SEM:
        href = await _get_upload_href(session, remote_path)
        async with session.put(href, data=_iter_file_async(
                file_storage.stream)) as put_resp:
            put_resp.raise_for_status()

        download_href = await _get_download_href(session, remote_path)
        return download_href


async def _get_download_href(session: ClientSession, remote_path: str) -> str:
    async with session.get(DOWNLOAD_URL, params={'path': remote_path}) as resp:
        resp.raise_for_status()
        data = await resp.json()
        return data['href']


async def upload_files_to_disk(files: List) -> List[str]:
    _ensure_token()
    if not files:
        return []

    timeout = ClientTimeout(total=600)  # общий таймаут.
    async with aiohttp.ClientSession(headers=AUTH_HEADER,
                                     timeout=timeout) as session:
        tasks = [
            asyncio.create_task(_upload_one(session, f))
            for f in files
            if f and getattr(f, 'filename', None)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    urls: List[str] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        if r:
            urls.append(r)
    return urls
