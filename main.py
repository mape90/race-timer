
import utime, network, ntptime, socket, urequests
from machine import Pin, RTC


# Global variables
g_master_ssid = ""
g_master_pass = ""

g_dissabled_time_ms = 1000
g_server_ip = "192.168.1.1"

g_own_id = 1
g_sleep_time = 0.01 # 10ms

g_sensor_1_pin = 13
g_sensor_2_pin = 12

g_sensor1 = Sensor(g_sensor_1_pin, 1)
g_sensor2 = Sensor(g_sensor_2_pin, 2)
# End of global variables

def sensor_event(pin):
    ''' Handles sensor events
    Input:
        Machine.Pin: pin who created the event
    '''
	if str(pin) == "Pin({})".format(g_sensor_1_pin):
		g_sensor1.event()
	if str(pin) == "Pin({})".format(g_sensor_2_pin):
		g_sensor2.event()

def handle_sensors():
	'''Find if sensors have unhandled events
	and send them to master
	'''
	if g_sensor1.get_event() != 0:
		if send_event_to_master(g_sensor1):
			g_sensor1.clear_event()
	if g_sensor2.get_event() != 0:
		if send_event_to_master(g_sensor2):
			g_sensor2.clear_event()

class Sensor:
    def __init__(self, pin_num, id, dissabled_ms=g_dissabled_time_ms):
        self.pin = Pin(pin_num Pin.IN)
        self.pin.irq(trigger=Pin.IRQ_FALLING, handler=sensor_event)
        self.last_event = 0
		self.event_cleared = True
        self.id = id
        self.dissabled_ms = dissabled_ms

    def get_pin(self):
        return self.pin

	def event(self):
        now = now_ms()
        if self.event_cleared and not self.is_dissabled():
			self.event_cleared = False
            self.last_event = now

	def get_event(self):
        return self.last_event

	def clear_event(self):
        self.event_cleared = True

	def is_dissabled(self):
    	return (now_ms()-self.last_event) < self.dissabled_ms


def now_ms():
    ''' Returns ms from 1.1.2000
    '''
    ms = int(RTC().datetime()[7]/1000)
    ms += utime.time()*1000
    return ms

def send_event_to_master(event):
    '''Send event in json format to master
    format: {id: <int>, sensor: <int>, time_ms: <int>}
    returns: bool if got 200
    '''
    try:
        data = "{{id: {}, sensor: {}, time_ms: {}}}"
        data.format(g_own_id, sensor.id, sensor.get_event())
        response = urequests.post("http://"+g_server_ip+ "/event", data = data)
        response.close()
        return response.status_code == 200
    except Exception as e:
        print(e)
        return False

def send_alive_to_master():
    '''Send alive message to master
    format: {id: <int>}
    return: bool if got 200
    '''
    try:
        data = "{{id: {}}}"
        data.format(g_own_id)
        response = urequests.post("http://"+g_server_ip+ "/alive", data = data)
        response.close()
        return response.status_code == 200
    except Exception as e:
        print(e)
        return False

class RaceTimer:
    '''
    1) Init network (connect to master)
    2) sync time
    3) Init pins
    4) Init triggers
    5) wait pin events

    Event:
    get event (new object)
    -> timer until next event can be recieved.
    -> send message (tcp) to server

    Alive message:
    every 5sec send alive message
    '''
    def __init__(self):
        self.wlan = None
        self.network_online=False
        self.network_init()
        self.last_alive = now_ms()

    def send_alive(self):
        if ( now_ms() - self.last_alive ) > g_alive_interval_ms:
            if send_alive_to_master():
                self.last_alive = now_ms()

    def network_init(self):
        if not self.network_online:
            try:
                self.wlan = network.WLAN(network.STA_IF)
                self.wlan.active(True)
                self.wlan.connect(g_master_ssid, g_master_pass)
                self.network_online=True
                print('network config:', sta_if.ifconfig())
                ntptime.settime()
            except Exception as e:
                print(e)
        else:
            if not self.wlan.isconnected():
                try:
                    self.wlan.active(False)
                    self.wlan.active(True)
                    self.wlan.connect(g_master_ssid, g_master_pass)
                    ntptime.settime()
                except Exception as e:
                    print(e)

    def run(self):
        while True:
            self.network_init()
            handle_sensors()
            self.send_alive()
            utime.sleep(g_sleep_time)

def main():
    create_sensors()
    rt = RaceTimer()
    rt.run()

main()
