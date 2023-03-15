import sys

from PyQt6.QtCore import QDateTime,QTimer,pyqtSignal, QObject, pyqtSlot, QThread
from PyQt6.QtWidgets import QApplication, QLabel,QTableWidget, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import *
import paho.mqtt.client as mqtt
import json
import time
import urllib.request
from functools import partial
import winsound

offlineTime = 5
freshDataTime = 30
maxShowDataTime = 120
localRecordsFilePath = "log.json"

hostname = "test.mosquitto.org"
username = ""
portnum = 1883
password = ""
broker_topic = "HELLO-TOPIC-HM123"

# hostname = input("HostName:")
# portnum = input("Port:")
# username = input("Username:")
# password = input("Password:")

# broker_topic = input("Topic:")
# offlineTime = input("OfflineTime:")
# freshDataTime = input("FreshDataTime:")
# maxShowDataTime = input("MaxShowDataTime:")
# localRecordsFilePath = input("JsonLogFile:")

start_time = time.time()
class Downloader(QObject):
    # downloaded = pyqtSignal(bytes)
    
    @pyqtSlot(str)
    def download(self, url, photo):
        # self.photo = pho
        img = urllib.request.urlopen(url).read()
        pixmap1 = QPixmap()
        if img:
            pixmap1.loadFromData(img)
            photo.setPixmap(pixmap1.scaledToWidth(150))
        # self.downloaded.emit(img)

class MainGUI(QWidget):
    def __init__(self, main, *args, **kwargs):
        super(MainGUI,self).__init__()
        self.main = main
        self.last_message_time = time.time()
        self.setupUi()
        self.log_file = open('log.json', 'r', encoding='utf-8').read()
        self.log_json = []
        if self.log_file:
            self.log_json = json.loads(self.log_file)
        self.load_json_log()
        self.show()

    def load_json_log(self):
        for i in self.log_json:
            if i:
                if (start_time - int(i['time'])) < maxShowDataTime:
                    self.add_device_item(json.dumps(i))

    def setupUi(self):
        self.setFont(QFont('Times', 14))
        self.setWindowTitle("App")
        self.setGeometry(100,100,700,500)
        self.mainlayout = QVBoxLayout()
        self.setLayout(self.mainlayout)
        self.toplayout = QHBoxLayout()
        self.centerlayout = QVBoxLayout()
        self.statusLabel = QLabel()
        self.statusMsg = QLabel()
        self.dateLabel = QLabel()
        self.statusLabel.setFont(QFont('Times', 14))

        self.toplayout.addWidget(self.statusLabel)
        self.toplayout.addWidget(self.statusMsg)
        self.toplayout.addStretch()
        self.toplayout.addWidget(self.dateLabel)

        self.tableWidget = QTableWidget()
        self.tableWidget.horizontalHeader().setMinimumSectionSize(152)
        self.tableWidget.verticalHeader().setMinimumSectionSize(82)
        self.tableWidget.verticalHeader().setMinimumHeight(82)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.horizontalHeader().hide()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.centerlayout.addWidget(self.tableWidget)
        
        self.mainlayout.addLayout(self.toplayout)
        self.mainlayout.addLayout(self.centerlayout)
    
    
    def change_state_online(self):
        self.statusLabel.setText("Online")
        self.statusLabel.setStyleSheet("QLabel { background-color : rgb(144, 238, 144); color : black;border: 1px solid black; }")
        self.statusMsg.setText("Everything is Ok!")

    def change_state_offline(self):
        self.statusLabel.setText("Offline")
        self.statusLabel.setStyleSheet("QLabel { background-color : rgb(255, 0, 0); color : black;border: 1px solid black; }")
        self.statusMsg.setText("")

    def update_packet(self, dev_info, packet_json, message_time, photo1, photo2):
        initialSeconds = time.time() - message_time
        hours = initialSeconds // 3600
        minutes = (initialSeconds - (hours * 3600)) // 60
        seconds = initialSeconds % 60

        local_time = "%d:%02d:%02d" % (hours, minutes, seconds)

        if (time.time() - message_time) < freshDataTime:
            photo1.setStyleSheet("QLabel {border: 2px solid red; margin: 5px;}")
            photo2.setStyleSheet("QLabel {border: 2px solid red; margin: 5px;}")
            dev_info.setStyleSheet("QLabel {border: 2px solid red; margin: 5px;}")
            dev_info.setText(str(packet_json['device']) +"("+str(local_time)+")"+"\n"+packet_json['textA']+"\n"+packet_json['textB'])
        else:
            photo1.setStyleSheet("QLabel {border: 2px solid black; margin: 5px;}")
            photo2.setStyleSheet("QLabel {border: 2px solid black; margin: 5px;}")
            dev_info.setStyleSheet("QLabel {border: 2px solid black; margin: 5px;}")
            dev_info.setText(str(packet_json['device']) +"("+str(local_time)+")"+"\n"+packet_json['textA']+"\n"+packet_json['textB'])

    def closeEvent(self, event):
        json_log_file = open("log.json", "w")
        jsonString = json.dumps(self.log_json)
        json_log_file.write(jsonString)
        json_log_file.close()
        
    
    def add_device_item(self,msg):
        packet_json = json.loads(msg)
        self.tableWidget.insertRow(0)
        self.tableWidget.setRowHeight(0,90)
        photo1 = QLabel()
        self.thread = QThread(self)
        self.thread.start()

        self.downloader1 = Downloader()
        self.downloader1.moveToThread(self.thread)
        
        wrapper1 = partial(self.downloader1.download, str(packet_json['photo1']), photo1)
        QTimer.singleShot(0, wrapper1)
        
        photo1.setMinimumSize(150,80)
        photo2 = QLabel()
        photo2.setMinimumSize(150,80)
        message_time = time.time()
        self.last_message_time = message_time
        self.downloader2 = Downloader()
        self.downloader2.moveToThread(self.thread)

        wrapper2 = partial(self.downloader1.download, str(packet_json['photo2']), photo2)
        QTimer.singleShot(0, wrapper2)

        dev_info = QLabel()
        dev_info.setStyleSheet("QLabel {border: 2px solid black; margin: 5px;}")
        dev_info.setFont(QFont('Times', 12))
        dev_info.setMinimumSize(250,80)

        newTimer = QTimer(dev_info)
        newTimer.timeout.connect(lambda: self.update_packet(dev_info, packet_json,message_time, photo1,photo2))
        newTimer.start(1000)

        dev_info.setText(str(packet_json['device'])+"\n"+packet_json['textA']+"\n"+packet_json['textB'])

        self.tableWidget.setCellWidget(0,0,photo1)
        self.tableWidget.setCellWidget(0,1,photo2)
        self.tableWidget.setCellWidget(0,2,dev_info)
        
        
        if (time.time() - start_time ) > maxShowDataTime:
            self.tableWidget.removeRow(self.tableWidget.rowCount()-1)

