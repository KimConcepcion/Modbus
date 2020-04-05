#!/usr/bin/env python

# --------------------------------------------------------------------------- #
# I M P O R T S
# --------------------------------------------------------------------------- #
from pymodbus.server.sync import StartTcpServer
# from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.framer.socket_framer import ModbusSocketFramer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
import threading
import time

# --------------------------------------------------------------------------- #
# Custom datablock with thread:
# --------------------------------------------------------------------------- #
class DataBlock(ModbusSequentialDataBlock):

    def __init__(self):
        self.address    = 0
        self.end_addr   = 124
        self.values     = [0]*self.end_addr

    def get_data(self):
        # self.lock.acquire()
        modbus_data = self.values.copy()
        print(modbus_data)
        # self.lock.release()


# --------------------------------------------------------------------------- #
# Modbus TCP Server/Slave Class
# --------------------------------------------------------------------------- #
class ModbusServer():

    def __init__(self):
        self._slave_id   = 0x02
        self._block      = DataBlock()
        self._init_modbus_slave()

    def _init_modbus_slave(self):
        self._slaves  = { self._slave_id : ModbusSlaveContext(di=None, co=None, ir=None, hr=self._block) }
        self._context = ModbusServerContext( slaves=self._slaves, single=False )

    def start_modbus_server(self, host, port, **kwargs):
        print('Starting Modbus TCP server at IP: %s on PORT: %s' %(host, port))
        self._identity = None
        self._address  = (host, port)
        self.server = threading.Thread( target=StartTcpServer, args=(self._context, self._identity, self._address) )
        self.server.start()

    def update(self):
        self._slaves[self._slave_id].store['h'].get_data()

# --------------------------------------------------------------------------- #
# T E S T   R E G I O N
# --------------------------------------------------------------------------- #
if __name__ == "__main__":

    HOST = '192.168.127.7'
    PORT = 502

    sp_1 = ModbusServer()
    sp_1.start_modbus_server(HOST, PORT)

    # Cyclic scan simulator:
    while True:
        sp_1.update()
        time.sleep(2)
