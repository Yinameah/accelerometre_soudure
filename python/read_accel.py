#!/usr/bin/python

# Si jamais, pour écrire des nombre sur le port série, il faut utiliser :
# ser.write([3]) ! La liste [3] est considérée comme un 11 binaire...
import os
import sys
import time
import glob
import random

import serial
import csv
from datetime import datetime

from PyQt5.QtWidgets import QApplication, QDialog, QGridLayout, QPushButton, QTextEdit, QSpacerItem, QSizePolicy, QMainWindow, QWidget, QComboBox, QCheckBox, QVBoxLayout, QHBoxLayout, QFileDialog, QVBoxLayout, QLabel, QSpacerItem, QInputDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
import icons_rc

import pyqtgraph as pg

class EditableInfiniteLine(pg.InfiniteLine):

    labelChanged = pyqtSignal(str, int)
    
    def __init__(self, pos=None, angle=90, pen=None, movable=False, bounds=None,
                hoverPen=None, label=None, labelOpts=None, name=None):
        super().__init__(pos, angle, pen, movable, bounds, hoverPen, label, labelOpts, name)

        # Store relevant time mark sample_number
        self.tm_sample_nbr = 0

    def mouseDoubleClickEvent(self, evt):
        mark_txt, ok = QInputDialog.getText(self.parent(), 'Time Mark',
                                            'Enter new name for this Time Mark')

        if ok :
            self.labelChanged.emit(mark_txt, self.tm_sample_nbr)


