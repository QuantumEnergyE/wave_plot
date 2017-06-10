# -*- coding: utf-8 -*-
import logging
import os
import sys
import matplotlib.pyplot as plt
import tempfile
import numpy as np
import wave
import subprocess
from PyQt4 import QtCore
from PyQt4 import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

point_per_second = 44100
up_interval = 1 # 每1s刷新一次页面
max_display = 44100*10 # 保留5s的记录

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%a, %d %b %Y %H:%M:%S',
    filename=os.path.join(os.path.dirname(sys.argv[0]), "wave_plot.log"),
    filemode='w'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.root.addHandler(console)


def run_shell(command):
    logging.info(command)
    cmd = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    for info in cmd.communicate():
        logging.info(info)


class WavePlot(object):
    def __init__(self, file):
        if not os.path.exists(file):
            raise Exception("file isn't exists!")
        self.fp = self.mp3_to_wav(file) if os.path.splitext(file)[-1] != ".wav" else wave.open(file)

    def __del__(self):
        if self.fp:
            self.fp.close()

    def __getattr__(self, item):
        pass

    def mp3_to_wav(self, file):
        try:
            self.tmp_wav = os.path.join(tempfile.mkdtemp(), os.path.basename(file).replace(".mp3", ".wav") )
            command = "ffmpeg -i %s %s" % (file, self.tmp_wav)
            run_shell(command)
            if os.path.exists(self.tmp_wav):
                return wave.open(self.tmp_wav)
            os.remove(self.tmp_wav)
        except Exception as ex:
            logging.error(ex)
            return None

    def get_data(self):
        if not self.fp:
            logging.info("no fp!")
            return {}
        params = self.fp.getparams()
        nchannels, sampwidth, framerate, nframes = params[:4]
        global point_per_second
        point_per_second = framerate
        str_data = self.fp.readframes(nframes)
        wave_data = np.fromstring(str_data, dtype=np.short)
        wave_data.shape = -1, nchannels
        wave_data = wave_data.T
        time = np.arange(0, nframes) * (1.0 / framerate)
        return {"x":time, 'ys':wave_data}

    @staticmethod
    def draw(**kwargs):
        if not kwargs:
            logging.info("no data!")
            return
        time = kwargs['x']
        wave_data = kwargs['ys']
        plt.subplot(211)
        plt.plot(time, wave_data[0])
        plt.subplot(212)
        plt.plot(time, wave_data[1], c="g")
        plt.show()


class Wave(QtGui.QDialog):
    def __init__(self, data, parent=None):
        super(Wave, self).__init__(parent)
        self.setFixedSize(1080, 720)

        self.data = data
        self.flag = 0
        self.pos = 0
        self.dy_start = 0
        self.times = len(self.data['x'])
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.button = QtGui.QPushButton('start')
        self.button.clicked.connect(self.control)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(self.button)
        self.setLayout(layout)

        self.timer=QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.plot)
        self.timer.start(up_interval*1000)

    def control(self):
        self.flag = 0 if self.flag else 1
        if self.flag:
            self.button.setText("stop")
        else:
            self.button.setText("start")

    def plot(self):
        if self.flag:
            end = self.pos + up_interval*point_per_second
            if end - self.dy_start > max_display:
                self.ax.cla()
                self.dy_start = self.pos
            self.ax.plot(self.data['x'][self.pos:end], self.data['ys'][0][self.pos:end])
            self.ax.set_xlabel("Time(s)")
            self.ax.set_ylabel("Hz")
            self.pos = self.pos + up_interval*point_per_second
            if not self.pos > self.times:
                self.canvas.draw()


if __name__ == '__main__':
    wp = WavePlot("D:/1.mp3")
    data = wp.get_data()
    app = QtGui.QApplication(sys.argv)
    wave = Wave(data)
    wave.show()
    sys.exit(app.exec_())
