#!/usr/bin/env python

# --------------------------------------------------------------------------- #
# I M P O R T S
# --------------------------------------------------------------------------- #
from pymodbus.server.sync import ModbusTcpServer
from pymodbus.framer.socket_framer import ModbusSocketFramer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
import logging


# --------------------------------------------------------------------------- #
# Modbus TCP Server/Slave Class
#
# TODO: Implement conversion of hr-register value to 16bit & split into bits
# --------------------------------------------------------------------------- #
class ModbusSlaveUnit():

    def __init__(self):
        self._slave_id   = 0x02
        self._start_addr = 0x00
        self._end_addr   = 0x7c
        self._data       = [0]
        self._init_modbus_slave()

    def _init_modbus_slave(self):
        self._slaves  = { self._slave_id : ModbusSlaveContext(di=None, co=None, ir=None, hr=ModbusSequentialDataBlock(self._start_addr, self._data*self._end_addr)) }
        self._context = ModbusServerContext( slaves=self._slaves, single=False )

    def start_modbus_slave(self, host, port, custom_functions=[], **kwargs):
        print('Starting Modbus TCP server at IP: %s on PORT: %s' %(host, port))
        self._identity = None
        self._address  = (host, port)
        self._framer   = kwargs.pop("framer", ModbusSocketFramer)
        self._server   = ModbusTcpServer(self._context, self._framer, self._identity, self._address, **kwargs)

        for f in custom_functions:
            self._server.decoder.register(f)
        self._server.serve_forever()

    def close_modbus_slave(self):
        self._server.server_close()

    def _get_register_bitsself(self, data):
        '''
        Fetch individual bits of register by converting 
        data into string based 16bit value.
        Returns bits in a list format.
        '''
        bits = '{0:016b}'.format(data)
        bits = list(bits)
        return bits


# --------------------------------------------------------------------------- #
# M A I N   R E G I O N
# --------------------------------------------------------------------------- #
if __name__ == "__main__":

    HOST = '192.168.127.7'
    PORT = 502

    sp_1 = ModbusSlaveUnit()
    sp_1.start_modbus_slave(HOST, PORT)