class ExploreGraphWindow(QDialog):

    def __init__(self, filename, parent=None):
        super().__init__(parent)

        self.filename = filename
        # Read CSV file, store_data
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            self.samples = dict()
            self.samples['s'] = []
            self.samples['x'] = []
            self.samples['y'] = []
            self.samples['z'] = []
            self.samples['t'] = []
            self.samples['l'] = []
            for row in reader:
                self.samples['s'].append(float(row['Time [s]']))
                self.samples['x'].append(int(row['X accel']))
                self.samples['y'].append(int(row['Y accel']))
                self.samples['z'].append(int(row['Z accel']))
                self.samples['t'].append(int(row['Temp']))
                self.samples['l'].append(row['Label'])
    
        self.display_details = dict(x = False, y = False, z = False, t = False)

        self.setWindowTitle('Mesure')
        self.setStyleSheet('background:black')
        self.setModal(True)
        self.setWindowFlags(Qt.Window)

        # Plot Widget  ## giving the plots names allows us to link their axes together
        self.pw = pg.PlotWidget(name='Plot')
        self.pw_zoom = pg.PlotWidget(name='Plot_Zoom')

        self.pw.setLabel('bottom', 'Time', 's')
        self.pw_zoom.setLabel('bottom', 'Time', 's')

        # Time Mark !
        self.time_marks = dict() # {'numero de sample':'label', }
        # On récupère les labels, et affiche les barres
        for i, label in enumerate(self.samples['l']):
            if label != '':
                self.time_marks[i] = label
                tm_line = pg.InfiniteLine(angle=90, movable=False, pen='aaa')
                # Use custom line that can be edited
                tm_line2 = EditableInfiniteLine(angle=90, movable=False, pen='aaa')
                tm_line2.labelChanged.connect(self.update_label)
                tm_line2.tm_sample_nbr = i
                self.pw.addItem(tm_line)
                self.pw_zoom.addItem(tm_line2)
                tm_line.setPos(self.samples['s'][i])
                tm_line2.setPos(self.samples['s'][i])

        # Labels with data
        w_label = QWidget()
        w_label.setLayout(QHBoxLayout())
        w_label.layout().addStretch()
        self.DataLabel = dict()
        for k in ['x', 'y', 'z', 't']:
            self.DataLabel[k] = QLabel()
            self.DataLabel[k].setStyleSheet('color:grey')
            self.DataLabel[k].setText('Infos')
            w_label.layout().addWidget(self.DataLabel[k])
        # Time Marks display
        self.timeMarkLabel = QLabel()
        self.timeMarkLabel.setStyleSheet('font-size:16px; color:grey')
        w_label.layout().addWidget(self.timeMarkLabel)

        # Buttons
        self.ShowXDataBox = QCheckBox('X Data')
        self.ShowXDataBox.setStyleSheet('color:grey')
        self.ShowXDataBox.stateChanged.connect(self.show_x_data)
        self.ShowXDataBox.setChecked(True)
        self.ShowYDataBox = QCheckBox('Y Data')
        self.ShowYDataBox.stateChanged.connect(self.show_y_data)
        self.ShowYDataBox.setStyleSheet('color:grey')
        self.ShowZDataBox = QCheckBox('Z Data')
        self.ShowZDataBox.stateChanged.connect(self.show_z_data)
        self.ShowZDataBox.setStyleSheet('color:grey')
        self.ShowTDataBox = QCheckBox('Temp')
        self.ShowTDataBox.setStyleSheet('color:grey')
        self.ShowTDataBox.stateChanged.connect(self.show_t_data)

        # Layout
        w_butt = QWidget()
        ButtonBox = QVBoxLayout(w_butt)
        ButtonBox.addWidget(self.ShowXDataBox)
        ButtonBox.addWidget(self.ShowYDataBox)
        ButtonBox.addWidget(self.ShowZDataBox)
        ButtonBox.addWidget(self.ShowTDataBox)

        w_graph = QWidget()
        graph_layout = QVBoxLayout(w_graph)
        graph_layout.addWidget(w_label)
        graph_layout.addWidget(self.pw_zoom)
        graph_layout.addWidget(self.pw)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(w_butt)
        self.layout().addWidget(w_graph)

        # PG CONFIG
        # Région de zoom
        self.region = pg.LinearRegionItem()
        self.region.setZValue(50) # Pour que ce soit devant j'imagine
        self.region.sigRegionChanged.connect(self.update_zoom)
        self.region.setRegion([1, 6])

        self.pw.addItem(self.region, ignoreBounds=True)
        #self.pw_zoom.setAutoVisible(y=True)

        self.pw_zoom.sigRangeChanged.connect(self.update_region)
        #self.region.setRegion([5, 10])

        # cross hair
        self.vline = pg.InfiniteLine(angle=90, movable=False)
        self.hline = pg.InfiniteLine(angle=0, movable=False)
        self.pw_zoom.addItem(self.vline, ignoreBounds=True)
        self.pw_zoom.addItem(self.hline, ignoreBounds=True)

        self.pw_zoom.scene().sigMouseMoved.connect(self.mouseMoved)

        # On récupère la ViewBox pour mapper la croix correctement
        self.vb = self.pw_zoom.getViewBox()

        self.show()

    def update_label(self, txt, sample_no):
        """
            React to custom InfiniteLine Signal
            Update label, store in csv ...
        """
        # rename in local variable
        self.samples['l'][sample_no] = txt
        self.time_marks[sample_no] = txt

        # Open file and rewrite all
        with open(self.filename, 'w', encoding="utf8") as csvfile:

            c = csv.writer(csvfile)

            c.writerow(['Time [s]', 'X accel', 'Y accel', 'Z accel', 'Temp', 'Label'])
            #for sample in self.samples:
            for i in range(len(self.samples['s'])):
                #print(type(self.samples['s'][i]))
                row = [ self.samples['s'][i],
                        self.samples['x'][i],
                        self.samples['y'][i],
                        self.samples['z'][i],
                        self.samples['t'][i],
                        self.samples['l'][i] ]
                c.writerow(row)

    def mouseMoved(self, pos):
        """
            Appellé au déplacement de la souris sur le plot zoomé
            Met à jour la position de la croix
        """

        # Map mouse position to graph and move cross
        mousePoint = self.vb.mapSceneToView(pos)
        self.vline.setPos(mousePoint.x())
        self.hline.setPos(mousePoint.y())

        # Select closest sample to actual position
        index = float(mousePoint.x())
        for no_sample, s in enumerate(self.samples['s']):
            if s > index:
                break

        # display relevant value label
        data_label = ''
        for k, color in [('x','red'), ('y','green'), ('z','blue'), ('t', 'yellow')]:
            self.DataLabel[k].hide()
            if self.display_details[k]:
                data_label = f"{k} = {self.samples[k][no_sample]}  "
                self.DataLabel[k].setText(data_label)
                self.DataLabel[k].setStyleSheet(f"color:{color}; font-size:16px")
                self.DataLabel[k].show()

        # display time mark value
        no_sample_with_mark = None
        for sample_target in self.time_marks.keys():
            if abs(sample_target - no_sample) < 50 :
                no_sample_with_mark = sample_target
                break
        if no_sample_with_mark is not None:
            self.timeMarkLabel.setText(self.time_marks[no_sample_with_mark])
            self.timeMarkLabel.show()
        else:
            self.timeMarkLabel.hide()

    def update_zoom(self):
        """
            Mise à jour du Range du plot zoomé quand on bouge la région dans l'autre plot
        """
        self.region.setZValue(10)
        minX, maxX = self.region.getRegion()
        self.pw_zoom.setXRange(minX, maxX, padding=0)

    def update_region(self, sender, viewRange):
        """
            Mise à jour de la région dans le plot principal quand on navigue dans le plot zoomé
            Reçoit l'émetteur (probablement), en l'occurence le PlotWidget
            Et le viewRange, sous forme de list [[x,x],[y,y]]
        """
        # On récupère le range
        rgn = viewRange[0]
        # On l'assigne à la région
        self.region.setRegion(rgn)

    def show_x_data(self):
        """
            Obvious
        """
        if self.ShowXDataBox.isChecked():
            self.x_z_graphItem = self.pw_zoom.plot(self.samples['s'], self.samples['x'], pen = 'r')
            self.x_graphItem = self.pw.plot(self.samples['s'], self.samples['x'], pen = 'r')
            self.display_details['x'] = True
        else:
            self.pw_zoom.removeItem(self.x_z_graphItem)
            self.pw.removeItem(self.x_graphItem)
            self.display_details['x'] = False

    def show_y_data(self):
        """
            Obvious
        """
        if self.ShowYDataBox.isChecked():
            self.z_y_graphItem = self.pw_zoom.plot(self.samples['s'], self.samples['y'], pen = 'g')
            self.y_graphItem = self.pw.plot(self.samples['s'], self.samples['y'], pen = 'g')
            self.display_details['y'] = True
        else:
            self.pw_zoom.removeItem(self.z_y_graphItem)
            self.pw.removeItem(self.y_graphItem)
            self.display_details['y'] = False

    def show_z_data(self):
        """
            Obvious
        """
        if self.ShowZDataBox.isChecked():
            self.z_z_graphItem = self.pw_zoom.plot(self.samples['s'], self.samples['z'], pen = 'b')
            self.z_graphItem = self.pw.plot(self.samples['s'], self.samples['z'], pen = 'b')
            self.display_details['z'] = True
        else:
            self.pw_zoom.removeItem(self.z_z_graphItem)
            self.pw.removeItem(self.z_graphItem)
            self.display_details['z'] = False

    def show_t_data(self):
        """
            Obvious
        """
        if self.ShowTDataBox.isChecked():
            self.z_t_graphItem = self.pw_zoom.plot(self.samples['s'], self.samples['t'], pen = 'y')
            self.t_graphItem = self.pw.plot(self.samples['s'], self.samples['t'], pen = 'y')
            self.display_details['t'] = True
        else:
            self.pw_zoom.removeItem(self.z_t_graphItem)
            self.pw.removeItem(self.t_graphItem)
            self.display_details['t'] = False


