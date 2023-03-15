import sys

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtWidgets, Qt
from PyQt5.QtCore import pyqtSlot
import csv
import sys,os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from functools import partial
from Import import MOBIUS_API as MA
#import paho.mqtt.client as mqtt
import json
import paho.mqtt.client as mqtt
import pandas as pd
import threading, requests, time


IP='210.105.85.20'
Topic='Smartcs/ITS'


class GetInfDev:
    def __init__(self, value = None, LDev = None,
                 BDev = None, DESdev = None):
        self._value = value
        self._Ldev = LDev
        self._BDev = BDev
        self._DESdev = DESdev
        # getting the values

    @property
    def value(self):
        #print('Getting value')
        return self._value
        # setting the values

    @property
    def LDev(self):
        # setting the values
        return self._Ldev

    @property
    def BDev(self):
        # setting the values
        return self._BDev

    @property
    def DESdev(self):
        # setting the values
        return self._DESdev

    @value.setter
    def value(self, value):
        print('Setting value to ' + value)
        self._value = value
        # deleting the values

    @LDev.setter
    def LDev(self, LDev):
        print('Setting value to ' + LDev)
        self._Ldev = LDev
        # deleting the values

    @BDev.setter
    def BDev(self, BDev):
        print('Setting value to ' + BDev)
        self._BDev = BDev
        # deleting the values

    @DESdev.setter
    def DESdev(self, DESdev):
        print('Setting value to ' + DESdev)
        self._DESdev = DESdev
        # deleting the values

    @value.deleter
    def value(self):
        print('Deleting value')
        del self._value

    @LDev.deleter
    def LDev(self):
        # setting the values
        del self._Ldev

    @BDev.deleter
    def BDev(self):
        # setting the values
        del self._BDev

    @DESdev.deleter
    def DESdev(self):
        # setting the values
        del self._DESdev

