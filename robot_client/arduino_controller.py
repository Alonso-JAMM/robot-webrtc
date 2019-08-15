import serial
import json
import time
import socketio
import asyncio

URL = 'http://10.0.0.5:8082'
socket_client = socketio.AsyncClient()
loop = asyncio.get_event_loop()


class ArduinoSerial:
    """Class to connect to the arduino """
    def __init__(self, device, baud_rate, timeout=0.05):
        # Opens serial connection
        self.connection = serial.Serial(device, baud_rate)
        # Sleeps a little bit since the arduino restarts after beginning serial connection and we need to
        # wait a little bit in order for it to read data sent
        time.sleep(2)

    def write(self, msg):
        # converts the object msg into a string to be sent
        data = json.dumps(msg)
        if self.connection.isOpen():
            # Send the json message in ascii format
            self.connection.write(data.encode('ascii'))

    def read(self):
        # Reads data from the serial connection
        if self.connection.isOpen():
            # Reads data from the serial port
            data = self.connection.readline()
            return data

    def stop(self):
        # Stops serial communication
        if self.connection.isOpen():
            self.connection.close()


async def run():
    await socket_client.connect(URL)
    await socket_client.wait()


if __name__ == '__main__':
    device = '/dev/ttyACM0'
    baud_rate = 19200
    arduino = ArduinoSerial(device, baud_rate)

    loop.run_until_complete(run())
    # arduino.stop()
