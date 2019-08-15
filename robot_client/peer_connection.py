from robot_client import config
import os
import logging
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription, RTCRtpSender
from aiortc.contrib.media import MediaPlayer


logger = logging.getLogger('client.PC')

# Set of peer connections that the client has with other users
peer_connections = set()


class PeerConnection:
    def __init__(self, local_id, remote_id):
        self.local_id = local_id
        self.remote_id = remote_id
        self.pc = RTCPeerConnection()
        # Test if video file exists, if not, then set default green frames
        if exists(config.devices["camera"]):
            self.pc.addTrack(MediaPlayer(config.devices["camera"], format="v4l2", options=config.video_options).video)
        else:
            self.pc.addTrack(VideoStreamTrack())

    async def answer(self, msg):
        # Setting up the remote session (the caller's information)
        remote_session = RTCSessionDescription(
            sdp=msg['msgData']['sdp'],
            type=msg['msgData']['type']
        )
        await self.pc.setRemoteDescription(remote_session)
        # Setting up the local session (our information)
        local_session = await self.pc.createAnswer()
        await self.pc.setLocalDescription(local_session)
        # Data to send back to the caller
        data = {
            "msgType": "answer",
            'targetEasyrtcid': msg['senderEasyrtcid'],
            "msgData": {
                "type": "answer",
                "sdp": self.pc.localDescription.sdp
            }
        }
        return data


def exists(path):
    try:
        os.stat(path)
    except OSError:
        return False
    return True
