import pathlib
import socket
try:
    import can
except:
    pass
import sys
import threading

pj_path = pathlib.Path(__file__).parent.parent.parent.parent.parent
print(f'pj_path: {pj_path}')
sys.path.append(str(pj_path))
print(f'sys.path: {sys.path}')

ALLOWED_CONNECTIONS = 1
BUFFER_SIZE = 1024
DEFAULT_ENCODING = 'utf-8'
LOST_CONNECTION_PACKAGE = ''
LOST_CONNECTION_PACKAGES_LIMIT = 5


class GServer:
    """
    GServer
    """

    def __init__(self, port, encoding=DEFAULT_ENCODING):
        """
        """
        self.__port = port

        self.__connection = self.__start()
        self.__connected = False

        self.__encoding = encoding

        self.echo_mode_on = False

        self.__client = None

        try:
            self.__can = can.interface.Bus(interface='socketcan', channel='can0', bitrate=500000)
        except Exception as exception:
            self.__can = None
            error = f'Failed to init CAN: {exception}'
            self.__log_error(error)

    def connect_with_client(self):
        """connect_with_client

            Connects with a requesting client.
        :return: None
        """
        client_is_valid = False

        self.__log_info("Waiting for connection request...")
        while not client_is_valid:
            # establish a connection
            self.__client, client_address = self.__connection.accept()
            self.__log_info("Got a connection request from {}".format(str(client_address[0])))

            client_is_valid = True
            self.__log_info("Connected to {}!".format(client_address))

            if client_is_valid:
                pass
            else:
                self.__log_info("Unknown client connection request! Connection refused!")
                self.__client.shutdown(socket.SHUT_RDWR)
                self.__client.close()
                self.__client = None

    def __log_info(self, info):
        """

        """
        assert self
        print(info)

    def __log_warning(self, warning):
        """

        """
        assert self
        print(warning)

    def __log_error(self, error):
        """

        """
        assert self
        print(error)

    @property
    def port(self):
        """

        """
        return self.__port

    def get_local_machine_ip_addresses(self):
        """__get_local_machine_ip_addresses__

            Fetch a list of local's machine IP addresses.
        :return: list of IP addresses
        :rtype: list of str
        """
        ip_list = []
        try:
            ip_list.append([_ for _ in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                                         if not ip.startswith("127.")][:1],
                                        [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close())
                                          for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]])
                            if _][0][0])
        except Exception as err:
            error = "Couldn't fetch local machine's IP addresses! {}".format(err)
            self.__log_error(error)

        return ip_list

    def __start(self):
        """
            Start GServer.
        :return: starting server result
        :rtype: socket.socket
        """
        self.__log_info("Starting Gserver...")
        try:
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.bind(("", self.__port))
        except Exception as err:
            error = "Failed to start GServer! {}".format(err)
            self.__log_error(error)
            return False

        connection.listen(ALLOWED_CONNECTIONS)
        self.__connected = True

        machine_ips = self.get_local_machine_ip_addresses()
        if len(machine_ips) > 0:
            self.__log_info("GServer is running and waiting for client connection!")
            self.__log_info("HOSTNAME: {}".format(socket.gethostname()))

            for ip_index, machine_ip in enumerate(machine_ips):
                self.__log_info("IP option #{}: {}".format(ip_index + 1, machine_ip))
            self.__log_info("PORT: {}".format(self.__port))
        else:
            self.__log_info("Failed to retrieve local machine's IP address!")
            return False

        return connection

    def stop(self):
        """
        Stop GServer.
        :return: stopping server result
        :rtype: bool
        """
        self.__log_info("Stopping GServer...")
        try:
            self.__connection.close()
        except Exception as err:
            error = "Failed to stop GServer! {}".format(err)
            self.__log_error(error)
            return False

        self.__connection = None
        self.__connected = False

        return True

    def __get_package_from_client__(self):
        """__get_package_from_client__

            Get a package from client.
        :return: package
        :rtype: bytearray
        """
        package = self.__client.recv(BUFFER_SIZE)
        return package

    def string_to_bytes(self, _string, encoding=None):
        """
            Method converts string type to bytes, using specified encoding.
        Conversion is required for socket's data transfer protocol: string type is not supported.
        :param _string: string to be converted
        :param encoding: character encoding key
        :return: bytes(_string, encoding)
        """
        return bytes(_string, self.__encoding)

    def send_package(self, package):
        """
            Sends a package to the server.
        :param package: package to be sent
        :return: True if ok, error occurred otherwise
        """
        try:
            package = self.string_to_bytes(package)
            self.__client.send(package)
            return True
        except Exception as err:
            error = "Error occurred while sending package to server: " + str(err)
            self.__log_warning(error)
            return error

    def __echo__(self):
        """__echo__

            Thread echo.
        :return: None
        """
        while self.echo_mode_on:
            incoming_package = self.__get_package_from_client__()

            self.__log_info("echo mode - received package: {} - {}".format(incoming_package, len(incoming_package)))

            speed = incoming_package[0] << 8 | incoming_package[1]
            speed *= 89.6 * 1.09
            print(speed)

            rpm = incoming_package[2] << 8 | incoming_package[3]
            rpm *= 1.02
            print(rpm)

            package = []
            speed_bytes = int(speed).to_bytes(2, 'big', signed=False)
            print(speed_bytes)
            rpm_bytes = int(rpm).to_bytes(2, 'big', signed=False)
            print(rpm_bytes)

            for b in rpm_bytes:
                package.append(int(b))
            package.extend([69, 69])
            for b in speed_bytes:
                package.append(int(b))
            package.extend([69, 69])

            if self.__can:
                try:
                    tx_msg = can.Message(arbitration_id=0x201,
                                         data=package, is_extended_id=False)
                    self.__can.send(tx_msg)
                    tx_msg = can.Message(arbitration_id=0x212,
                                         data=[0, 0, 0, 0, 0, 0, 0, 0, ], is_extended_id=False)
                    self.__can.send(tx_msg)
                    tx_msg = can.Message(arbitration_id=0x420,
                                         data=[0x9b, 0, 0, 0, 0, 0, 0, 0, ], is_extended_id=False)
                    self.__can.send(tx_msg)
                    tx_msg = can.Message(arbitration_id=0x422,
                                         data=[0, 0, 0, 0, 0, 0, 0, 0, ], is_extended_id=False)
                    self.__can.send(tx_msg)
                except Exception as exception:
                    error = f'Failed to send CAN msg: {exception}'
                    self.__log_error(error)

    def echo(self):
        """echo

            Run server in echo mode.
        :return: None
        """
        if self.__client is None:
            self.connect_with_client()

        package_income_thread = threading.Thread(target=self.__echo__)
        self.echo_mode_on = True
        package_income_thread.start()

    def stop_echo(self):
        """echo

            Stop echo mode.
        :return: None
        """
        self.echo_mode_on = False
        self.__log_info("Stopped echo mode!")


def main():
    """"""
    gs = GServer(
        port=8069,
    )
    try:
        gs.echo()
    except KeyboardInterrupt:
        gs.stop()
    gs.stop()


if __name__ == '__main__':
    main()