class LiveGraphWindow(QDialog):
    """
        Fenêtre de mesure "live"
    """
    def __init__(self, ser, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Mesure')
        self.ser = ser

        # Plot Widget  ## giving the plots names allows us to link their axes together
        self.pw = pg.PlotWidget(name='Plot1')
        self.pw.setLabel('bottom', 'Time', 's')

        # Buttons
        self.MarkTimeButton = QPushButton('Set time mark')
        self.MarkTimeButton.clicked.connect(self.set_time_mark)
        self.CloseAndSaveButton = QPushButton('Close and Save')
        self.CloseAndSaveButton.clicked.connect(self.save_data)

        # Layout
        self.setLayout(QGridLayout())
        self.layout().addWidget(self.pw, 0, 0, 1, 3)
        self.layout().addWidget(self.MarkTimeButton, 1, 0, 1, 1)
        self.layout().addWidget(self.CloseAndSaveButton, 1, 2, 1, 1)

        # Options
        self.setModal(True)

        self.show()

        # "Clean" Serial port
        self.ser.flushInput()
        self.ser.readline()

        # Variables de stockage des données
        self.millis_ref_start = 0 # allow to begin at 0
        self.samples_data = [] # [[s, x, y, z, t, l], ]

        # Store date to label csv file
        self.aquisition_date = str(datetime.now())

        # Launch timer for aquisition
        self.timercount = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(50)

        # Launch timer for auto-save
        #self.timer_save = QTimer()
        #self.timer.timeout.connect(self.auto_save)
        #self.timer.start(3000)

    def update_graph(self):
        """
            Periodically get and plot data
        """
        x_mesure_burst = []
        y_mesure_burst = []
        z_mesure_burst = []
        t_mesure_burst = []
        s_mesure_burst = []

        while self.ser.in_waiting > 0:
            Rx = self.ser.readline()

            val= Rx.split(bytes('\r'.encode()))[0]

            message = val.decode()

            if 'MSG' not in message:

                millis, xdata, ydata, zdata, tdata = message.split(':')

                # Should only occur on first loop
                if self.millis_ref_start == 0:
                    self.millis_ref_start = millis

                x_mesure_burst.append(int(xdata))
                y_mesure_burst.append(int(ydata))
                z_mesure_burst.append(int(zdata))
                t_mesure_burst.append(int(tdata))
                s_mesure_burst.append((int(millis)-int(self.millis_ref_start))/1000)

        # Put Data in list for saving
        raw_data_burst = []
        for i in range(len(s_mesure_burst)):
            raw_data_burst.append([ s_mesure_burst[i], 
                                    x_mesure_burst[i], 
                                    y_mesure_burst[i],
                                    z_mesure_burst[i],
                                    t_mesure_burst[i],
                                    ''])
        self.samples_data.extend(raw_data_burst)

        # Plot Data
        self.pw.plot(s_mesure_burst, x_mesure_burst, pen='r')
        self.pw.plot(s_mesure_burst, y_mesure_burst, pen='g')
        self.pw.plot(s_mesure_burst, z_mesure_burst, pen='b')
        self.pw.plot(s_mesure_burst, t_mesure_burst, pen='y')

        self.timercount += 1
        if self.timercount > 30 :
            self.timercount = 0
            self.save_data(True)

    def closeEvent(self, evt):
        # Stop aquiring data
        self.timer.stop()

    def set_time_mark(self):
        """
            Record time of the click display bar and store that info
        """
        # Get last sample
        last_sample = self.samples_data[-1]

        # Open Dialog
        mark_txt, ok = QInputDialog.getText(self, 'Time Mark', 'Enter name for Time Mark')

        if ok:
            if mark_txt != '':
                last_sample[-1] = mark_txt
            else:
                last_sample[-1] = 'Time Mark'

    def save_data(self, auto_save):
        """
            When closing mesure windows, save data to csv
        """
        # Create csv file
        csvfolder = 'aquisitions'
        if not os.path.exists(csvfolder):
            os.makedirs(csvfolder)
        csvfile = os.path.join(csvfolder, self.aquisition_date + '.csv')

        with open(csvfile, 'w', encoding="utf8") as csvfile:

            c = csv.writer(csvfile)

            c.writerow(['Time [s]', 'X accel', 'Y accel', 'Z accel', 'Temp', 'Label'])
            for sample in self.samples_data:
                c.writerow(sample)

        if not auto_save:
            self.close_win()

    def close_win(self):
        self.close()


class MainWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Accelerometer')

        # Button
        self.SerConnectButton = QPushButton()
        self.SerConnectButton.setText("Open serial connection")
        self.SerConnectButton.pressed.connect(self.open_serial)

        self.SerialPortCombo = QComboBox()

        self.RefreshSerialButton = QPushButton()
        reloadIcon = QIcon(':/icons/reload.png')
        self.RefreshSerialButton.setIcon(reloadIcon)
        self.RefreshSerialButton.clicked.connect(self.refresh_serial)

        self.BeginNewMesureButton = QPushButton()
        self.BeginNewMesureButton.setText("Begin new mesure")
        self.BeginNewMesureButton.clicked.connect(self.begin_mesure)

        self.OpenMesureBututon = QPushButton()
        self.OpenMesureBututon.setText("Open mesure")
        self.OpenMesureBututon.clicked.connect(self.open_mesure)

        # Layout
        self.mainLayout = QGridLayout()
        self.setLayout(self.mainLayout)

        self.mainLayout.addWidget(self.RefreshSerialButton, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.SerialPortCombo, 0, 1, 1, 1)
        self.mainLayout.addWidget(self.SerConnectButton, 0, 2, 1, 1)

        self.mainLayout.addWidget(self.BeginNewMesureButton, 1, 0, 1, 3)
        self.mainLayout.addWidget(self.OpenMesureBututon, 2, 0, 1, 3)

        # Init de la variable du port série et populate serial port list
        self.ser = serial.Serial()
        self.ser.baudrate = 115200;
        self.refresh_serial()

        self.show()

        # AUTO CONNECT FOR TESTS
        #self.open_serial()
        #self.begin_mesure()
        #self.open_mesure()


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
            time.sleep(2)

            self.SerConnectButton.setStyleSheet("background-color:green")

        except serial.SerialException:

            if not self.ser.isOpen():
                self.SerConnectButton.setStyleSheet("background-color:red")

    def begin_mesure(self):
        """
            Open Mesure Window and start aquiring
        """
        if self.ser.isOpen():
            LiveGraphWin = LiveGraphWindow(self.ser, self)


    def open_mesure(self):
        """
            Open a mesure already recorded
        """
        # Return tuple('filename','type')
        filename = QFileDialog.getOpenFileName(
                            self,
                            "Open CSV", 
                            "aquisitions/", 
                            "CSV Files (*.csv)")

        #filename = []
        #filename.append('/home/aurelien/sketchbook/arduino/accelerometre_pour_soudure/aquisitions/test.csv')
        if filename[0] != '':
            ExploreGraphWin = ExploreGraphWindow(filename[0], self)
        
            


if __name__ == "__main__":
    
    app = QApplication(sys.argv)

    win = MainWindow()

    try:
        app.exec_()
    finally:
        win.ser.close()



