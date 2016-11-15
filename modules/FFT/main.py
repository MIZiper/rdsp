from rdsp import gl
from PyQt4 import QtGui
from guiqwt.plot import ImageWidget
from guiqwt.builder import make
from rdsp.widgets import DisplayRangePicker
from rdsp.module import ModuleType, ModuleBase
import numpy as np

class FFTModule(ModuleBase):
    ModuleName = 'FFT'
    ContextMenu = [
        {'title':'Process', 'action':'processNow'},
        {'title':'Config', 'action':'setConfig'},
        {'title':'Delete', 'action':'delete'}
    ]
    def __init__(self, guid, name, parent, processed=False):
        super().__init__(guid,name,parent)
        self.tracks = []
        self.freqs = []
        self.config = {
            'lines':1000,
            'overlap':70
        }
        self.result = None
        self.resultLoaded = False
        self.processed = processed

    def getResult(self):
        if not self.resultLoaded:
            self.result = gl.projectManager.loadResult(self.guid)[0]
            self.resultLoaded = True
        return self.result

    def getFreqData(self, guid):
        if self.processed:
            result = self.getResult()
            return result[guid]
        return {}

    def configWindow(self, config=None):
        if not config:
            config = {
                'name': self.name,
                'lines':1000,
                'overlap':70,
                'trackSrc':self.parent.getTracksList(),
                'tracks':[]
            }

        cfgWin = FFTConfig(config)
        cfgWin.exec_()
        if cfgWin.result():
            self.parseConfig(cfgWin.getResult())
            return True
        return False

    def getProperty(self):
        return {
            'Lines':self.config['lines'],
            'Overlap':self.config['overlap']
        }

    def parseConfig(self, config):
        if 'name' in config:
            self.name = config['name']
        self.config = {
            'lines':config['lines'],
            'overlap':config['overlap']
        }
        self.tracks = [
            self.parent.getTrack(guid) for guid in config['tracks']
        ]
        if 'freqs' in config:
            self.freqs = [
                FFTFreqModule(guid, self.parent.getTrack(guid).name, self) for guid in config['freqs']
            ]

    def getListConfig(self):
        config = {
            'type':self.ModuleName,
            'name':self.name,
            'object':self,
            'sub':[freq.getListConfig() for freq in self.freqs]
            # freqs not saved and the info are stored in npy, so need to save to file?
        }
        return config

    def getFileConfig(self):
        config = {
            'type':self.ModuleName,
            'guid':self.guid,
            'name':self.name,
            'processed':self.processed,
            'config':{
                'tracks':[track.guid for track in self.tracks],
                'lines':self.config['lines'],
                'overlap':self.config['overlap'],
                'freqs':[freq.guid for freq in self.freqs]
            }
        }
        return config

    def setConfig(self):
        # cfg = self.config
        cfg = self.getFileConfig()['config']
        cfg['name'] = self.name
        cfg['trackSrc'] = self.parent.getTracksList()
        if self.configWindow(cfg):
            # self.parent.refresh()
            gl.projectManager.saveProject()

    def delete(self):
        self.parent.removeProcess(self)
        if self.processed:
            gl.projectManager.removeResult(self.guid)
            
    def processNow(self):
        cfg = self.config

        Nw = cfg['lines'] * 2.56
        win = np.hanning(Nw)
        ols = np.int(Nw*(1-cfg['overlap']/100)) # OverLapStep

        result = {}
        self.freqs.clear()
        for track in self.tracks:
            track_data = track.getData()[0]
            r = {
                'bandwidth':track.config['bandwidth'],
                'overlap':cfg['overlap'],
                'data':None
                # 'Nw'
            }
            N = track_data.size
            olt = np.floor((N-Nw)/ols)+1 # OverLapTimes
            stride = track_data.strides[0]
            
            mat = np.lib.stride_tricks.as_strided(track_data, shape=(olt,Nw), strides=(stride*ols,stride))
            mat_mean = mat.mean(axis=1).reshape(olt,1)
            mat_dcLess = mat - mat_mean
            mat_dcLess *= win
            
            mat_result = np.fft.fft(mat_dcLess)
            mat_result_half = mat_result[:,:Nw/2]

            # mat_amp = 2*2*np.abs(mat_result_half)/Nw # restore from window and fft
            # mat_agl = np.angle(mat_result_half, deg=True)
            r['data'] = 2*mat_result_half/Nw*2 # since the complex contain amp/agl info
            result[track.guid] = r
            
            f = FFTFreqModule(track.guid, track.name, self)
            self.freqs.append(f)

        gl.projectManager.saveResult(self.guid, [result])
        self.result = result

        self.processed = True
        self.resultLoaded = True
        self.parent.refresh()

