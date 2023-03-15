#!/usr/bin/env python3
"""A PyQt5 GUI utility to monitor and send MQTT server messages."""

################################################################
# Written in 2018-2020 by Garth Zeglin <garthz@cmu.edu>

# To the extent possible under law, the author has dedicated all copyright
# and related and neighboring rights to this software to the public domain
# worldwide. This software is distributed without any warranty.

# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

################################################################
# standard Python libraries
from __future__ import print_function
import os, sys, struct, time, logging, functools, queue, signal, getpass

# documentation: https://doc.qt.io/qt-5/index.html
# documentation: https://www.riverbankcomputing.com/static/Docs/PyQt5/index.html
from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork

# documentation: https://www.eclipse.org/paho/clients/python/docs/
import paho.mqtt.client as mqtt

# default logging output
log = logging.getLogger('main')

# logger to pass to the MQTT library
mqtt_log = logging.getLogger('mqtt')
mqtt_log.setLevel(logging.WARNING)

# IDeATE server instances, as per https://mqtt.ideate.cmu.edu/#ports

ideate_ports = { 
    1883:'1883',
    8884 : '16-223',
                 8885 : '16-375',
                 8886 : '60-223',
                 8887 : '62-362',
}

mqtt_rc_codes = ['Success', 'Incorrect protocol version', 'Invalid client identifier', 'Server unavailable', 'Bad username or password', 'Not authorized']

