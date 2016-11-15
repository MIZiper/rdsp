from PyQt4 import QtGui
import numpy as null_paintdevice
from rdsp.module import SignalContainer
import numpy as np

class InterceptionModule(SignalContainer):
    ModuleName = 'Interception'

    def configWindow(self):
        config = {
            'name':self.name,
            'trackSrc':self.parent.getTracksList()
        }
        cfgWin = InterceptionConfig(config)
        cfgWin.exec_()
        if cfgWin.result():
            self.processNow(cfgWin.getResult())
            return True
        return False

    def processNow(self, config):
        tracks = []
        self.name = config['name']

        for guid in config['tracks']:
            track = self.parent.getTrack(guid)
            (x,y) = track.getPlotData()
            idx0 = np.searchsorted(x,config['start'])
            idx1 = np.searchsorted(x,config['stop'])
            tracks.append({
                'name':track.name,
                'data':np.array([y[idx0:idx1]]),
                'config':track.config
            })

        self.addTracks(tracks)

class InterceptionConfig(QtGui.QDialog):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle('Interception Configuration')
        self.initUI()

    def initUI(self):
        config = self.config
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        lblName = QtGui.QLabel('Name')
        txtName = QtGui.QLineEdit(config['name'])

        lblStart = QtGui.QLabel('Start')
        lblStop = QtGui.QLabel('Stop')
        txtStart = QtGui.QDoubleSpinBox()
        txtStart.setMaximum(998.0)
        txtStop = QtGui.QDoubleSpinBox()
        txtStop.setMaximum(998.0)
        # init start/stop time from internal setting stored by range plugin

        btnTrack = QtGui.QCommandLinkButton('Add Track')
        btnTrack.clicked.connect(self.addTrack)
        tblTrack = QtGui.QTableWidget(0,1)
        tblTrack.setHorizontalHeaderLabels(['Track Name'])
        tblTrack.verticalHeader().sectionDoubleClicked.connect(self.removeTrack)
        self.track_table = tblTrack
        self.name_txt = txtName
        self.start_txt = txtStart
        self.stop_txt = txtStop

        layoutMain = QtGui.QVBoxLayout(self)
        layoutMain.aw(lblName).aw(txtName).aw(lblStart).aw(txtStart).aw(
            lblStop).aw(txtStop).aw(btnTrack).aw(tblTrack).aw(buttonBox)

    def addTrack(self):
        tt = self.track_table
        n = tt.rowCount()
        tt.setRowCount(n+1)

        cmbTracks = QtGui.QComboBox()
        tracks = [track['name'] for track in self.config['trackSrc']]
        cmbTracks.addItems(tracks)

        tt.setCellWidget(n,0,cmbTracks)

    def removeTrack(self, index):
        self.track_table.removeRow(index)

    def getResult(self):
        tt = self.track_table
        trackSrc = self.config['trackSrc']
        tracks = []
        for i in range(tt.rowCount()):
            tracks.append(trackSrc[tt.cellWidget(i,0).currentIndex()]['guid'])
        return {
            'tracks':tracks,
            'start':self.start_txt.value(),
            'stop':self.stop_txt.value(),
            'name':self.name_txt.text()
        }