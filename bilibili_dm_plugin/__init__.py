#  Copyright (c) 2023 楚天寻箫（ictye）
#
#    此软件基于楚天寻箫非商业开源软件许可协议 1.0发布.
#    您可以根据该协议的规定，在非商业或商业环境中使用、分发和引用此软件.
#    惟分发此软件副本时，您不得以商业方式获利，并且不得限制用户获取该应用副本的体验.
#    如果您修改或者引用了此软件，请按协议规定发布您的修改源码.
#
#    此软件由版权所有者提供，没有明确的技术支持承诺，使用此软件和源码造成的任何损失，
#    版权所有者概不负责。如需技术支持，请联系版权所有者或社区获取最新版本。
#
#   更多详情请参阅许可协议文档
import asyncio

try_imp = True
import sys

sys.path.append("./")

from . import blivedm
from depends import plugin_main, msgs, connects

import aiohttp
from typing import *
import http.cookies
from .blivedm.clients import ws_base
from .blivedm.models import web as web_models

session: Optional[aiohttp.ClientSession] = None
SESSDATA = ''


class Handler(blivedm.BaseHandler):
    def __init__(self, lists: list):
        self.user_face: dict = {}
        self.lists = lists

    def _on_danmaku(self, client: blivedm.BLiveClient, message):
        print(f'[{client.room_id}] {message.uname}：{message.msg}')
        self.user_face[message.uname] = message.face
        peop_type = {0: 0, 1: 1, 2: 2, 3: 3}
        message = msgs.msg_box(
            message_class="default",
            message_body=msgs.dm(
                msg=message.msg,
                who=msgs.msg_who(
                    type=peop_type[message.privilege_type] if message.admin == 0 else 5,
                    name=message.uname,
                    face=message.face
                ).to_dict()
            ).to_dict(),
            msg_type="dm"
        ).to_dict()
        self.lists.append(message)

    def _on_gift(self, client: ws_base.WebSocketClientBase, message: web_models.GiftMessage):
        print(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
              f' （{message.coin_type}瓜子x{message.total_coin}）')
        peop_type = {0: 0, 1: 1, 2: 2, 3: 3}
        message = msgs.msg_box(
            message_class="default",
            message_body=msgs.info(
                msg=f"感谢{message.uname}赠送的{message.gift_name}",
                who=msgs.msg_who(
                    type=peop_type[message.guard_level],
                    name=message.uname,
                    face=message.face
                ).to_dict(),
                pic=self.user_face[message.uname] if message.uname in self.user_face else "null"
            ).to_dict(),
            msg_type="info"
        ).to_dict()
        self.lists.append(message)


# noinspection DuplicatedCode
class Plugin_Main(plugin_main.Plugin_Main):

    def plugin_init(self):
        self.runners = []

        self.sprit_cgi_support = True
        self.sprit_cgi_path = "test"
        return "message"

    async def sprit_cgi(self, request):
        return self.web.Response(text="ok")

    async def plugin_main(self):
        while True:
            await asyncio.sleep(1)

    def plugin_callback(self):
        print(f"plugin {__name__} is done")

    def dm_iter(self, params: dict, connect_waper: connects.connect_wrapper) -> object:
        class dm_iter_back:
            def __init__(self, params, connect_waper):
                self.messages = []

                cookies = http.cookies.SimpleCookie()
                cookies['SESSDATA'] = SESSDATA
                cookies['SESSDATA']['domain'] = 'bilibili.com'

                session = aiohttp.ClientSession()
                session.cookie_jar.update_cookies(cookies)

                self.client = blivedm.BLiveClient(params["broom"], session=session)

                handler = Handler(self.messages)
                self.client.set_handler(handler)
                self.client.start()

            async def __aiter__(self):
                try:
                    yield self.messages.pop()
                except IndexError:
                    return

            def __del__(self):
                asyncio.get_event_loop().create_task(self.client.stop_and_close())

        return dm_iter_back(params, connect_waper)