class Communicate(QObject):
    packetRecieved = pyqtSignal(str)

class MainApp(object):
    def __init__(self):
        
        self.c = Communicate()
        self.c.packetRecieved.connect(self.on_message_received)
        self.window = MainGUI(self)
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.connect_to_mqtt_server()
        self.client.loop_start()

        timer = QTimer(self.window)
        timer.timeout.connect(lambda: self.timeoutEvent())
        timer.start(1000)

    def timeoutEvent(self):
        self.window.dateLabel.setText(QDateTime.currentDateTime().toString("dd/MM/yyyy hh:mm:ss"))
        if(time.time() - self.window.last_message_time) >= offlineTime:
            self.window.change_state_offline()
        else:
            self.window.change_state_online()

    def on_message(self,client, userdata, msg):
        self.c.packetRecieved.emit(msg.payload.decode())
        packet_json = json.loads(msg.payload.decode())
        self.window.log_json.append(packet_json)

    def on_connect(self,client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(broker_topic)
            self.window.change_state_online()
        else:
            self.window.change_state_offline()
    
    def on_disconnect(self, userdata, flags, rc):
        self.window.change_state_offline()
    
    def on_message_received(self,msg):
        winsound.Beep(440, 500)
        self.window.add_device_item(msg)

    def connect_to_mqtt_server(self):
        self.client.username_pw_set(username, password)
        try:
            self.client.connect(hostname, portnum,60)
        except:
            self.window.statusLabel.setText("Offline")
            self.window.statusLabel.setStyleSheet("QLabel { background-color : rgb(255, 0, 0); color : black;border: 1px solid black; }")

def main():
    app = QApplication([])
    app.setStyle('Fusion')
    main = MainApp()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()