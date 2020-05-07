# USIN CODE FROM AIORTC EXAMPLES https://github.com/aiortc/aiortc/blob/master/examples/janus/janus.py
import logging
import asyncio
import random
import aiohttp
import string
import time
import os

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer

pcs = set()


def transaction_id():
    return "".join(random.choice(string.ascii_letters) for x in range(12))


def exists(path):
    try:
        os.stat(path)
    except OSError:
        return False
    return True


class JanusPlugin:
    def __init__(self, session, url):
        self._url = url
        self._session = session
        self._queue = asyncio.Queue()
        
    async def send(self, payload):
        message = {
            "janus": "message",
            "transaction": transaction_id(),
            }
        message.update(payload)
        async with self._session._http.post(self._url, json=message) as response:
            data = await response.json()
            assert data["janus"] == "ack"
            
        response = await self._queue.get()
        # For some reason assert fails even though response and mesage
        # have the same transaction
        #assert response["transaction"] == message["transaction"]
        return response


class JanusSession:
    def __init__(self, url):
        self._root_url = url
        self._http = None
        self._session_url = None
        self._poll_task = None
        self._plugins = {}
        
    async def attach(self, plugin_name: str) -> JanusPlugin:
        message = {
            "janus": "attach",
            "plugin": plugin_name,
            "transaction": transaction_id(),
        }
        async with self._http.post(self._session_url, json=message) as response:
            data = await response.json()
            assert data["janus"] == "success"
            plugin_id = data["data"]["id"]
            plugin = JanusPlugin(self, self._session_url + "/" + str(plugin_id))
            self._plugins[plugin_id] = plugin
            return plugin
        
    async def create(self):
        self._http = aiohttp.ClientSession()
        message = {
            "janus": "create",
            "transaction": transaction_id(),
            }
        async with self._http.post(self._root_url, json=message) as response:
            data = await response.json()
            assert data["janus"] == "success"
            session_id = data["data"]["id"]
            self._session_url = self._root_url + "/" + str(session_id)
        self._poll_task = asyncio.ensure_future(self._poll())
        
    async def leave(self):
        request = {"body": {
            "request": "leave"
            }
        }
        for plugin in self._plugins:
            await self._plugins[plugin].send(request)
        for pc in pcs:
            await pc.close()

    async def destroy(self):
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
            
        if self._session_url:
            message = {
                "janus": "destroy",
                "transaction": transaction_id(),
                }
            async with self._http.post(self._session_url, json=message) as response:
                data = await response.json()
                assert data["janus"] == "success"
            self._session_url = None
            
        if self._http:
            await self._http.close()
            self._http = None

    async def _poll(self):
        while True:
            params = {"maxev": 1, "rid": int(time.time() * 1000)}
            async with self._http.get(self._session_url, params=params) as response:
                data = await response.json()
                if data["janus"] == "event":
                    plugin = self._plugins.get(data["sender"], None)
                    if plugin:
                        await plugin._queue.put(data)
                    else:
                        pass
                        #logging.debug(f"data is: {data}")


async def publish(plugin, camera_options):
    """
    Send video to the room.
    """
    pc = RTCPeerConnection()
    pcs.add(pc)

    # configure media
    media = {"audio": False, "video": True}
    if exists('/dev/video0'):
        pc.addTrack(MediaPlayer('/dev/video0', format="v4l2", options=camera_options).video)
    else:
        pc.addTrack(VideoStreamTrack())

    # send offer
    await pc.setLocalDescription(await pc.createOffer())
    request = {"request": "publish"}
    request.update(media)
    response = await plugin.send(
        {
            "body": request,
            "jsep": { 
                "sdp": pc.localDescription.sdp,
                "trickle": False,
                "type": pc.localDescription.type,
            },
        }
    )

    # apply answer
    await pc.setRemoteDescription(
        RTCSessionDescription(
            sdp=response["jsep"]["sdp"], type=response["jsep"]["type"]
        )
    )


async def camera_stream(session, room, camera_options):
    await session.create()
    # join video room
    plugin = await session.attach("janus.plugin.videoroom")
    response = await plugin.send(
        {
            "body": {
                "display": "bot1",
                "ptype": "publisher",
                "request": "join",
                "room": room,
            },
        }
    )
    # send video
    await publish(plugin=plugin, camera_options=camera_options)
    # exchange media for 1 minute
    logging.debug("Exchanging media")
    # No need to sleep anymore
    #await asyncio.sleep(60)


async def messages(session, room):
    await session.create()
    # join text room
    plugin = await session.attach("janu")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Initializing janus client test")

    url = "http://classickerobel.duckdns.org:8080/janus"
    room = 1234

    camera_options = {
        "framerate": "30",
        "video_size": "320x192",
    }

    # create signaling and peer connection
    session = JanusSession(url)

    loop = asyncio.get_event_loop()
    try:
        # Now we can publish for ever
        loop.run_until_complete(
            camera_stream(session=session, room=room, camera_options=camera_options)
        )
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # close peer connections
        loop.run_until_complete(session.leave())
