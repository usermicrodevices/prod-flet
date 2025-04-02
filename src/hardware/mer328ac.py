'tested with scales "M-ER 328AC(PX) - Touch-M"'

STX = b'\x02'
ENQ = b'\x05'
ACK = b'\x06'
NAK = b'\x15'

import logging, sys, threading, time
try:
    import serial
except Exception as e:
    logging.error(e)
    serial = None


class pos2m:

    READ_SIZE = 15
    W0 = b'\x17\x00'#stable zero
    W1 = b'\x04\x00'#stable weight
    STATES = {W0:'STABLE-ZERO', W1:'STABLE-WEIGHT'}
    CMD_3A = b'\x3A'#state command
    PASSWORD = b'\x30\x30\x33\x30'
    REQUEST_STATE = CMD_3A + PASSWORD

    data = {'weight':0.0, 'state':'UNKNOWN', 'error':b'\x00'}
    device = None
    infinity_thread = None

    def __init__(self, *args, **kwargs):
        self.weight_ratio = kwargs.pop('weight_ratio', 0)
        self.delay_requests = kwargs.pop('delay_requests', 2)
        self.delay_reopen_device = kwargs.pop('delay_reopen_device', 5)
        start_infinity_read = kwargs.pop('start_infinity_read', False)
        self.serial_args = args
        self.serial_kwargs = kwargs
        if self.open_device():
            self.init_protocol()
            if start_infinity_read:
                self.run_infinity_read()

    def __del__(self):
        self.close()

    def close(self):
        if self.device and self.device.is_open:
            self.device.close()
            self.device = None
        if self.infinity_thread and self.infinity_thread.is_alive():
            try:
                self.infinity_thread.join(self.delay_requests + self.delay_reopen_device + 1)
            except Exception as e:
                logging.error(e)

    def open_device(self):
        if serial is None:
            return False
        try:
            self.device = serial.Serial(*self.serial_args, **self.serial_kwargs)
        except Exception as e:
            logging.warning(e)
            try:
                self.device = serial.Serial('/dev/ttyUSB0', 9600, timeout=1, exclusive=True)
            except Exception as e:
                logging.warning(e)
                try:
                    self.device = serial.Serial('/dev/ttyS0', 9600, timeout=1, exclusive=True)
                except Exception as e:
                    logging.error(e)
        return self.device and self.device.is_open

    def blen(self, data):
        return bytes([len(data)])

    def lrc(self, data):
        res = 0
        for b in data:
            res ^= b
        return bytes([res])

    def init_protocol(self):
        request_state_prep = self.blen(self.REQUEST_STATE) + self.REQUEST_STATE
        self.cmd_request_state = STX + request_state_prep + self.lrc(request_state_prep)
        #logging.debug(['self.cmd_request_state', tuple(hex(b) for b in self.cmd_request_state)])

    def read_weight_raw(self):
        data = b''
        if self.device and self.device.is_open:
            try:
                self.device.write(self.cmd_request_state)
            except KeyboardInterrupt:
                sys.exit(' KeyboardInterrupt')
            except Exception as e:
                logging.error(e)
            else:
                if self.device and self.device.is_open:
                    try:
                        data = self.device.read(self.READ_SIZE)
                    except KeyboardInterrupt:
                        sys.exit(' KeyboardInterrupt')
                    except Exception as e:
                        logging.error(e)
                    else:
                        if self.device and self.device.is_open:
                            try:
                                self.device.write(ACK)
                            except KeyboardInterrupt:
                                sys.exit(' KeyboardInterrupt')
                            except Exception as e:
                                logging.error(e)
        return data

    def get_weight(self):
        data = self.data.copy()
        data_raw = self.read_weight_raw()
        if len(data_raw) == self.READ_SIZE:
            data['error'] = bytes([data_raw[4]])
            if data['error'] != b'\x00':
                logging.error(['ERROR-CODE', data['error']])
            data['state'] = self.STATES.get(data_raw[5:7], 'UNKNOWN')
            data['weight'] = int.from_bytes(data_raw[7:11], 'little')
            if self.weight_ratio:
                data['weight'] /= self.weight_ratio
        return data

    def run_infinity_read(self):
        self.infinity_thread = threading.Thread(target=self.infinity_read, daemon=True)
        self.infinity_thread.start()

    def infinity_read(self):
        self.data = self.get_weight()
        while self.device:
            try:
                time.sleep(self.delay_requests)
            except KeyboardInterrupt:
                sys.exit(' KeyboardInterrupt')
            except Exception as e:
                logging.error(e)
            else:
                self.data = self.get_weight()
            if self.device and not self.device.is_open:
                while self.device and not self.open_device():
                    try:
                        time.sleep(self.delay_reopen_device)
                    except KeyboardInterrupt:
                        sys.exit(' KeyboardInterrupt')
                    except Exception as e:
                        logging.error(e)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    #protocol = pos2m('/dev/ttyS0', 9600, delay_requests=.1, delay_reopen_device=10)
    #protocol = pos2m('/dev/ttyUSB0', 9600, delay_requests=.1, start_infinity_read=True)
    protocol = pos2m('/dev/ttyUSB0', 9600, timeout=.5, delay_requests=.1, weight_ratio=1000)
    if protocol:
        one_read_weight = protocol.get_weight()
        logging.debug('ONE_READ_WEIGHT')
        logging.debug(one_read_weight)
        protocol.run_infinity_read()
        logging.debug('RUN_INFINITY_READ')
        w = protocol.data
        logging.debug(w)
        while True:
            if w != protocol.data:
                w = protocol.data
                logging.debug(w)
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                sys.exit(' KeyboardInterrupt')
            except Exception as e:
                logging.error(e)