################################################################
class MainGUI(QtWidgets.QMainWindow):
    """A custom main window which provides all GUI controls.  Requires a delegate main application object to handle user requests."""

    def __init__(self, main, *args, **kwargs):
        super(MainGUI,self).__init__()

        # save the main object for delegating GUI events
        self.main = main

        # create the GUI elements
        self.console_queue = queue.Queue()
        self.setupUi()

        self._handler = None
        self.enable_console_logging()

        # finish initialization
        self.show()

        # manage the console output across threads
        self.console_timer = QtCore.QTimer()
        self.console_timer.timeout.connect(self._poll_console_queue)
        self.console_timer.start(50)  # units are milliseconds

        return

    # ------------------------------------------------------------------------------------------------
    def setupUi(self):
        self.setWindowTitle("IDeATe MQTT Monitor")
        self.resize(600, 600)

        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(-1, -1, -1, 9) # left, top, right, bottom

        # help panel button
        help = QtWidgets.QPushButton('Open the Help Panel')
        help.pressed.connect(self.help_requested)
        self.verticalLayout.addWidget(help)

        # generate GUI for configuring the MQTT connection

        # server name entry and port selection
        hbox = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(hbox)
        hbox.addWidget(QtWidgets.QLabel("MQTT server address:"))
        self.mqtt_server_name = QtWidgets.QLineEdit()
        self.mqtt_server_name.setText(str(self.main.hostname))
        self.mqtt_server_name.editingFinished.connect(self.mqtt_server_name_entered)
        hbox.addWidget(self.mqtt_server_name)

        hbox.addWidget(QtWidgets.QLabel("port:"))
        self.port_selector = QtWidgets.QComboBox()
        hbox.addWidget(self.port_selector)

        self.port_selector.addItem("")
        for pairs in ideate_ports.items():
            self.port_selector.addItem("%d (%s)" % pairs)
        self.port_selector.activated['QString'].connect(self.mqtt_port_selected)

        # attempt to pre-select the stored port number
        try:
            idx = list(ideate_ports.keys()).index(self.main.portnum)
            self.port_selector.setCurrentIndex(idx+1)
        except ValueError:
            pass

        # instructions
        explanation = QtWidgets.QLabel("""Username and password provided by instructor.  Please see help panel for details.""")
        explanation.setWordWrap(True)
        self.verticalLayout.addWidget(explanation)

        # user and password entry
        hbox = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(hbox)
        hbox.addWidget(QtWidgets.QLabel("MQTT username:"))
        self.mqtt_username = QtWidgets.QLineEdit()
        self.mqtt_username.setText(str(self.main.username))
        self.mqtt_username.editingFinished.connect(self.mqtt_username_entered)
        hbox.addWidget(self.mqtt_username)

        hbox.addWidget(QtWidgets.QLabel("password:"))
        self.mqtt_password = QtWidgets.QLineEdit()
        self.mqtt_password.setText(str(self.main.password))
        self.mqtt_password.editingFinished.connect(self.mqtt_password_entered)
        hbox.addWidget(self.mqtt_password)

        # instructions
        explanation = QtWidgets.QLabel("""A subscription specifies topics to receive.  Please see help panel for details.""")
        explanation.setWordWrap(True)
        self.verticalLayout.addWidget(explanation)

        # subscription topic entry
        hbox = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("MQTT message subscription:")
        self.mqtt_sub = QtWidgets.QLineEdit()
        self.mqtt_sub.setText(self.main.subscription)
        self.mqtt_sub.editingFinished.connect(self.mqtt_sub_entered)
        hbox.addWidget(label)
        hbox.addWidget(self.mqtt_sub)
        self.verticalLayout.addLayout(hbox)

        # connection indicator
        self.connected = QtWidgets.QLabel()
        self.connected.setLineWidth(3)
        self.connected.setFrameStyle(QtWidgets.QFrame.Box)
        self.connected.setAlignment(QtCore.Qt.AlignCenter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.connected.setSizePolicy(sizePolicy)
        self.set_connected_state(False)

        # connection control buttons
        connect = QtWidgets.QPushButton('Connect')
        connect.pressed.connect(self.connection_requested)
        disconnect = QtWidgets.QPushButton('Disconnect')
        disconnect.pressed.connect(self.main.disconnect_from_mqtt_server)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.connected)
        hbox.addWidget(connect)
        hbox.addWidget(disconnect)
        self.verticalLayout.addLayout(hbox)

        # text area for displaying both internal and received messages
        self.consoleOutput = QtWidgets.QPlainTextEdit()
        self.consoleOutput.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.verticalLayout.addWidget(self.consoleOutput)

        # instructions
        explanation = QtWidgets.QLabel("""Pressing enter in the data field will broadcast the string on the given topic.""")
        explanation.setWordWrap(True)
        self.verticalLayout.addWidget(explanation)

        # message topic entry
        hbox = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("MQTT message topic:")
        self.mqtt_topic = QtWidgets.QLineEdit()
        self.mqtt_topic.setText(self.main.topic)
        self.mqtt_topic.editingFinished.connect(self.mqtt_topic_entered)
        hbox.addWidget(label)
        hbox.addWidget(self.mqtt_topic)
        self.verticalLayout.addLayout(hbox)

        # message payload entry
        hbox = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("MQTT message data:")
        self.mqtt_payload = QtWidgets.QLineEdit()
        self.mqtt_payload.setText(self.main.payload)
        self.mqtt_payload.returnPressed.connect(self.mqtt_payload_entered)
        hbox.addWidget(label)
        hbox.addWidget(self.mqtt_payload)
        self.verticalLayout.addLayout(hbox)

        # set up the status bar which appears at the bottom of the window
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # set up the main menu
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 500, 22))
        self.menubar.setNativeMenuBar(False)
        self.menubar.setObjectName("menubar")
        self.menuTitle = QtWidgets.QMenu(self.menubar)
        self.setMenuBar(self.menubar)
        self.actionQuit = QtWidgets.QAction(self)
        self.menuTitle.addAction(self.actionQuit)
        self.menubar.addAction(self.menuTitle.menuAction())
        self.menuTitle.setTitle("File")
        self.actionQuit.setText("Quit")
        self.actionQuit.setShortcut("Ctrl+Q")
        self.actionQuit.triggered.connect(self.quitSelected)

        return

    # --- logging to screen -------------------------------------------------------------
    def enable_console_logging(self):
        # get the root logger to receive all logging traffic
        logger = logging.getLogger()
        # create a logging handler which writes to the console window via self.write
        handler = logging.StreamHandler(self)
        handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s: %(message)s'))
        logger.addHandler(handler)
        # logger.setLevel(logging.NOTSET)
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.NOTSET)
        self._handler = handler
        log.info("Enabled logging in console window.")
        return

    def disable_console_logging(self):
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)
            self._handler = None

    # --- window and qt event processing -------------------------------------------------------------
    def show_status(self, string):
        self.statusbar.showMessage(string)

    def _poll_console_queue(self):
        """Write any queued console text to the console text area from the main thread."""
        while not self.console_queue.empty():
            string = str(self.console_queue.get())
            stripped = string.rstrip()
            if stripped != "":
                self.consoleOutput.appendPlainText(stripped)
        return

    def write(self, string):
        """Write output to the console text area in a thread-safe way.  Qt only allows
        calls from the main thread, but the service routines run on separate threads."""
        self.console_queue.put(string)
        return

    def quitSelected(self):
        self.write("User selected quit.")
        self.close()

    def closeEvent(self, event):
        self.write("Received window close event.")
        self.main.app_is_exiting()
        self.disable_console_logging()
        super(MainGUI,self).closeEvent(event)

    def set_connected_state(self, flag):
        if flag is True:
            self.connected.setText("  Connected   ")
            self.connected.setStyleSheet("color: white; background-color: green;")
        else:
            self.connected.setText(" Not Connected ")
            self.connected.setStyleSheet("color: white; background-color: blue;")


    # --- GUI widget event processing ----------------------------------------------------------------------

    def help_requested(self):
        panel = QtWidgets.QDialog(self)
        panel.resize(600,400)
        panel.setWindowTitle("IDeATe MQTT Monitor: Help Info")
        vbox = QtWidgets.QVBoxLayout(panel)
        hbox = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox)
        text = QtWidgets.QTextEdit(panel)
        hbox.addWidget(text)
        text.insertHtml("""
<style type="text/css">
table { margin-left: 20px; }
td { padding-left: 20px; }
</style>
<a href="#top"></a>
<h1>IDeATe MQTT Monitor</h1>
<p>This Python application is a tool intended for debugging programs which pass short data messages back and forth across the network via a MQTT server.  It supports opening an authenticated connection to the server, subscribing to a class of messages in order to receive them, viewing message traffic, and publishing new messages on a specified message topic.</p>
<h2>Connecting</h2>
<p>The first set of controls configures server parameters before attempting a connection.  Changes will not take effect until the next connection attempt.</p

<dl>
  <dt>server address</dt><dd>The network name of the MQTT server. (Defaults to mqtt.ideate.cmu.edu.)</dd>
  <dt>server port</dt><dd>The numeric port number for the MQTT server.  IDeATe is using a separate server for each course, so the drop-down menu also identifies the associated course number.</dd>
  <dt>username</dt><dd>Server-specific identity, chosen by your instructor.</dd>
  <dt>password</dt><dd>Server-specific password, chosen by your instructor.</dd>
</dl>

<p>Your username and password is specific to the MQTT server and will be provided by your instructor.  This may be individual or may be a shared login for all students in the course.  Please note, the password will not be your Andrew password.</p>

<h2>Listening</h2>

<p>MQTT works on a publish/subscribe model in which messages are published on <i>topics</i> identified by a topic name.  The name is structured like a path string separated by <tt>/</tt> characters to organize messages into a hierarchy of topics and subtopics.
Our course policy will be to prefix all topics with a student andrew ID, e.g. if your user name is xyzzy, we ask that you publish on the 'xyzzy' topic and sub-topics, as per the following examples.</p>


<p>
<table>
<tr><td><b>xyzzy</b></td><td>top-level topic on which user 'xyzzy' should publish</td></tr>
<tr><td><b>xyzzy/status</b></td><td>a sub-topic on which user 'xyzzy' could publish</td></tr>
<tr><td><b>xyzzy/sensor</b></td><td>another sub-topic on which user 'xyzzy' could publish</td></tr>
<tr><td><b>xyzzy/sensor/1</b></td><td>a possible sub-sub-topic</td></tr>
</table>
</p>

<p>The message subscription field specifies topics to receive.  The subscription may include a # character as a wildcard, as per the following examples.</p>
<p><table>
<tr><td><b>#</b></td><td>subscribe to all messages</td></tr>
<tr><td><b>xyzzy</b></td><td>subscribe to the top-level published messages for user xyzzy</td></tr>
<tr><td><b>xyzzy/#</b></td><td>subscribe to all published messages for user xyzzy, including subtopics</td></tr>
</table>
</p>
<p>Changing the subscription field immediately changes what is received; the monitor unsubscribes from the previous pattern and subscribes to the new one.  Entering an empty field defaults to the global pattern '#'.</p>

<p>The large text field is the console area which shows both debugging and status log messages as well as received messages.</p>

<h2>Sending</h2>

<p>At the bottom are a topic field and data field for publishing plain text messages.  Pressing enter in the data field will
transmit the data string on the specified topic.  The text is not cleared after entry, so pressing enter multiple times will send the same text multiple times.</p>
<p>The MQTT protocol supports binary messages (i.e. any sequence of bytes), but this tool currently only supports sending messages with plain text.</p>


<h2>More Information</h2>

<p>The IDeATE server has more detailed information on the server help page at <b>https://mqtt.ideate.cmu.edu</b></p>

""")
        text.scrollToAnchor("top")
        text.setReadOnly(True)
        panel.show()

    def mqtt_server_name_entered(self):
        name = self.mqtt_server_name.text()
        self.write("Server name changed: %s" % name)
        self.main.set_server_name(name)

    def decode_port_selection(self):
        title = self.port_selector.currentText()
        if title == "":
            return None
        else:
            return int(title.split()[0])  # convert the first token to a number

    def mqtt_port_selected(self, title):
        portnum  = self.decode_port_selection()
        self.write("Port selection changed: %s" % title)
        self.main.set_server_port(portnum)

    def mqtt_username_entered(self):
        name = self.mqtt_username.text()
        self.write("User name changed: %s" % name)
        self.main.set_username(name)

    def mqtt_password_entered(self):
        name = self.mqtt_password.text()
        self.write("Password changed: %s" % name)
        self.main.set_password(name)

    def connection_requested(self):
        # When the connect button is pressed, make sure all fields are up to
        # date.  It is otherwise possible to leave a text field selected with
        # unreceived changes while pressing Connect.
        hostname = self.mqtt_server_name.text()
        portnum  = self.decode_port_selection()
        username = self.mqtt_username.text()
        password = self.mqtt_password.text()

        self.main.set_server_name(hostname)
        self.main.set_server_port(portnum)
        self.main.set_username(username)
        self.main.set_password(password)

        self.main.connect_to_mqtt_server()

    def mqtt_sub_entered(self):
        sub = self.mqtt_sub.text()
        if sub == '':
            self.mqtt_sub.setText("#")
            sub = "#"

        self.write("Subscription changed to: %s" % sub)
        self.main.set_subscription(sub)

    def mqtt_topic_entered(self):
        topic = self.mqtt_topic.text()
        self.write("Topic changed to: %s" % topic)
        self.main.set_topic(topic)

    def mqtt_payload_entered(self):
        topic = self.mqtt_topic.text()
        payload = self.mqtt_payload.text()
        self.main.send_message(topic, payload)

