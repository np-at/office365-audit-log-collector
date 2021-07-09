# Standard libs
import socket
import json
from collections import deque
import threading


class GraylogInterface(object):

    def __init__(self, graylog_address, graylog_port, use_nv_formatter=False):

        self.use_nv_formatter = use_nv_formatter
        self.gl_address = graylog_address
        self.gl_port = graylog_port
        self.monitor_thread = None
        self.queue = deque()

    def start(self):

        self.monitor_thread = threading.Thread(target=self.monitor_queue, daemon=True)
        self.monitor_thread.start()

    def stop(self, gracefully=True):

        self.queue.insert(0 if not gracefully else -1, 'stop monitor thread')
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()

    def monitor_queue(self):

        while 1:
            if self.queue:
                msg = self.queue.popleft()
                if msg == 'stop monitor thread':
                    return
                else:
                    self._send_message_to_graylog(msg=msg)

    def send_messages_to_graylog(self, *messages):

        for message in messages:
            self.queue.append(message)

    def _connect_to_graylog_input(self):
        """
        Return a socket connected to the Graylog input.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.gl_address, int(self.gl_port)))
        return s

    def _send_message_to_graylog(self, msg):
        """
        Send a single message to a graylog input; the socket must be closed after each individual message,
        otherwise Graylog will interpret it as a single large message.
        :param msg: dict
        """
        if self.use_nv_formatter:
            msg = self.nv_formatter(msg)

        msg_string = json.dumps(msg)
        if not msg_string:
            return
        sock = self._connect_to_graylog_input()
        try:
            sock.sendall(msg_string.encode())
        except:
            sock.close()
        else:
            sock.close()

    @staticmethod
    def nv_formatter(json_content):
        """
        Flattens {Name: name, Value: value} objects into { name: value } for easier parsing by graylog
        :param json_content: dict
        :returns dict
        """
        for i in json_content:
            if type(json_content[i]) == list:
                prop_name_to_replace = i
                new_prop = {}
                for y in json_content[i]:
                    if type(y) == dict:
                        new_prop_prop_name = None
                        new_prop_prop_value = []
                        for prop in y:
                            if str.lower(prop) == 'name':
                                new_prop_prop_name = y[prop]
                            elif str.lower(prop) == 'value':
                                if len(y) == 2:
                                    new_prop_prop_value.append(y[prop])
                                else:
                                    new_prop_prop_value.append({prop: y[prop]})
                            else:
                                new_prop_prop_value.append({prop: y[prop]})

                        if new_prop_prop_name:
                            if len(new_prop_prop_value) == 1:
                                new_prop[new_prop_prop_name] = new_prop_prop_value[0]
                            else:
                                new_prop[new_prop_prop_name] = new_prop_prop_value

                if len(new_prop) >= 1:
                    json_content[prop_name_to_replace] = new_prop
        return json_content