class FFTConfig(QtGui.QDialog):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle('FFT Configuration')
        self.initUI()

    def initUI(self):
        config = self.config
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        lblName = QtGui.QLabel('Name')
        txtName = QtGui.QLineEdit(config['name'])

        lblLines = QtGui.QLabel('Lines')
        txtLines = QtGui.QSpinBox()
        txtLines.setRange(1000,50000)
        txtLines.setSingleStep(1000)
        txtLines.setValue(config['lines'])

        lblWindow = QtGui.QLabel('Window')
        # cmbWindow = QtGui.QComboBox()

        lblOverlap = QtGui.QLabel('Overlap (%)')
        txtOverlap = QtGui.QSpinBox()
        txtOverlap.setRange(0,100)
        txtOverlap.setSingleStep(1)
        txtOverlap.setValue(config['overlap'])

        btnTrack = QtGui.QCommandLinkButton('Add Track')
        btnTrack.clicked.connect(self.addTrack)
        tblTrack = QtGui.QTableWidget(0,1)
        tblTrack.setHorizontalHeaderLabels(['Track Name'])
        tblTrack.verticalHeader().sectionDoubleClicked.connect(self.removeTrack)
        self.track_table = tblTrack
        for track in config['tracks']:
            self.addTrack(track)

        layoutMain = QtGui.QVBoxLayout()
        layoutMain.addWidget(lblName)
        layoutMain.addWidget(txtName)
        layoutMain.addWidget(lblLines)
        layoutMain.addWidget(txtLines)
        layoutMain.addWidget(lblOverlap)
        layoutMain.addWidget(txtOverlap)
        layoutMain.addWidget(btnTrack)
        layoutMain.addWidget(tblTrack)
        layoutMain.addWidget(buttonBox)
        self.setLayout(layoutMain)

        self.name_txt = txtName
        self.lines_txt = txtLines
        self.overlap_txt = txtOverlap

    def addTrack(self, guid=None):
        tt = self.track_table
        n = tt.rowCount()
        tt.setRowCount(n+1)
        trackSrc = self.config['trackSrc']

        cmbTracks = QtGui.QComboBox()
        tracks = [track['name'] for track in trackSrc]
        cmbTracks.addItems(tracks)

        tt.setCellWidget(n,0,cmbTracks)

        if guid:
            for i in range(len(tracks)):
                if guid==trackSrc[i]['guid']:
                    cmbTracks.setCurrentIndex(i)
                    break

    def removeTrack(self, index):
        self.track_table.removeRow(index)

    def getResult(self):
        tt = self.track_table
        trackSrc = self.config['trackSrc']
        tracks = []
        for i in range(tt.rowCount()):
            tracks.append(trackSrc[tt.cellWidget(i,0).currentIndex()]['guid'])

        return {
            'name':self.name_txt.text(),
            'lines':self.lines_txt.value(),
            'overlap':self.overlap_txt.value(),
            'tracks':tracks
        }

class FFTFreqModule(ModuleBase):
    ModuleName = 'FFTFreq'
    ModuleType = ModuleType.config
    ContextMenu = [
        {'title':'Show Result', 'action':'showResult'}, #FirstPhase,Average
        {'title':'Export', 'action':'export2xlsx'}, #TBDetermined
        {'title':'Show STFT', 'action':'showStft'}
    ]
    def __init__(self, guid, name, parent):
        super().__init__(guid,name,parent)
        self.data = None
        self.config = {}
        self.dataLoaded = False
        self.track = self.parent.parent.getTrack(self.guid)

    def getData(self):
        if not self.dataLoaded:
            self.data = self.parent.getFreqData(self.guid)
            self.dataLoaded = True
        return self.data

    def getListConfig(self):
        cfg = {
            'type':self.ModuleName,
            'name':self.name,
            'object':self,
            'sub':[
                self.track.getListConfig()
            ]
        }
        return cfg

    def getFileConfig(self):
        pass

    def parseConfig(self, config):
        pass

    def getProperty(self):
        return {}

    def export2xlsx(self):
        pass

    def showResult(self):
        result = self.getData()
        # result {'data','bandwidth','overlap'}
        # widget = FFTFreqWidget(data)
        # gl.plotManager.addWidget(self.name,widget)
        d = result['data']
        (l,w) = d.shape
        sr = result['bandwidth']*2.56
        x = np.fft.fftfreq(2*w,1/sr)[:w]
        y = d.mean(0)
        gl.plotManager.plotNew((self.name,x,y))

    def showStft(self):
        rp = DisplayRangePicker(maxFreq=self.track.config['bandwidth'])
        rp.exec()
        if rp.result():
            result = self.getData()
            config = rp.getResult()

            (l,w) = result['data'].shape
            sr = result['bandwidth']*2.56
            ols = np.int(2*w*(1-result['overlap']/100))
            x = (np.arange(l)*ols+w)/sr
            # intercept x if time was provided
            y = np.fft.fftfreq(2*w,1/sr)[:w]
            z = result['data']
            if config['freq']:
                (lower,upper) = config['freq']
                bLow = y>=(lower-0.5)
                bUp = y<=(upper+0.5)
                bAll = np.all([bLow,bUp],axis=0)
                y = y[bAll]
                z = z[:,bAll]
            (Y,X) = np.meshgrid(y,x)
            Z = np.abs(z)
            
            widget = FFTStftWidget((X,Y,Z))
            gl.plotManager.addWidget(self.name,widget)

class FFTFreqWidget(QtGui.QWidget):
    def __init__(self, result):
        super().__init__()

class FFTStftWidget(ImageWidget):
    def __init__(self, xyz):
        super().__init__(xlabel='Time', ylabel='Frequency',
            xunit='s', yunit='Hz', yreverse=False, lock_aspect_ratio=False)
        (x,y,z) = xyz
        itm = make.pcolor(x,y,z)
        self.plot.add_item(itm)
        self.register_all_image_tools()

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

class FFTStftWidgetPlt(QtGui.QWidget):
    def __init__(self, xyz):
        super.__init__()

        (x,y,z) = xyz

        fig = plt.figure()
        # ax = fig.add_subplot(111)
        canvas = FigureCanvas(fig)
        plt.pcolor(x,y,z)
        plt.xlabel('Time (s)')
        plt.ylabel('Frequency (Hz)')
        plt.colorbar()
        nvb = NavigationToolbar(canvas, self)
        
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(nvb)
        layout.addWidget(canvas)

        canvas.draw()