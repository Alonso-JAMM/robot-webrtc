import socketio
import asyncio
import logging
import json
from aiortc import sdp
from robot_client.peer_connection import peer_connections
from robot_client.peer_connection import PeerConnection

# child logger
log = logging.getLogger("main.easy")


class ClientNameSpace(socketio.AsyncClientNamespace):
    """ This class has all the socketio events for the client. """
    def __init__(self, name="bot1", arduino=None):
        super().__init__()
        # pc (Peer Connection) is an object passed to the classs in order to make
        # Note that pc is not required since in some cases it is only needed to be in the room
        self.pc = None
        self.name = name
        self.arduino = arduino              # Arduino object that will be used to read and write to it

    async def on_connect(self):
        log.info("Connected to the server!")
        # Once connected to the server, we ask it to be authenticated
        # This is the message that the server is expecting
        msg = {
            "msgType": "authenticate",
            "msgData": {
                "apiVersion": "1.1.1-beta",
                "applicationName": "Client-Line",
                "username": f"{self.name}"
            }
        }
        call_back = self.auth_callback
        # Asks the server to authenticate and the server sends back information about the rooms available
        await self.emit("easyrtcAuth", msg, callback=call_back)

    async def on_easyrtcCmd(self, msg):
        """Will listen to easyrtcCmd messages. These messages include:
            offer: this will be the call from other users,
            candidate: this will be the addition of new candidates to the peer connection
            roomData: this will give information about changes in the room information, it will be useful
                      to delete peer connections when other peer disconnects from the call
            offer and candidate are used by peer connection. If it is only required to see the socketio
            messages, just roomData is required"""
        # Received a new call
        if msg["msgType"] == "offer" and self.name is not "listener":
            remote_id = msg["senderEasyrtcid"]
            local_id = msg["easyrtcid"]
            log.info("Received a new call!")
            log.debug("Initiating a new Peer Connection")
            # Creating the peer connection for the call with unique id's of caller and this client
            self.pc = PeerConnection(local_id, remote_id)
            peer_connections.add(self.pc)
            # Returns the answer from the offer
            answer = await self.pc.answer(msg)
            call_back = self.answer_cb
            await self.emit("easyrtcCmd", answer, callback=call_back)
            # The caller will send candidates, so we need to add them to the peer connection
        elif msg["msgType"] == "candidate" and self.name is not "listener":
            remote_id = msg["senderEasyrtcid"]
            log.info("Received a new candidate")
            # Some of the candidates may be just be a blank sdp, we don't want them
            if msg["msgData"]["candidate"] != "":
                candidate = sdp.candidate_from_sdp(msg["msgData"]["candidate"])
                candidate.sdpMid = msg["msgData"]["id"]
                candidate.sdpMLineIndex = msg["msgData"]["label"]
                log.debug(f"Candidate: {candidate}")
                for peer in peer_connections:
                    if peer.remote_id == remote_id:
                        peer.pc.addIceCandidate(candidate)
        # user left the room, so we need to remove the peer connection. Note that we also receive roomData
        # messages when some joins the room. So it is necessary to now that a user is being removed in order to
        # proceed
        elif msg["msgType"] == "roomData" and "removeClient" in msg["msgData"]["roomData"]["default"][
                    "clientListDelta"] and self.name is not "listener":
            for peer in peer_connections:
                # The best way to get the remote id
                remote_id = list(msg["msgData"]["roomData"]["default"]["clientListDelta"]["removeClient"].
                                 values())[0]["easyrtcid"]
                if peer.remote_id == remote_id:
                    log.debug(f"Deleting {peer.local_id} from set of peers")
                    await peer.pc.close()
                    peer_connections.discard(peer)

    async def on_message(self, msg):
        """Data received that includes movement and other actions for the bot"""
        if self.name == "listener":
            print(msg)

    async def on_move(self, msg):
        if self.name == "listener":
            data_json = """{ 
                   "M": [
                       "255",
                       "255"
                       ],
                   "L1": [
                       "255"
                       ],
                   "L2": [
                       "0"
                       ]
                   }"""
            msg = json.loads(data_json)
            for command in msg:
                data = "<" + command
                for parameter in msg[command]:
                    data = data + " " + parameter
                data = data + ">"
                self.arduino.write(data)
                self.arduino.read()
                self.arduino.write(data)
                self.arduino.read()

    async def auth_callback(self, msg):
        # Callback function for the authentication process
        log.debug(f"Authentication message: {msg}")
        # Begins still alive messages that tell the server not to drop the connection
        await self.still_alive()
        return 0

    async def still_alive(self):
        # Sending still alive messages in order to not have the connection dropped
        data = {
            "msgType": "stillAlive"
        }
        call_back = self.still_alive_cb
        # Sending still alive message to the server every 20 seconds
        while True:
            await self.emit("easyrtcCmd", data, callback=call_back)
            await asyncio.sleep(20)

    async def still_alive_cb(self, msg):
        # Callback used by the still alive command, it should return "ack"
        log.debug(f"still alive, message returned: {msg}")
        return 0

    async def answer_cb(self, msg):
        # Callback used when emitting an answer, it is similar to still_alive_cb
        log.info("The answer was received by the caller")
        log.debug(f"The message sent back is: {msg}")
        return 0


class SocketClient:
    """ This class initializes the socketio client with namespaces and connects it to the server """
    def __init__(self, namespace=None):
        self.client = socketio.AsyncClient()
        if namespace is None:
            self.client.register_namespace(ClientNameSpace())
        else:
            self.client.register_namespace(namespace)

    async def connect(self, url):
        # Begins connection to the socketio server
        await self.client.connect(url)
        await self.client.wait()

    async def disconnect(self):
        # Disconnects from the server
        await self.client.disconnect()
