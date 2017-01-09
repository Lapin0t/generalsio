# -*- coding: utf-8 -*-


import asyncio
import logging
import json

import websockets


_ENDPOINTS = {
        'na': 'ws://ws.generals.io/socket.io/?EIO=3&transport=websocket',
        'eu': 'ws://euws.generals.io/socket.io/?EIO=3&transport=websocket'}

_REPLAY_URLS = {
        'na': 'http://generals.io/replays/',
        'eu': 'http://eu.generals.io/replays/'}


TILE_EMPTY = -1
TILE_MOUNTAIN = -2
TILE_FOG = -3
TILE_OBSTACTLE = -4


_JOIN_MSG = {'1v1': 'join_1v1', 'team': 'join_team', 'ffa': 'play'}


class APIClient:
    def __init__(self, region='na', loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop

        self._region = region

    async def __aenter__(self):
        logging.debug('creating connection')
        f_ws = websockets.connect(_ENDPOINTS[self.region], loop=self._loop)
        self._loop.run_until_complete(f_ws)
        self._ws = f_ws.result()

        logging.debug('starting heartbeats')
        asyncio.ensure_future(self._send_heartbeats, loop=self._loop)

        logging.debug('starting message queue handler')
        self._queue = asyncio.Queue()
        asyncio.ensure_future(self._queue_handler, loop=self._loop)

    async def __aexit__(self, exc_type, exc, tb):
        await self._ws.close()

    async def _send_heartbeats(self):
        """Send a PING every 2 second to keep the websocket open."""

        try:
            while True:
                await self._ws.send('2')
                await asyncio.sleep(2.)
        except websockets.ConnectionClosed:
            return

    async def _queue_handler(self):
        """Send queued messages to the server."""

        try:
            while True:
                await self._ws.send(await self._queue.get())
        except websockets.ConnectionClosed:
            return

    async def _join(self, userid, username, mode, gameid=None,
            force_start=False):
        #await self._send(['star_and_rank', userid])
        await self._send(['set_username', userid, username])

        if mode == 'private':
            if gameid is None:
                raise ValueError('gameid must be provided for private games')
            await self._send(['join_private', gameid, username, userid])
        else:
            await self._send([_JOIN_MSG[mode], username, userid])

        await self._send(['set_force_start', gameid, userid])

    async def _send(self, data):
        """Send a socket.io event to the socket. This is a coroutine."""

        await self._ws.send('42' + json.dumps(data))

    def _send_nowait(self, data):
        """Send a socket.io event to the socket and return immediately."""

        self._queue.put_nowait('42' + json.dumps(data))

    async def play(self, handler, userid, username, mode, gameid=None):
        try:
            await self._join(userid, username, mode, gameid)
            while True:
                msg = await self._ws.recv()
                # this is just the poor man's socket.io message parser
                # see https://github.com/socketio/socket.io-protocol and
                # https://github.com/socketio/engine.io-protocol

                # here we just ignore every message that is not an engine.io
                # message containing a socket.io event (let's hope the server
                # doesn't asks for fancy ACKS or deconnects)
                if not msg.startswith('42'):
                    continue

                try:
                    data = json.loads(msg[2:])
                except json.JSONDecodeError:
                    logging.warning('malformated json: {}'.format(msg[2:]))
                    continue

                if data[0] == 'game_start':
                    logging.info('game starting')
                    self._process_start(data[1])
                    handler.on_start(self)
                elif data[0] == 'game_update':
                    self._process_update(data[1])
                    handler.on_update(self)
                elif data[0] in ('game_won', 'game_lost'):
                    logging.info('game ended')
                    result = self._process_end(data[0], data[1])
                    handler.on_end(self, result)
                    break
                elif data[0] == 'chat_message':
                    handler.on_message(data[2]['text'], data[2]['playerIndex'])
                elif data[0] in ('queue_update', 'pre_game_start', 'stars',
                        'rank'):
                    pass
                else:
                    logging.warning('unknow event: {}'.format(data))
        except websockets.ConnectionClosed:
            logging.error('websocket closed during game')
        else:
            await self.quit()

    def _process_start(self, data):
        self.player_index = data['playerIndex']
        self.usernames = data[usernames]
        self._replay_id = data['replay_id']
        self._chat_room = data['chat_room']

    def _process_update(self, data):
        #TODO
        pass

    async def quit(self):
        logging.info('exiting game')
        await self._send('leave_game')



def _apply_diff(cache, diff):
    """Apply a diff to an array (in-place)."""

    i = 0
    off = 0
    while i < len(diff) - 1:
        off += diff[i]    # offset increment
        n = diff[i+1]     # length of the replacement
        cache[off:off+n] = diff[i+2:i+2+n]
        off += n
        i += n + 2
    if i == len(diff) - 1:
        del cache[off+diff[i]:]  # length update using last item
        i += 1
    if i != len(diff):
        raise ValueError('malformated diff')
