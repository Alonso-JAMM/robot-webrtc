# USIN CODE FROM AIORTC EXAMPLES https://github.com/aiortc/aiortc/blob/master/examples/janus/janus.py
import logging
import asyncio
import random
import aiohttp
import string
import time
import os
import json


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
            # Text room does not return "ack" when joined
            #assert data["janus"] == "ack"
            
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


class TextClient:
    def __init__(self, session, room):
        self.session = session
        self.room = room    # Janus room to connect
        self.plugin = None
        self.channel = None
        
    async def create(self):
        """
        Connects to the text room
        """
        await self.session.create()
        self.plugin = await session.attach("janus.plugin.textroom")
        
        pc = RTCPeerConnection()
        pcs.add(pc)
        
        self.channel = pc.createDataChannel("JanusDataChannel")
        self.channel.on("open", self.join_room)
        self.channel.on("message", self.reader)
        
        # Initializing Peer Connection
        request = {"request": "setup"}
        response = await self.plugin.send(
            {
                "body": request,
            }
        )
        await pc.setRemoteDescription(
            RTCSessionDescription(
                sdp=response["jsep"]["sdp"], type=response["jsep"]["type"]
            )
        )
        await pc.setLocalDescription(await pc.createAnswer())
        answer = {"request": "ack"}
        await self.plugin.send(
            {
                "body": answer,
                "jsep":{
                    "sdp": pc.localDescription.sdp,
                    "trickle": False,
                    "type": pc.localDescription.type,
                },
            }
        )

    
    def join_room(self):
        """
        First message sent to the room using Data Channel. This is the part 
        that interfaces with the Arduino
        """
        data = {
            "textroom": "join",
            "transaction": transaction_id(),
            "room": self.room,
            "username": transaction_id(),
            "display": "bot1"
        }
        self.channel.send(json.dumps(data))
    
    def reader(self, data):
        """
        Reads mesages posted on the data channel
        """
        print(data)
        


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
    
    text_room = TextClient(session, room)
    
    
    loop = asyncio.get_event_loop()
    try:
        # Now we can publish for ever
        loop.run_until_complete(
            camera_stream(session=session, room=room, camera_options=camera_options)
        )
        loop.run_until_complete(
            text_room.create()
        )
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # close peer connections
        loop.run_until_complete(session.destroy())
        coros = [pc.close() for pc in pcs]
        loop.run_until_complete(asyncio.gather(*coros))
