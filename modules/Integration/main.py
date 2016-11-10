from PyQt4 import QtGui
from scipy import integrate
import numpy as np
from rdsp.module import SignalContainer

class IntegrationModule(SignalContainer):
    ModuleName = 'Integration'
    
    def configWindow(self):
        config = {
            'name':self.name,
            'trackSrc':self.parent.getTracksList()
        }
        cfgWin = IntegrationConfig(config)
        cfgWin.exec_()
        if cfgWin.result():
            self.processNow(cfgWin.getResult())
            return True
        return False

    def processNow(self, config):
        tracks = []
        self.name = config['name']
        
        for t in config['trackSet']:
            track = self.parent.getTrack(t['guid'])
            (x,y) = track.getPlotData()
            dt = y
            if t['type']=='td':
                for i in np.arange(t['order'])+1:
                    dt = integrate.cumtrapz(dt,x,initial=0)
                    dt -= np.polyval(np.polyfit(x,dt,1),x)
                    # dt -= np.polyval(np.polyfit(x,dt,i),x)
            else:
                N = dt.size
                freqs = np.fft.fftfreq(N,1/(track.config['bandwidth']*2.56))
                a = freqs*1j*2*np.pi
                fdt = np.fft.fft(dt)
                b = np.zeros(N,dtype='complex')
                b[1:N] = a[1:N]**(-t['order'])
                fdt *= b
                dt = np.real(np.fft.ifft(fdt))
                # dt -= np.polyval(np.polyfit(x,dt,t['order']),x)
            tracks.append({
                'name':track.name,
                'data':np.array([dt]),
                'config':track.config # should modify the unit
            })

        self.addTracks(tracks)

class IntegrationConfig(QtGui.QDialog):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle('Integration Configuration')
        self.initUI()

    def initUI(self):
        config = self.config
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        lblName = QtGui.QLabel('Name')
        txtName = QtGui.QLineEdit(config['name'])

        btnTrack = QtGui.QCommandLinkButton('Add Track')
        btnTrack.clicked.connect(self.addTrack)
        tblTrack = QtGui.QTableWidget(0,3)
        tblTrack.setHorizontalHeaderLabels(['Track Name','Order','Type'])
        tblTrack.verticalHeader().sectionDoubleClicked.connect(self.removeTrack)
        self.track_table = tblTrack
        self.name_txt = txtName

        layoutMain = QtGui.QVBoxLayout(self)
        layoutMain.aw(lblName).aw(txtName).aw(btnTrack).aw(tblTrack).aw(buttonBox)

    def addTrack(self):
        tt = self.track_table
        n = tt.rowCount()
        tt.setRowCount(n+1)

        cmbTracks = QtGui.QComboBox()
        tracks = [track['name'] for track in self.config['trackSrc']]
        cmbTracks.addItems(tracks)

        cmbType = QtGui.QComboBox()
        cmbType.addItems(('TD','FD'))

        cmbOrder = QtGui.QComboBox()
        cmbOrder.addItems(('1','2'))

        tt.setCellWidget(n,0,cmbTracks)
        tt.setCellWidget(n,1,cmbOrder)
        tt.setCellWidget(n,2,cmbType)

    def removeTrack(self, index):
        self.track_table.removeRow(index)

    def getResult(self):
        tt = self.track_table
        trackSrc = self.config['trackSrc']
        trackSet = []
        for i in range(tt.rowCount()):
            trackSet.append({
                'guid':trackSrc[tt.cellWidget(i,0).currentIndex()]['guid'],
                'order':tt.cellWidget(i,1).currentIndex()+1,
                'type':('td','fd')[tt.cellWidget(i,2).currentIndex()]
            })

        return {
            'name':self.name_txt.text(),
            'trackSet':trackSet
        }