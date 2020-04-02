# --------------------------------------------------------------------------- #
# I M P O R T S
# --------------------------------------------------------------------------- #
from binascii import b2a_hex
from pymodbus.compat import socketserver, byte2int
from pymodbus.exceptions import NoSuchSlaveException
from pymodbus.pdu import ModbusExceptions as merror
import socket
import traceback

import logging
_logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Modbus Request handler
# --------------------------------------------------------------------------- #
class ModbusBaseRequestHandler(socketserver.BaseRequestHandler):
    """ Implements the modbus server protocol

    This uses the socketserver.BaseRequestHandler to implement
    the client handler.
    """
    running = False
    framer = None
    
    def setup(self):
        """ Callback for when a client connects
        """
        self.running = True
        self.framer = self.server.framer(self.server.decoder, client=None)
        self.server.threads.append(self)

    def finish(self):
        """ Callback for when a client disconnects
        """
        _logger.debug("Client Disconnected [%s:%s]" % self.client_address)
        self.server.threads.remove(self)

    def execute(self, request):
        """ The callback to call with the resulting message

        :param request: The decoded request message
        """
        broadcast = False
        try:
            if self.server.broadcast_enable and request.unit_id == 0:
                broadcast = True
                # if broadcasting then execute on all slave contexts, note response will be ignored
                for unit_id in self.server.context.slaves():
                    response = request.execute(self.server.context[unit_id])
            else:
                context = self.server.context[request.unit_id]
                response = request.execute(context)

                words = self._get_register_words(request.address, request.count, context)
                print(words)

        except NoSuchSlaveException as ex:
            _logger.debug("requested slave does "
                          "not exist: %s" % request.unit_id )
            if self.server.ignore_missing_slaves:
                return  # the client will simply timeout waiting for a response
            response = request.doException(merror.GatewayNoResponse)
        except Exception as ex:
            _logger.debug("Datastore unable to fulfill request: "
                          "%s; %s", ex, traceback.format_exc())
            response = request.doException(merror.SlaveFailure)
        # no response when broadcasting
        if not broadcast:
            response.transaction_id = request.transaction_id
            response.unit_id = request.unit_id
            self.send(response)

    def _get_register_words(self, address, num_of_registers, context):
        '''
        Convert requested register values to words (16bit)
        Returns converted register values in list format
        '''
        registers = context.store['h'].values[address+1:num_of_registers+1]
        words = ['{0:016b}'.format(idx) for idx in registers]
        return words
    
    def _get_register_bits(self, address, num_of_registers, context):
        '''
        Convert requested register values to bits
        Returns register value bits in a list format.
        '''
        words = self._get_register_words(address, num_of_registers, context)
        bits  = [list(idx) for idx in words]
        return bits


# --------------------------------------------------------------------------- #
# Modbus Request handler
# --------------------------------------------------------------------------- #
class ModbusRequestHandler(ModbusBaseRequestHandler):
    """ Implements the modbus server protocol

    This uses the socketserver.BaseRequestHandler to implement
    the client handler for a connected protocol (TCP).
    """

    def handle(self):
        """Callback when we receive any data, until self.running becomes False.
        Blocks indefinitely awaiting data.  If shutdown is required, then the
        global socket.settimeout(<seconds>) may be used, to allow timely
        checking of self.running.  However, since this also affects socket
        connects, if there are outgoing socket connections used in the same
        program, then these will be prevented, if the specfied timeout is too
        short.  Hence, this is unreliable.
        """
        reset_frame = False
        while self.running:
            try:
                units = self.server.context.slaves()
                data = self.request.recv(1024)
                
                if not data:
                    self.running = False
                else:
                    if not isinstance(units, (list, tuple)):
                        units = [units]
                    # if broadcast is enabled make sure to
                    # process requests to address 0
                    if self.server.broadcast_enable:
                        if 0 not in units:
                            units.append(0)

                if _logger.isEnabledFor(logging.DEBUG):
                    _logger.debug('Handling data: ' + hexlify_packets(data))
                single = self.server.context.single
                self.framer.processIncomingPacket(data, self.execute, units,
                                                  single=single)

            except socket.timeout as msg:
                if _logger.isEnabledFor(logging.DEBUG):
                    _logger.debug("Socket timeout occurred %s", msg)
                reset_frame = True
            except socket.error as msg:
                _logger.error("Socket error occurred %s" % msg)
                self.running = False
            except:
                _logger.error("Socket exception occurred "
                              "%s" % traceback.format_exc() )
                self.running = False
                reset_frame = True
            finally:
                if reset_frame:
                    self.framer.resetFrame()
                    reset_frame = False

    def send(self, message):
        """ Send a request (string) to the network

        :param message: The unencoded modbus response
        """
        if message.should_respond:
            # self.server.control.Counter.BusMessage += 1
            pdu = self.framer.buildPacket(message)
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug('send: [%s]- %s' % (message, b2a_hex(pdu)))
            return self.request.send(pdu)