################################################################
class MainApp(object):
    """Main application object holding any non-GUI related state."""

    def __init__(self):

        # Attach a handler to the keyboard interrupt (control-C).
        signal.signal(signal.SIGINT, self._sigint_handler)

        # load any available persistent application settings
        QtCore.QCoreApplication.setOrganizationName("IDeATe")
        QtCore.QCoreApplication.setOrganizationDomain("ideate.cmu.edu")
        QtCore.QCoreApplication.setApplicationName('mqtt_monitor')
        self.settings = QtCore.QSettings()

        # uncomment to restore 'factory defaults'
        # self.settings.clear()

        # MQTT server settings
        self.hostname = self.settings.value('mqtt_host', 'mqtt.ideate.cmu.edu')
        self.portnum  = self.settings.value('mqtt_port', None)
        self.username = self.settings.value('mqtt_user', 'students')
        self.password = self.settings.value('mqtt_password', '(not yet entered)')

        # Create a default subscription based on the username.  The hash mark is a wildcard.
        username = getpass.getuser()
        self.subscription = self.settings.value('mqtt_subscription', username + '/#')

        # default message to send
        self.topic = self.settings.value('mqtt_topic', username)
        self.payload = self.settings.value('mqtt_payload', 'hello')

        # create the interface window
        self.window = MainGUI(self)

        # Initialize the MQTT client system
        self.client = mqtt.Client()
        self.client.enable_logger(mqtt_log)
        self.client.on_log = self.on_log
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.tls_set()

        self.window.show_status("Please set the MQTT server address and select Connect.")
        return

    ################################################################
    def app_is_exiting(self):
        if self.client.is_connected():
            self.client.disconnect()
            self.client.loop_stop()

    def _sigint_handler(self, signal, frame):
        print("Keyboard interrupt caught, running close handlers...")
        self.app_is_exiting()
        sys.exit(0)

    ################################################################
    def set_server_name(self, name):
        self.hostname = name
        self.settings.setValue('mqtt_host', name)

    def set_server_port(self, value):
        self.portnum = value
        self.settings.setValue('mqtt_port', self.portnum)

    def set_username(self, name):
        self.username = name
        self.settings.setValue('mqtt_user', name)

    def set_password(self, name):
        self.password = name
        self.settings.setValue('mqtt_password', name)

    def connect_to_mqtt_server(self):
        if self.client.is_connected():
            self.window.write("Already connected.")
        else:
            if self.portnum is None:
                log.warning("Please specify the server port before attempting connection.")
            else:
                log.debug("Initiating MQTT connection to %s:%d" % (self.hostname, self.portnum))
                self.window.write("Attempting connection.")
                self.client.username_pw_set(self.username, self.password)
                self.client.connect_async(self.hostname, self.portnum)
                self.client.loop_start()

    def disconnect_from_mqtt_server(self):
        if self.client.is_connected():
            self.client.disconnect()
        else:
            self.window.write("Not connected.")
        self.client.loop_stop()

    ################################################################
    # The callback for when the broker responds to our connection request.
    def on_connect(self, client, userdata, flags, rc):
        self.window.write("Connected to server with with flags: %s, result code: %s" % (flags, rc))

        if rc == 0:
            log.info("Connection succeeded.")

        elif rc > 0:
            if rc < len(mqtt_rc_codes):
                log.warning("Connection failed with error: %s", mqtt_rc_codes[rc])
            else:
                log.warning("Connection failed with unknown error %d", rc)

        # Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.
        client.subscribe(self.subscription)
        self.window.show_status("Connected.")
        self.window.set_connected_state(True)
        return

    # The callback for when the broker responds with error messages.
    def on_log(client, userdata, level, buf):
        log.debug("on_log level %s: %s", level, userdata)
        return

    def on_disconnect(self, client, userdata, rc):
        log.debug("disconnected")
        self.window.write("Disconnected from server.")
        self.window.show_status("Disconnected.")
        self.window.set_connected_state(False)

    # The callback for when a message has been received on a topic to which this
    # client is subscribed.  The message variable is a MQTTMessage that describes
    # all of the message parameters.

    # Some useful MQTTMessage fields: topic, payload, qos, retain, mid, properties.
    #   The payload is a binary string (bytes).
    #   qos is an integer quality of service indicator (0,1, or 2)
    #   mid is an integer message ID.

    def on_message(self, client, userdata, msg):
        self.window.write("{%s} %s" % (msg.topic, msg.payload))
        return

    ################################################################
    def set_subscription(self, sub):
        if self.client.is_connected():
            self.client.unsubscribe(self.subscription)
            try:
                self.client.subscribe(sub)
                self.subscription = sub
                self.settings.setValue('mqtt_subscription', sub)
            except ValueError:
                self.window.write("Invalid subscription string, not changed.")
                self.client.subscribe(self.subscription)
        else:
            self.subscription = sub
            self.settings.setValue('mqtt_subscription', sub)

    def set_topic(self, sub):
        self.topic = sub
        self.settings.setValue('mqtt_topic', sub)

    def send_message(self, topic, payload):
        if self.client.is_connected():
            self.client.publish(topic, payload)
        else:
            self.window.write("Not connected.")
        self.payload = payload
        self.settings.setValue('mqtt_payload', payload)

    ################################################################

def main():
    # Optionally add an additional root log handler to stream messages to the terminal console.
    if False:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s: %(message)s'))
        logging.getLogger().addHandler(console_handler)

    # initialize the Qt system itself
    app = QtWidgets.QApplication(sys.argv)

    # create the main application controller
    main = MainApp()

    # run the event loop until the user is done
    log.info("Starting event loop.")
    sys.exit(app.exec_())

################################################################
# Main script follows.  This sequence is executed when the script is initiated from the command line.

if __name__ == "__main__":
    main()