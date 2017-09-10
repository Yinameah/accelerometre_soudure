#!/usr/bin/python

# Si jamais, pour écrire des nombre sur le port série, il faut utiliser :
# ser.write([3]) ! La liste [3] est considérée comme un 11 binaire...
import os
import sys
import glob
import random

import serial
import csv
from multiprocessing import Process, Pipe
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt

import icons_rc
from PyQt5.QtWidgets import QApplication, QDialog, QGridLayout, QPushButton, QTextEdit, QSpacerItem, QSizePolicy, QMainWindow, QWidget, QComboBox, QCheckBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Accelerometer')

        self.mainLayout = QGridLayout()
        mainWidget = QWidget(self)
        mainWidget.setLayout(self.mainLayout)
        self.setCentralWidget(mainWidget)

        self.SerConnectButton = QPushButton()
        self.SerConnectButton.setText("Open serial connection")
        self.SerConnectButton.clicked.connect(self.open_serial)

        self.SerialPortCombo = QComboBox()

        self.RefreshSerialButton = QPushButton()
        reloadIcon = QIcon(':/icons/reload.png')
        self.RefreshSerialButton.setIcon(reloadIcon)
        self.RefreshSerialButton.clicked.connect(self.refresh_serial)

        self.AquisitionCheckBox = QCheckBox()
        self.AquisitionCheckBox.setText('Record Data')
        self.AquisitionCheckBox.stateChanged.connect(self.on_aquisition_toggeled)

        self.BeginNewMesureButton = QPushButton()
        self.BeginNewMesureButton.setText("Begin new mesure")


        self.mainLayout.addWidget(self.RefreshSerialButton, 0, 0)
        self.mainLayout.addWidget(self.SerialPortCombo, 0, 1)
        self.mainLayout.addWidget(self.SerConnectButton, 0, 2)

        self.mainLayout.addWidget(self.AquisitionCheckBox, 1, 1)
        self.mainLayout.addWidget(self.BeginNewMesureButton, 1, 2)

        # Init de la variable du port série et populate serial port list
        self.ser = serial.Serial()
        self.ser.baudrate = 115200;
        self.refresh_serial()

        # Init des variables de stockage de mesure
        self.current_mesures = []

        self.show()



    def refresh_serial(self):
        """ Lists serial port names
            :raises EnvironmentError:
                On unsupported or unknow platforns
            :returns:
                A list of the serial ports available on te system
        """

        # Empty list
        for i in range(self.SerialPortCombo.count()):
            self.SerialPortCombo.removeItem(0)

        # Look for usable serial path
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass

        # Close serial port in case ...
        self.ser.close()
        # Reset button color
        self.SerConnectButton.setStyleSheet("background:")
        # Reset checkboxState
        self.AquisitionCheckBox.setCheckState(False)

        # Populate list
        for i, port in enumerate(result):
            self.SerialPortCombo.insertItem(i, port)

    def open_serial(self):
        """
            Open serial based on ComboBox value
            Button color change if it goes well/wrong
        """
        # First close if it's already open
        self.ser.close()
        self.ser.port = self.SerialPortCombo.currentText()

        try:

            self.ser.open()

            self.SerConnectButton.setStyleSheet("background-color:green")

        except serial.SerialException:

            if not self.ser.isOpen():
                self.SerConnectButton.setStyleSheet("background-color:red")

    def on_aquisition_toggeled(self, checked):
        """
            Start recording data in another process
        """

        if self.AquisitionCheckBox.isChecked():
            if self.ser.isOpen():
                self.serial_process = Process(target=self.bg_reading_serial) 
                self.serial_process.start()
            else:
                self.AquisitionCheckBox.setCheckState(False)
        else:
            # Try to terminate process
            try:
                self.serial_process.terminate()
            except AttributeError:
                print("Pas de processus à terminer ...")


    def bg_reading_serial(self):
        # Empty serial buffer
        self.ser.flushInput()
        # Ignore first line (often not clean, no idea why)
        self.ser.readline()


        while True:
            Rx = self.ser.readline()

            val= Rx.split(bytes('\r'.encode()))[0]

            message = val.decode()

            #millis, xdata, ydata, zdata, tdata = message.split(':')
            mesure = message.split(':')
            print(mesure)
            # On peut par récuperer ça simplement c'est dans un autre process
            #self.current_mesures.append(mesure)

        
def graph(x, y):
    aquisition_date = str(datetime.now())

    csvfolder = 'aquisitions'
    if not os.path.exists(csvfolder):
        os.makedirs(csvfolder)
    csvfile = os.path.join(csvfolder, aquisition_date + '.csv')

    with open(csvfile, 'w', encoding="utf8") as csvfile:

        c = csv.writer(csvfile)

        for k, xi in enumerate(x):
            c.writerow([k, xi, y[k]])

    plt.figure(str(datetime.now()))
    plt.plot(x, y)
    plt.show()



def collect_serial_data():
    mesures = []
    data = None

    with open_serial() as ser:
        print(ser)

        # Première ligne pourrie, no idea why
        ser.readline()

        while len(mesures) < 1000:
            rx = ser.readline()

            val= rx.split(bytes('\r'.encode()))[0]

            message = val.decode()


            if not 'MSG' in message :
                data = message.split(':')

                mesures.append(data)




    x = [m[0] for m in mesures]
    print(x)
    y = [m[1] for m in mesures]

    p = Process(target=graph, args=(x, y))
    p.start()

    print(ser)


if __name__ == "__main__":
    
    app = QApplication(sys.argv)

    win = MainWindow()

    app.exec_()

    win.serial_process.terminate()
    win.ser.close()