class MqttClient(QtCore.QObject):
    Disconnected = 0
    Connecting = 1
    Connected = 2

    MQTT_3_1 = mqtt.MQTTv31
    MQTT_3_1_1 = mqtt.MQTTv311
    connected = QtCore.pyqtSignal() # get Mqtt signal messege con
    disconnected = QtCore.pyqtSignal() # get Mqtt signal messege discon

    stateChanged = QtCore.pyqtSignal(int)
    hostnameChanged = QtCore.pyqtSignal(str)
    portChanged = QtCore.pyqtSignal(int)
    keepAliveChanged = QtCore.pyqtSignal(int)
    cleanSessionChanged = QtCore.pyqtSignal(bool)
    protocolVersionChanged = QtCore.pyqtSignal(int)

    messageSignal = QtCore.pyqtSignal(str) # get Mqtt signal messege

    def __init__(self, parent=None):
        super(MqttClient, self).__init__(parent)
        self.m_hostname = ""
        self.m_port = 1883
        self.m_keepAlive = 60
        self.m_cleanSession = True
        self.m_state = MqttClient.Disconnected
        self.m_protocolVersion = MqttClient.MQTT_3_1

        self.m_client = mqtt.Client(clean_session=self.m_cleanSession, protocol=self.protocolVersion)
        #self.m_client = mqtt.Client()
        self.m_client.on_connect = self.on_connect
        self.m_client.on_message = self.on_message
        self.m_client.on_disconnect = self.on_disconnect

    @QtCore.pyqtProperty(int, notify=stateChanged)
    def state(self):
        return self.m_state

    @state.setter
    def state(self, state):
        if self.m_state == state: return
        self.m_state = state
        self.stateChanged.emit(state)

    @QtCore.pyqtProperty(str, notify=hostnameChanged)
    def hostname(self):
        return self.m_hostname

    @hostname.setter
    def hostname(self, hostname):
        if self.m_hostname == hostname: return
        self.m_hostname = hostname
        self.hostnameChanged.emit(hostname)

    @QtCore.pyqtProperty(int, notify=portChanged)
    def port(self):
        return self.m_port

    @port.setter
    def port(self, port):
        if self.m_port == port: return
        self.m_port = port
        self.portChanged.emit(port)

    @QtCore.pyqtProperty(int, notify=keepAliveChanged)
    def keepAlive(self):
        return self.m_keepAlive

    @keepAlive.setter
    def keepAlive(self, keepAlive):
        if self.m_keepAlive == keepAlive: return
        self.m_keepAlive = keepAlive
        self.keepAliveChanged.emit(keepAlive)

    @QtCore.pyqtProperty(bool, notify=cleanSessionChanged)
    def cleanSession(self):
        return self.m_cleanSession

    @cleanSession.setter
    def cleanSession(self, cleanSession):
        if self.m_cleanSession == cleanSession: return
        self.m_cleanSession = cleanSession
        self.cleanSessionChanged.emit(cleanSession)

    @QtCore.pyqtProperty(int, notify=protocolVersionChanged)
    def protocolVersion(self):
        return self.m_protocolVersion

    @protocolVersion.setter
    def protocolVersion(self, protocolVersion):
        if self.m_protocolVersion == protocolVersion: return
        if protocolVersion in (MqttClient.MQTT_3_1, MqttClient.MQTT_3_1_1):
            self.m_protocolVersion = protocolVersion
            self.protocolVersionChanged.emit(protocolVersion)

    #################################################################
    #           Connect To Host
    #
    def connectToHost(self):
        if self.m_hostname:
            self.m_client.connect(self.m_hostname,
                                  port=self.port,
                                  keepalive=self.keepAlive)
            self.state = MqttClient.Connecting
            #self.m_client.loop_forever()
            self.m_client.loop_start()

    @QtCore.pyqtSlot()
    def disconnectFromHost(self):
        self.m_client.disconnect()

    def subscribe(self, path):
        if self.state == MqttClient.Connected:
            self.m_client.subscribe(path, 1)


    #################################################################
    #            Mqtt callbacks
    #
    def on_message(self, mqttc, obj, msg):
        #mstr = msg.payload.decode("ascii")
        mstr = msg.payload.decode("utf-8", "ignore")
        self.messageSignal.emit(mstr)

    def on_connect(self, *args):
        print("on_connect", args)
        self.state = MqttClient.Connected
        self.connected.emit()

    def on_disconnect(self, *args):
        print("on_disconnect", args)
        self.state = MqttClient.Disconnected
        self.disconnected.emit()


class LoginWidget(QWidget):
    def __init__(self, parent=None):
        super(LoginWidget, self).__init__(parent)
        #self.setWindowTitle("MqttM_ring")




