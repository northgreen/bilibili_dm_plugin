import asyncio
import http.cookies
import logging
import os
import shutil
from typing import *
from urllib.parse import urlparse

import aiohttp
from aiohttp import web

from ictye_live_dm.depends import pluginmain, msgs
from . import blivedm
from .blivedm.clients import ws_base
from .blivedm.models import web as web_models

logger = logging.getLogger(__name__)
local_path = __path__[0]


async def download_file(url, file_name):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            with open(file_name, 'wb') as file:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    file.write(chunk)


async def return_for_face(path: str):
    if path:
        files = os.listdir(os.path.join(local_path, "tmp"))
        file = os.path.basename(urlparse(path).path)
        if file in files:
            return web.FileResponse(os.path.join(local_path, "tmp", file))
        else:
            await download_file(path, os.path.join(local_path, "tmp", file))
            return web.FileResponse(os.path.join(local_path, "tmp", file))


class MessageHandler(blivedm.BaseHandler):
    def __init__(self, lists: list):
        self.user_face: dict = {}
        self.lists = lists

    def _on_danmaku(self, client: blivedm.BLiveClient, message):
        logger.info(f'[{client.room_id}] {message.uname}：{message.msg}')
        self.user_face[message.uname] = ""
        peop_type = {0: 0, 1: 1, 2: 2, 3: 3}
        message = msgs.msg_box(
            message_class="default",
            message_body=msgs.Danmku(
                msg=message.msg,
                who=msgs.msg_who(
                    type=peop_type[message.privilege_type] if message.admin == 0 else 5,
                    name=message.uname,
                    face="/cgi/b_dm_plugin/face?url=" + ""
                ).to_dict()
            ).to_dict(),
            msg_type="Danmku"
        ).to_dict()
        self.lists.append(message)

    def _on_gift(self, client: ws_base.WebSocketClientBase, message: web_models.GiftMessage):
        logger.info(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
                    f' （{message.coin_type}瓜子x{message.total_coin}）')
        people_type = {0: 0, 1: 1, 2: 2, 3: 3}
        message = msgs.msg_box(
            message_class="default",
            message_body=msgs.info(
                msg=f"感谢{message.uname}赠送的{message.gift_name}",
                who=msgs.msg_who(
                    type=people_type[message.guard_level],
                    name=message.uname,
                    face="/cgi/b_dm_plugin/face?url=" + message.face
                ).to_dict(),
                pic=msgs.pic(
                    border=False,
                    pic_url="/cgi/b_dm_plugin/gift?item=" + message.gift_name + ".png"
                ).to_dict()
            ).to_dict(),
            msg_type="info"
        ).to_dict()
        self.lists.append(message)


# cg i
async def cgi_face(request: web.Request) -> web.FileResponse:
    ret = await return_for_face(request.rel_url.query.get("url"))
    return ret


async def cgi_gift(request: web.Request) -> web.FileResponse:
    return web.FileResponse(os.path.join(local_path, "resource", request.rel_url.query.get("item")))


class PluginMain(pluginmain.PluginMain):

    def __init__(self):
        super().__init__()
        self.SESSDATA = None

    def plugin_init(self):
        if os.path.exists(os.path.join(local_path, "tmp")):
            shutil.rmtree(os.path.join(local_path, "tmp"))
            os.mkdir(os.path.join(local_path, "tmp"))
        else:
            os.mkdir(os.path.join(local_path, "tmp"))
        self.plugin_name = "bilibili_dm_plugin"
        self.spirit_cgi_support = True
        self.sprit_cgi_lists["face"] = cgi_face
        self.sprit_cgi_lists["gift"] = cgi_gift
        self.read_config()

        # print(self.config)
        if "session" in self.config:
            self.SESSDATA = self.config["session"]
        else:
            self.config["session"] = ""
            self.update_config(self.config)

        return "message"

    async def plugin_main(self):
        while True:
            await asyncio.sleep(1)

    def plugin_callback(self):
        logger.info(f"plugin {__name__} is done")

    def dm_iter(self, params: dict) -> object:
        class DmIterBack:
            def __init__(self, __params, session):
                self.messages = []
                if "broom" in params:
                    cookies = http.cookies.SimpleCookie()
                    cookies['SESSDATA'] = session
                    cookies['SESSDATA']['domain'] = 'bilibili.com'

                    self.session: Optional[aiohttp.ClientSession]
                    self.session = aiohttp.ClientSession()
                    self.session.cookie_jar.update_cookies(cookies)

                    self.client = blivedm.BLiveClient(params["broom"], session=self.session)

                    handler = MessageHandler(self.messages)
                    self.client.set_handler(handler)
                    self.client.start()
                else:
                    logger.error("unexpected room, client will be invalid!")

            async def __aiter__(self):
                try:
                    yield self.messages.pop()
                except IndexError:
                    return

            async def callback(self):
                logger.info("blivedm closing")
                if hasattr(self, "client"):
                    await self.session.close()
                    await self.client.stop_and_close()

        return DmIterBack(params, self.SESSDATA)
