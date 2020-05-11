import serial
import json
import time


class ArduinoSerial:
    """Class to connect to the arduino """
    def __init__(self, device, baud_rate, timeout=0.015):
        # Opens serial connection
        self.connection = serial.Serial(device, baud_rate, timeout=timeout)
        # Sleeps a little bit since the arduino restarts after beginning serial connection and we need to
        # wait a little bit in order for it to read data sent
        
        time.sleep(2)

    def write(self, msg):
        # converts the object msg into a string to be sent
        #TODO may need to change from json to another format since Data channels will be used
        #data = json.dumps(msg)
        if self.connection.isOpen():
            # Send the json message in ascii format
            self.connection.write(msg.encode('ascii'))

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


if __name__ == '__main__':
    device = '/dev/ttyACM0'
    baud_rate = 38400
    arduino = ArduinoSerial(device, baud_rate)
    arduino.write("<M 255 255>")
    a = arduino.read()
    print(a)
    arduino.stop()