class Widget(QWidget):
    def __init__(self, parent=None):
        super(Widget, self).__init__(parent)
        self.setWindowTitle("MqttM_ring")
        self.txtfilename = "result_file/MOBIUS_ITS_MQTT.csv"

        self.Ae_list = MA.AE_List
        data = list(self.Ae_list['ID'])
        # DES=list(self.Ae_list['DES'])
        self.AE_list = data

        self.btn = []
        self.hBOX = []
        self.vBOX = QtWidgets.QVBoxLayout(self)
        for i in range(20):
            self.hBOX.append(QHBoxLayout(self))
        self.text = QtWidgets.QTextEdit(self)
        self.j = 0
        backgrcolor = 'background-color :  rgb(0, 255, 0)'
        self.initUI(backgrcolor)
        self.btnDec = QPushButton()
        #self.qList.setSelectionMode(QAbstractItemView.SingleSelection)
    def initUI(self, backgrcolor):
        k = 0
        for i, AE_name in enumerate(self.AE_list):
            if i != 0 and i % 5 == 0.0:
                k += 1
            self.dname = GetInfDev(AE_name + " :" + self.Ae_list['DES'][i])
            self.btnDec = QPushButton(self.dname.value, self)
            self.btnDec.setStyleSheet(backgrcolor)
            self.layout().addWidget(self.btnDec)
            self.btnDec.setObjectName("{}".format(self.dname.value))
            #self.btnDec.clicked.connect(self.on_click)
            self.btnDec.clicked.connect(self.changecolor)
            #self.btnDec.setStyleSheet("background-color :  green")
            self.btn.append(self.btnDec)
            self.hBOX[k].addWidget(self.btn[i])
            self.hBOX[k].addStretch(1)

        for i in range(k + 1):
            self.vBOX.addLayout(self.hBOX[i])

        self.client = MqttClient(self)
        self.client.stateChanged.connect(self.on_stateChanged)
        self.client.messageSignal.connect(self.on_messageSignal)

        self.client.hostname = IP
        self.client.connectToHost()

        self.vBOX.addWidget(self.text)
        self.setLayout(self.vBOX)
        self.setGeometry(700, 700, 750, 700)

    @QtCore.pyqtSlot(int)
    def on_stateChanged(self, state):
        if state == MqttClient.Connected:
            #print(state)
            self.client.subscribe(Topic)

    @QtCore.pyqtSlot(str)
    def on_messageSignal(self, msg):
        try:
            msg_in = json.loads(msg)
            if len(msg_in) > 30:
                DATA = msg_in
                if int(DATA['D-N']) == 1:
                    exec_iot = DATA['exec_iot']
                    AE_Status_Sub = DATA['AE_Status_Sub_Scube']
                    boot_time = DATA['boot_time']
                else:
                    exec_iot = DATA['exec_thyme']
                    AE_Status_Sub = DATA['AE_Status_Sub']
                    boot_time = DATA[' boot_time']
                L = str(DATA['D-ID'].strip())
                self.ldev = GetInfDev(None, str(DATA['D-ID'].strip()), str(DATA['current_datetime']),
                                 str(DATA['PF-IP'].strip()))
                if not self.ldev.LDev:
                    self.ldev.LDev = ['NONE']
                if not self.ldev.BDev:
                    self.ldev.BDev = ['NONE']
                if not self.ldev.DESdev:
                    self.ldev.DESdev = ['NONE']
                self.DES, AE_type, ITS, S_num, Administrator, M_NUM, Status, Dir, file, ftp_pw = MA.AE_seek(self.ldev.LDev, self.ldev.DESdev)
                #self.text.append('>> ' + self.ldev.LDev + ' ' + self.ldev.BDev + ' ' + self.DES + ' : Data Upload Complete!!!')
                print('>> ' + self.ldev.LDev + ' ' + self.ldev.BDev + ' ' + self.DES + ' : Data Upload Complete!!!')
                self.datas = pd.DataFrame([self.ldev.LDev + ' ' + self.ldev.BDev + ' ' + self.DES])
                with open(self.txtfilename, 'a', newline='\n') as self.fil:
                    self.datas.to_csv(self.fil, index=False, header=False)

        except ValueError:
            print("error: check the msg error")

    @pyqtSlot()
    def on_click(self):
        try:
            print(self.ldev.LDev)
            with open(self.txtfilename, 'rt') as file:
                reader = csv.reader(file, delimiter=',')  # good point by @boto
                for row in reader:
                    if str(row[0]).split(" ")[0] ==  self.sender().objectName().rsplit(" :",1)[0]:
                        self.text.append('Uploded data....>' +str(row)+' : Data!!!')
                    elif str(row[0]).split(" ")[0] != self.sender().objectName().rsplit(" :", 1)[0]:
                        self.text.append(self.sender().objectName() + '--->' + 'Data has not upload info yet!!!')
                        break
        except AttributeError:
            self.text.append(self.sender().objectName() + '>>>' + 'Data has not info yet!!!')

    @pyqtSlot()
    def changecolor(self):
      backgrcolor = 'background-color :  rgb(255, 0, 0)'
      self.initUI(backgrcolor)


    def closeEvent(self, event):
        os.remove(self.txtfilename)
        print("file daleted")

if __name__=='__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    form = Widget()
    form.show()
    sys.exit(app.exec_())
