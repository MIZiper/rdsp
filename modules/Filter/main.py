from PyQt4 import QtGui
from scipy import signal
import numpy as np
from rdsp.module import SignalContainer

class FilterModule(SignalContainer):
    ModuleName = 'Filter'

    def __init__(self, guid, name, parent):
        super().__init__(guid, name, parent)
        self.name = name+' - '+parent.name

    def configWindow(self):
        config = {
            'name':self.name,
            'trackSrc':self.parent.getTracksList()
        }
        cfgWin = FilterConfig(config)
        cfgWin.exec_()
        if cfgWin.result():
            self.processNow(cfgWin.getResult())
            return True
        return False

    def processNow(self, config):
        tracks = []

        # wp, ws: pass band freq & stop band freq
        # gp, gs: maximum loss in passband & minimum attenuation in stopband (dB)
        # N, Wn: order & dont know what
        #-> N, Wn = buttord(wp/(sr/2),ws/(sr/2),gp,gs)
        # b, a: dont know what & dont either
        #-> b, a = butter(N,Wn)
        #-> y = filtfilt(b,a,x)
        # in fact the Wn is close to wp/(sr/2)
        # so how to determine the order, for default setting?
        if config['type'] in ('lowpass','highpass'):
            w = config['freq']
        else:
            w = np.array(config['band'])
        
        for guid in config['tracks']:
            t = self.parent.getTrack(guid)
            Wn = w/(t.config['bandwidth']*2.56/2)
            b, a = signal.butter(config['order'],Wn,config['type'])
            r = signal.filtfilt(b,a,t.getData()[0])
            tracks.append({
                'name':t.name,
                'data':np.array([r]),
                'config':t.config
            })

        self.addTracks(tracks)
        

class FilterConfig(QtGui.QDialog):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle('Filter Configuration')
        self.initUI()

    def initUI(self):
        config = self.config
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        lblName = QtGui.QLabel('Name')
        txtName = QtGui.QLineEdit(config['name'])

        lblOrder = QtGui.QLabel('Order')
        txtOrder = QtGui.QSpinBox()
        txtOrder.setRange(0,20)
        txtOrder.setSingleStep(1)
        txtOrder.setValue(1)

        def visibleFuncGen(widgets):
            def closure(visibilities):
                for i in range(len(widgets)):
                    widgets[i].setVisible(visibilities[i])
            return closure

        grpFreq = QtGui.QGroupBox('Frequency')
        cmbBand = QtGui.QComboBox()
        cmbBand.addItems(['Low Pass','High Pass','Band Pass','Band Stop'])
        lblCrtFreq = QtGui.QLabel('Critical Frequency')
        txtCrtFreq = QtGui.QDoubleSpinBox()
        txtCrtFreq.setMaximum(1000.0)
        lblLowFreq = QtGui.QLabel('Low Frequency')
        txtLowFreq = QtGui.QDoubleSpinBox()
        txtLowFreq.setMaximum(1000.0)
        lblHighFreq = QtGui.QLabel('High Frequency')
        txtHighFreq = QtGui.QDoubleSpinBox()
        txtHighFreq.setMaximum(1000.0)
        wow = visibleFuncGen((lblCrtFreq,lblLowFreq,lblHighFreq,txtCrtFreq,txtLowFreq,txtHighFreq))
        wow((True,False,False)*2)
        cmbBand.currentIndexChanged.connect(
            lambda x: wow((True,False,False)*2) if x<2 else wow((False,True,True)*2)
        )
        
        layoutGrp = QtGui.QVBoxLayout(grpFreq)
        layoutGrp.aw(cmbBand).aw(
            lblCrtFreq).aw(txtCrtFreq).aw(lblLowFreq).aw(
            txtLowFreq).aw(lblHighFreq).aw(txtHighFreq)

        btnTrack = QtGui.QCommandLinkButton('Add Track')
        btnTrack.clicked.connect(self.addTrack)
        tblTrack = QtGui.QTableWidget(0,1)
        tblTrack.setHorizontalHeaderLabels(['Track Name'])
        tblTrack.verticalHeader().sectionDoubleClicked.connect(self.removeTrack)
        self.track_table = tblTrack
        self.band_cmb = cmbBand
        self.crtFreq = txtCrtFreq
        self.lowFreq = txtLowFreq
        self.highFreq = txtHighFreq
        self.name_txt = txtName
        self.order_txt = txtOrder

        layoutMain = QtGui.QVBoxLayout(self)
        layoutMain.aw(lblName).aw(txtName).aw(
            lblOrder).aw(txtOrder).aw(grpFreq).aw(btnTrack).aw(tblTrack).aw(buttonBox)

    def addTrack(self, guid=None):
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
        idx = self.band_cmb.currentIndex()

        return {
            'name':self.name_txt.text(),
            'order':self.order_txt.value(),
            'type':('lowpass','highpass','bandpass','bandstop')[idx],
            'band':(self.lowFreq.value(),self.highFreq.value()),
            'freq':self.crtFreq.value(),
            'tracks':tracks
        }