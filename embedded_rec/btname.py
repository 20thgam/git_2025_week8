import time
import serial

# ==========
# parameters
# ==========
devicename = "raspi01"
pinnumber = "123456"



bleSerial = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1.0)

def readAll(serial):
    time.sleep(2.0)
    while serial.in_waiting:
        print(bleSerial.readline().decode('utf-8'), end='')

try:
    print("# Check connection")
    bleSerial.write( b"AT\r\n" )
    readAll(bleSerial)
    print()

    print("# Reset")
    bleSerial.write( b"AT+RESET\r\n" )
    readAll(bleSerial)
    print()

    print("# Check connection")
    bleSerial.write( b"AT\r\n" )
    readAll(bleSerial)
    print()

    print("# Check device address")
    bleSerial.write( b"AT+LADDR\r\n" )
    readAll(bleSerial)
    print()

    print("# Set device name")
    bleSerial.write( ("AT+NAME%s\r\n" % devicename).encode() )
    readAll(bleSerial)
    print()

    print("# Check device name")
    bleSerial.write( b"AT+NAME\r\n" )
    readAll(bleSerial)
    print()

    print("# Set pin number")
    bleSerial.write( ("AT+PIN%s\r\n" % pinnumber).encode() )
    readAll(bleSerial)
    print()

    print("# Check pin number")
    bleSerial.write( b"AT+PIN\r\n" )
    readAll(bleSerial)
    print()
        
except KeyboardInterrupt:
    pass

bleSerial.close()