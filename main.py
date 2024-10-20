import machine
import network
import time
import creds
import socket
import struct
import requests

#GPIO number not the number for the pin on the board
#PULL_DOWN means when off, it is 0, when on it is 1
boardLED = machine.Pin('LED', machine.Pin.OUT)
waterPin = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_DOWN) #blue wire
servo = machine.PWM(machine.Pin(14)) #green wire
ntpDelta = 2209010400 #adjustment to get to MDT
servoUp = 1750
servoDown = int(servoUp*3.3)
frequency = 50
servo.freq(frequency)
timeHost = "pool.ntp.org"
wlan = network.WLAN(network.STA_IF)
coffeeTimes = [(8, 15), (8, 15), (6, 5), (8, 15), (8, 15), (8, 15), (8, 15)]

def connectInternet():
    wlan.active(True)
    wlan.connect(creds.SSID, creds.WIFI_PASSWORD)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status()>=3:
            break
        max_wait -= 1
        print("waiting for connection...")
        time.sleep(1)

    if wlan.status() != 3:
        #raise RuntimeError("network connection failed")
        print("cannot connect to internet")
    else:
        print("connected")
        sendEmail("Connected to Wifi")

def setTime():
    ntpQuery = bytearray(48)
    ntpQuery[0] = 0x1B
    addr = socket.getaddrinfo(timeHost, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(ntpQuery, addr)
        msg = s.recv(48)
    finally:
        s.close()
    val = struct.unpack("!I", msg[40:44])[0]
    t = val - ntpDelta
    tm = time.gmtime(t)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

def sendEmail(message):
    headers = {
    'Content-Type': 'application/json',
    }

    json_data = {
        'Messages': [
            {
                'From': {
                    'Email': creds.SENDING_EMAIL,
                    'Name': 'Coffee Machine',
                },
                'To': [
                    {
                        'Email': creds.MY_EMAIL,
                        'Name': 'Me',
                    },
                ],
                'Subject': message,
                'TextPart': message,
            },
        ],
    }

    print("attempting to send Email")

    r = requests.post(
        'https://api.mailjet.com/v3.1/send',
        headers=headers,
        json=json_data,
        auth=(creds.API_KEY, creds.API_SECRET),)
    if r.status_code >= 300 or r.status_code < 200:
        print("There was an error with the request to send a message. \n" +
              "Response Status: " + str(r.status_code))
    else:
        print("Success")
        print(r.status_code)
    r.close()    

connectInternet()
setTime()

while True:
    if wlan.status() != 3:
        connectInternet()      
        setTime()
    currentTime = time.localtime()[3:5] #get just hour and minutes
    
    #check day at 1am every day to determine which coffee time to do
    if currentTime == (1, 0):
        currentDay = time.localtime()[6] #day is 0-6 for monday-sunday
        coffeeTime = coffeeTimes[currentDay]
        
    if currentTime == coffeeTime:
        if waterPin.value():
            servo.duty_u16(servoDown)
            time.sleep(.5)
            servo.duty_u16(servoUp)
            print("coffee has started")
            sendEmail("Coffee has started")
        else:
            print("no water")
            sendEmail("No water in machine")
        time.sleep(3600) #wait an hour so it doesn't spam the button