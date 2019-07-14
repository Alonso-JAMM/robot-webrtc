import socketio
import asyncio
import os
import logging
import logging.config
from aiortc import RTCPeerConnection, sdp, VideoStreamTrack, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer


# Root directory of file, useful for sending back mp4 files
ROOT = os.path.dirname(__file__)
# set of peer connections that the client has with other users
peer_connections = set()
# Socketio client that will connect to the server in order to initiate webrtc connections
socket_client = socketio.AsyncClient()
# Socket url
URL = 'http://10.0.0.5:8082'

loop = asyncio.get_event_loop()

options = {
    "framerate": "15",
    "video_size": "320x180"
}


# Class representing each peer connection
class PeerConnection:
    def __init__(self, local_id, remote_id):
        self.local_id = local_id
        self.remote_id = remote_id
        self.pc = RTCPeerConnection()
        # Test if video file exists, if not, then set default green frames
        if os.path.isfile('/dev/video0'):
            self.pc.addTrack(MediaPlayer('/dev/video0', format="v4l2", options=options).video)
        # else:
        self.pc.addTrack(VideoStreamTrack())

    async def answer(self, msg):
        # Setting up the remote session (the caller's information)
        remote_session = RTCSessionDescription(
            sdp=msg['msgData']['sdp'],
            type=msg['msgData']['type']
        )
        await self.pc.setRemoteDescription(remote_session)

        logging.debug('The remote session is: %s', remote_session)
        logging.info('Creating an answer for the call')

        # Setting up the local session (our information)
        local_session = await self.pc.createAnswer()
        await self.pc.setLocalDescription(local_session)

        logging.debug('The local session is: %s', local_session)

        # Data to send back to the caller
        data = {
            "msgType": "answer",
            'targetEasyrtcid': msg['senderEasyrtcid'],
            "msgData": {
                "type": "answer",
                "sdp": self.pc.localDescription.sdp
            }
        }

        logging.debug('Data to send is: %s', data)
        logging.info('Sending data back')

        call_back = self.answer_cb
        await socket_client.emit('easyrtcCmd', data, callback=call_back)

    async def answer_cb(self, msg):
        # This is the callback for the answer call answer
        logging.info('The answer was received by the caller')
        logging.debug('The msg sent back is: %s', msg)
        return 0


@socket_client.event
async def easyrtcCmd(msg):
    """Will listen to easyrtcCmd messages. These messages include:
        offer: this will be the call from other users,
        candidate: this will be the addition of new candidates to the peer connection
        roomData: this will give information about changes in the room information, it will be useful
                  to delete peer connections when other peer disconnects from the call"""

    # Received a new call
    if msg['msgType'] == 'offer':
        remote_id = msg['senderEasyrtcid']
        local_id = msg['easyrtcid']
        logging.info('Received a new call!')
        logging.debug('Now creating new Peer Connection')
        # Creating the peer connection for the call with unique id's of caller and this client
        logging.info('Creating peer connection')
        pc = PeerConnection(local_id, remote_id)
        peer_connections.add(pc)    # Adding peer connection to the set of peer connections
        # Answering the call
        await pc.answer(msg)

    # The caller will send candidates, so we need to add them to the peer connection
    elif msg['msgType'] == 'candidate':
        remote_id = msg['senderEasyrtcid']
        logging.info('Received a new candidate')
        # Some of the candidates may be just be a blank sdp, we don't want them
        if msg['msgData']['candidate'] != "":
            candidate = sdp.candidate_from_sdp(msg['msgData']['candidate'])
            candidate.sdpMid = msg['msgData']['id']
            candidate.sdpMLineIndex = msg['msgData']['label']
            logging.debug('Candidate: %s', candidate)

            for peer in peer_connections:
                if peer.remote_id == remote_id:
                    peer.pc.addIceCandidate(candidate)

    # user left the room, so we need to remove the peer connection. Note that we also receive roomData
    # messages when some joins the room. So it is necessary to now that a user is being removed in order to
    # proceed
    elif msg['msgType'] == 'roomData' and 'removeClient' in msg['msgData']['roomData']['default']['clientListDelta']:
        for peer in peer_connections:
            # The best way to get the remote id
            remote_id = list(msg['msgData']['roomData']['default']['clientListDelta']['removeClient'].
                             values())[0]['easyrtcid']
            if peer.remote_id == remote_id:
                logging.info('Deleting %s from set of peers', peer.local_id)
                await peer.pc.close()
                peer_connections.discard(peer)


@socket_client.event
async def connect():
    """Event called when the user is connected to the server"""
    logging.info('Connected to the socket.io server!')
    await authentication()
    # Now begin the authentication to the server


@socket_client.event
async def move(msg):
    """Movement messages received by the caller to control the bot"""
    print(msg)


async def authentication():
    """Authentication for the server is needed in order to join rooms"""
    msg = {
        "msgType": "authenticate",
        "msgData": {
            "apiVersion": "1.1.1-beta",
            "applicationName": "Client-Line",
            "username": "bot1"
        }
    }
    logging.info('Authenticating')

    call_back = auth_cb
    # Asks the server to authenticate and the server sends back information about the rooms
    await socket_client.emit('easyrtcAuth', msg, callback=call_back)


async def auth_cb(msg):
    # Callback for the authentication function
    logging.info("Now we are authenticated")
    logging.debug("Authentication message: %s", msg)
    await still_alive()
    return 0


async def still_alive():
    # Sending still alive messages to the server in order not to get disconnected
    data = {
        "msgType": "stillAlive"
    }
    call_back = still_alive_cb
    # Sends a still alive message to the server every 20 seconds
    while True:
        await socket_client.emit("easyrtcCmd", data, callback=call_back)
        await asyncio.sleep(20)


async def still_alive_cb(msg):
    # Callback called every time the server receives the still alive message
    logging.info("still alive")
    logging.debug("returned message: %s", msg)
    return 0


async def run():
    await socket_client.connect(URL)

    await socket_client.wait()


if __name__ == '__main__':
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
    })
    logging.basicConfig(level=logging.DEBUG)
    loop.run_until_complete(run())
