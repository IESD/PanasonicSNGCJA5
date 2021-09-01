import logging
import smbus

# Parameters for each data address in the format Label : (Start address, data length in bytes)
DENSITY_ADDRESSES = {
    "PM1.0": (0x00, 4),
    "PM2.5": (0x04, 4),
    "PM10": (0x08, 4)
}

DENSITY_DIVISOR = 1000

COUNTS_ADDRESSES = {
    "PM0.5": (0x0c, 2),
    "PM1.0": (0x0e, 2),
    "PM2.5": (0x10, 2),
    "PM5": (0x14, 2),
    "PM7.5": (0x16, 2),
    "PM10": (0x18, 2)
}

STATUS_MASTER = "Sensor status"
STATUS_BIT_MASK = 0b11
STATUS_BYTE_FIELDS = {"Sensor status": 6, "PD Status": 4, "LD Status": 2, "Fan status": 0}
STATUS_ADDRESS = {
    "Sensor_Status": (0x26, 1)
}

COLLECTION_ADDRESSES = {
    "Densities": (0x00, 12),
    "Counts": (0x0c, 14),
    "All_data": (0x00, 26)
}

'''
Address register of mass density values is started from 0 (0x00) to 11 (0x0B).
Size of each value block is 4 bytes (32 bits) 
Total data length is 12 bytes

Value allocation
------------------------
PM1.0: byte 0 - byte 3 
PM2.5: byte 4 - byte 7
PM10: byte 8 - byte 11
'''

'''
Address register of particle count values is started from 12 (0x0C) to 25 (0x19)
Size of each value block is 2 bytes (16 bits)
Total data length is 14 bytes (or 12 bytes excluding byte 18 and 19)

Value allocation
------------------------
PM0.5: byte 12 - byte 13
PM1.0: byte 14 - byte 15
PM2.5: byte 16 - byte 17
N/A: byte 18 - byte 19
PM5.0: byte 20 - byte 21
PM7.5: byte 22 - byte 23
PM10: byte 24 - byte 25
'''


class SNGCJA5:

    def __init__(self, i2c_bus_no: int, logger: str = None):
        self.logger = None
        if logger:
            self.logger = logging.getLogger(logger)
        self.i2c_address = 0x33
        try:
            self.i2c_bus = smbus.SMBus(i2c_bus_no)
        except OSError as e:
            if self.logger:
                self.logger.error(f"OSError on getting i2c_bus : {e}")
            else:
                print("OSError")
                print(e)

        self.__current_status = {STATUS_MASTER: 0}

    def get_status(self):
        status = self.__read_data(STATUS_ADDRESS)
        return status[0]

    def get_mass_density_data(self) -> dict:
        return self.get_data_collection(DENSITY_ADDRESSES, DENSITY_DIVISOR)

    def get_particle_count_data(self) -> dict:
        return self.get_data_collection(COUNTS_ADDRESSES)

    def get_data_collection(self, addresses: dict, divisor=1):
        return_dict = {}
        for key in addresses:
            data = self.__read_data(*addresses[key])
            if data:
                val = 0
                for i in range(addresses[key][1]):
                    val = (data[i] << (8 * i) | val)

                # Error has been noted where on certain reads all 1 bits are returned, this is a data error
                if val == 2 ** addresses[key][1] - 1:
                    self.logger.warning(f"Suspect erroneous value {key} : {val} - resetting to 0")
                    val = 0
                return_dict[key] = val / divisor

        return return_dict

    def __read_data(self, start, length):
        status = self.get_status()
        if status == 0:
            try:
                return self.i2c_bus.read_i2c_block_data(self.i2c_address, start, length)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"{type(e).__name__}: {e}")
                else:
                    print(f"{type(e).__name__}: {e}")
        if self.logger:
            self.logger.warning(f"Non-zero SNGCJA5 status returned : {status}")
        return None
