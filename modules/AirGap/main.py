from rdsp.module import ModuleBase
from rdsp import gl
from rdsp.modules.AirGap.algorithm import findContinuous, findSEIndex, getAprxValue

import numpy as np
from PyQt4 import QtGui
import xlsxwriter

class AirGapModule(ModuleBase):
    ModuleName = 'AirGap'
    ContextMenu = [
        {'title':'Config', 'action':'setConfig'},
        {'title':'Process', 'action':'processNow'},
        {'title':'Show Result', 'action':'showResult'},
        {'title':'Export', 'action':'export2xlsx'},
        {'title':'Delete', 'action':'delete'}
    ]

    def __init__(self, guid, name, parent, processed=False):
        super().__init__(guid,name,parent)
        self.tracks = []
        self.keyPhasor = None
        self.config = {
            'rot-cw':True,
            'num-cw':False,
            'numOfPoles':48,
        }
        self.result = None
        self.resultLoaded = False
        self.processed = processed

    def getResult(self):
        if not self.resultLoaded:
            self.result = gl.projectManager.loadResult(self.guid)
            self.resultLoaded = True
        return self.result
    
    def configWindow(self, config=None):
        if not config:
            config = {
                'name':self.name,
                'rot-cw':True,
                'num-cw':False,
                'numOfPoles':48,
                'trackSrc':self.parent.getTracksList(),
                'keyPhasor':None,
                'trackSet':None
            }
            
        cfgWin = AirGapConfig(config)
        cfgWin.exec_()
        if cfgWin.result():
            self.parseConfig(cfgWin.getResult())
            return True
        return False

    def getProperty(self):
        return {
            "Number of Poles":self.config['numOfPoles']
        }

    def parseConfig(self, config):
        if 'name' in config:
            self.name = config['name']

        self.config = {
            'rot-cw':config['rot-cw'],
            'num-cw':config['num-cw'],
            'numOfPoles':config['numOfPoles']
        }
        self.keyPhasor = self.parent.getTrack(config['keyPhasor'])
        self.tracks = [
            {
                'object':self.parent.getTrack(track['guid']),
                'thickness':track['thickness'],
                'angle':track['angle'],
                'pole':track['pole']
            } for track in config['trackSet']
        ]

    def getFileConfig(self):
        config = {
            'type':self.ModuleName,
            'guid':self.guid,
            'name':self.name,
            'config':{},
            'processed':self.processed
        }
        cfg = config['config']
        cfg['rot-cw'] = self.config['rot-cw']
        cfg['num-cw'] = self.config['num-cw']
        cfg['numOfPoles'] = self.config['numOfPoles']
        cfg['keyPhasor'] = self.keyPhasor.guid
        cfg['trackSet'] = [
            {
                'guid':track['object'].guid,
                'thickness':track['thickness'],
                'angle':track['angle'],
                'pole':track['pole']
            } for track in self.tracks
        ]

        return config

    def getListConfig(self):
        config = {
            'type':self.ModuleName,
            'name':self.name,
            'object':self,
            'sub':[]
        }
        config['sub'] = [
            trackSet['object'].getListConfig() for trackSet in self.tracks
        ]
        kpCfg = self.keyPhasor.getListConfig()
        kpCfg['type'] = 'KeyPhasor'
        config['sub'].insert(0, kpCfg)

        return config

    def processNow(self):
        kp_data = self.keyPhasor.getData()[0]
        kp_data_bool = kp_data<((kp_data.max()+kp_data.min())/2)
        kp_se_pairs = findContinuous(kp_data_bool,0)
        tolerance = 0.01
        poles = self.config['numOfPoles']
        rotCw = self.config['rot-cw']
        numCw = self.config['num-cw']

        def funcname(loi):
            result = []
            for trackSet in self.tracks:
                track_data = trackSet['object'].getData()[0]
                track_data_bool = track_data<((track_data.max()+track_data.min())/2)
                track_se_pairs = findContinuous(track_data_bool,0)
                se_idx = findSEIndex(kp_se_pairs, track_se_pairs)
                t_pole = trackSet['pole']
                t_thick = trackSet['thickness']
                t_freq = trackSet['object'].config['bandwidth']*2.56
                l = se_idx.size
                r = {
                    'speed':np.zeros(l-1),
                    'name':trackSet['object'].name,
                    'angle':trackSet['angle'],
                    'data':np.zeros((poles,l-1))
                }
                dat = r['data']
                spd = r['speed']
                for i in range(1,l):
                    track_se_segment = track_se_pairs[se_idx[i-1]:se_idx[i],:]
                    (ll,ww) = track_se_segment.shape
                    # assert ll==numOfPoles
                    for j in range(ll):
                        (v,c) = getAprxValue(track_data,track_se_segment[j,:],tolerance)
                        n = t_pole+j*(-1+numCw*2)*(1-2*rotCw)
                        if n<=0:
                            n += poles
                        else:
                            if n>poles:
                                n -= poles
                        dat[j,i-1] = v+t_thick
                    spd[i-1] = 60*t_freq/(
                        track_se_pairs[se_idx[i],0] - track_se_pairs[se_idx[i-1],0]
                    )
                result.append(r)
                loi[1] += 1
            gl.projectManager.saveResult(self.guid, result)
            self.result = np.array(result)
            loi[2] = 1
        gl.progressManager.startNewProgress('Calculating',funcname,[len(self.tracks),0,0])

        self.processed = True
        self.resultLoaded = True

        # make sure processed=True
        gl.projectManager.saveProject()

    def setConfig(self):
        config = self.getFileConfig()
        cfg = config['config']
        cfg['name'] = self.name
        cfg['trackSrc'] = self.parent.getTracksList()
        if self.configWindow(cfg):
            self.parent.refresh()

    def showResult(self):
        if self.processed:
            result = self.getResult()
            widget = AirGapResult(result)
            gl.plotManager.addWidget(self.name,widget)

    def export2xlsx(self):
        if self.processed:
            filename = QtGui.QFileDialog.getSaveFileName(caption='Export to Excel', filter='Excel File (*.xlsx)')
            if not filename:
                return

            result = self.getResult()
            wb = xlsxwriter.Workbook(filename)
            num_format = wb.add_format({'num_format':'0.000'})
            for dt in result:
                ws = wb.add_worksheet(dt['name'])
                ws.write_row(0,1,dt['speed'],num_format)
                ws.write_string(0,0,'Speed (rpm)')
                row = 2
                for d in dt['data']:
                    ws.write(row,0,row-1)
                    ws.write_row(row,1,d,num_format)
                    row += 1

            wb.close()

    def delete(self):
        self.parent.removeProcess(self)
        if self.processed:
            gl.projectManager.removeResult(self.guid)

class AirGapConfig(QtGui.QDialog):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle('AirGap Configuration')
        self.initUI()

    def initUI(self):
        config = self.config
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        lblName = QtGui.QLabel("Name")
        txtName = QtGui.QLineEdit(config['name'])

        grpRotation = QtGui.QGroupBox('Generator Rotation')
        rdoRotCw = QtGui.QRadioButton('Clockwise')
        rdoRotCcw = QtGui.QRadioButton('Counter-Clockwise')
        if config['rot-cw']:
            rdoRotCw.setChecked(True)
        else:
            rdoRotCcw.setChecked(True)
        rotLayout = QtGui.QHBoxLayout(grpRotation)
        rotLayout.addWidget(rdoRotCw)
        rotLayout.addWidget(rdoRotCcw)

        grpNumbering = QtGui.QGroupBox('Numbering Direction')
        rdoNumCw = QtGui.QRadioButton('Clockwise')
        rdoNumCcw = QtGui.QRadioButton('Counter-Clockwise')
        if config['num-cw']:
            rdoNumCw.setChecked(True)
        else:
            rdoNumCcw.setChecked(True)
        numLayout = QtGui.QHBoxLayout(grpNumbering)
        numLayout.addWidget(rdoNumCw)
        numLayout.addWidget(rdoNumCcw)

        lblCount = QtGui.QLabel('Number of Poles')
        txtCount = QtGui.QSpinBox()
        txtCount.setRange(0, 100)
        txtCount.setSingleStep(1)
        txtCount.setValue(config['numOfPoles'])

        lblKpTrack = QtGui.QLabel('KeyPhasor Track')
        cmbTracks = QtGui.QComboBox()
        tracks = [track['name'] for track in self.config['trackSrc']]
        cmbTracks.addItems(tracks)
        if config['keyPhasor']:
            for i in range(len(tracks)):
                if self.config['trackSrc'][i]['guid']==config['keyPhasor']:
                    cmbTracks.setCurrentIndex(i)
                    break

        btnTrack = QtGui.QCommandLinkButton('Add Track')
        btnTrack.clicked.connect(self.addTrack)

        sideLayout = QtGui.QVBoxLayout()
        sideLayout.addWidget(lblName)
        sideLayout.addWidget(txtName)
        sideLayout.addWidget(grpRotation)
        sideLayout.addWidget(grpNumbering)
        sideLayout.addWidget(lblCount)
        sideLayout.addWidget(txtCount)
        sideLayout.addWidget(lblKpTrack)
        sideLayout.addWidget(cmbTracks)
        sideLayout.addWidget(btnTrack)
        sideLayout.addStretch(1)

        tracksTable = QtGui.QTableWidget(0,4)
        tracksTable.setHorizontalHeaderLabels(['Track Name','Thickness','Angle','Pole'])        
        tracksTable.verticalHeader().sectionDoubleClicked.connect(self.removeTrack)
        self.tracks_table = tracksTable
        if config['trackSet']:
            for i in range(len(config['trackSet'])):
                self.addTrack(config['trackSet'][i])

        mainLayout = QtGui.QHBoxLayout()
        mainLayout.addLayout(sideLayout)
        mainLayout.addWidget(tracksTable, stretch=1)
        layoutMain = QtGui.QVBoxLayout()
        layoutMain.addLayout(mainLayout)
        layoutMain.addWidget(buttonBox)
        self.setLayout(layoutMain)

        self.name_txt = txtName
        self.rotCw_rdo = rdoRotCw
        self.numCw_rdo = rdoNumCw
        self.numOfPoles_txt = txtCount
        self.keyPhasor_cmb = cmbTracks

    def addTrack(self, trackCfg=None):
        tt = self.tracks_table
        n = tt.rowCount()
        tt.setRowCount(n+1)

        cmbTracks = QtGui.QComboBox()
        tracks = [track['name'] for track in self.config['trackSrc']]
        cmbTracks.addItems(tracks)

        tt.setCellWidget(n,0,cmbTracks)

        if trackCfg:
            for i in range(len(tracks)):
                if trackCfg['guid']==self.config['trackSrc'][i]['guid']:
                    cmbTracks.setCurrentIndex(i)
                    break
            itm = QtGui.QTableWidgetItem(str(trackCfg['thickness']))
            tt.setItem(n,1,itm)
            itm = QtGui.QTableWidgetItem(str(trackCfg['angle']))
            tt.setItem(n,2,itm)
            itm = QtGui.QTableWidgetItem(str(trackCfg['pole']))
            tt.setItem(n,3,itm)

    def removeTrack(self, index):
        self.tracks_table.removeRow(index)

    def getResult(self):
        tt = self.tracks_table
        trackSrc = self.config['trackSrc']
        trackSet = []
        for r in range(tt.rowCount()):
            trackSet.append({
                'guid':trackSrc[tt.cellWidget(r,0).currentIndex()]['guid'],
                'thickness':float(tt.item(r,1).text()),
                'angle':float(tt.item(r,2).text()),
                'pole':int(tt.item(r,3).text())
                # try catch parseFloat error required
            })

        return {
            'name':self.name_txt.text(),
            'rot-cw':self.rotCw_rdo.isChecked(),
            'num-cw':self.numCw_rdo.isChecked(),
            'numOfPoles':self.numOfPoles_txt.value(),
            'keyPhasor':trackSrc[self.keyPhasor_cmb.currentIndex()]['guid'],
            'trackSet':trackSet
        }

from PyQt4.QtCore import Qt
from guiqwt.builder import make
from guiqwt.plot import CurveWidget

class AirGapResult(QtGui.QWidget):
    def __init__(self, result):
        super().__init__()

        self.numOfSensor = result.size
        (self.numOfPole,self.numOfSpeed) = result[0]['data'].shape
        
        a = np.array([c['data'] for c in result])
        self.max = a.max()
        self.min = a.min()
        self.range = (self.max-self.min)/8*10

        # sort result by angle
        t = [(x['angle'],i,x) for i,x in enumerate(result)]
        t.sort()
        result = [s[2] for s in t]
        self.result = result

        # append first angle to close the loop
        r = {'angle':result[0]['angle']+360,'data':result[0]['data']}
        result.append(r)

        self.poleIndex = 0
        self.speedIndex = 0
        self.sensorIndex = 0

        self.initUI()
        self.orbitPlot()

    def initUI(self):
        layout = QtGui.QVBoxLayout(self)
        
        curve_plot = CurveWidget()
        curve_plot.register_all_curve_tools()
        curve_rotor = make.curve([],[])
        curve_stator = make.curve([],[])
        curve_eccent = make.circle(0,0,0,0)
        plot = curve_plot.plot
        # plot.setAxisScale(0,-self.range,self.range)
        # plot.setAxisScale(2,-self.range,self.range)
        plot.add_item(curve_rotor)
        plot.add_item(curve_stator)
        plot.add_item(curve_eccent)
        self.curve_rotor = curve_rotor
        self.curve_stator = curve_stator
        self.curve_plot = curve_plot
        self.curve_eccent = curve_eccent
        
        info_layout = QtGui.QVBoxLayout()
        eccent_grp = QtGui.QGroupBox("Eccentricity")
        eccent_layout = QtGui.QVBoxLayout(eccent_grp)
        eccent_x_lbl = QtGui.QLabel("X")
        eccent_x = QtGui.QLabel('0')
        eccent_y_lbl = QtGui.QLabel('Y')
        eccent_y = QtGui.QLabel('0')
        eccent_l_lbl = QtGui.QLabel('(X^2+Y^2)^0.5')
        eccent_l = QtGui.QLabel('0')
        eccent_layout.addWidget(eccent_x_lbl)
        eccent_layout.addWidget(eccent_x)
        eccent_layout.addWidget(eccent_y_lbl)
        eccent_layout.addWidget(eccent_y)
        eccent_layout.addWidget(eccent_l_lbl)
        eccent_layout.addWidget(eccent_l)
        self.eccent_x = eccent_x
        self.eccent_y = eccent_y
        self.eccent_l = eccent_l
        
        statRef_lbl = QtGui.QLabel("Stator Ref.")
        statRef_cmb = QtGui.QComboBox()
        statRef_cmb.addItems([str(i) for i in np.arange(self.numOfPole)+1])
        statRef_cmb.currentIndexChanged.connect(self.pole_changed)
        rotRef_lbl = QtGui.QLabel("Rotor Ref.")
        rotRef_cmb = QtGui.QComboBox()
        rotRef_cmb.addItems([self.result[i]['name'] for i in range(self.numOfSensor)])
        rotRef_cmb.currentIndexChanged.connect(self.sensor_changed)
        info_layout.addWidget(eccent_grp)
        info_layout.addStretch(1)
        info_layout.addWidget(statRef_lbl)
        info_layout.addWidget(statRef_cmb)
        info_layout.addWidget(rotRef_lbl)
        info_layout.addWidget(rotRef_cmb)
        
        speed_slider = QtGui.QSlider(Qt.Horizontal)
        speed_slider.setTickPosition(QtGui.QSlider.TicksAbove)
        speed_slider.setMaximum(self.numOfSpeed-1)
        speed_slider.valueChanged.connect(self.speed_changed)
        speed_label = QtGui.QLabel("Speed")
        self.speed_label = speed_label
        spd_layout = QtGui.QHBoxLayout()
        spd_layout.addWidget(speed_slider)
        spd_layout.addWidget(speed_label)

        up_layout = QtGui.QHBoxLayout()
        up_layout.addWidget(curve_plot,stretch=1)
        up_layout.addLayout(info_layout)
        layout.addLayout(up_layout)
        layout.addLayout(spd_layout)

    def speed_changed(self, index):
        self.speedIndex = index
        self.orbitPlot()

    def pole_changed(self, index):
        self.poleIndex = index
        self.orbitPlot()

    def sensor_changed(self, index):
        self.sensorIndex = index
        self.orbitPlot()

    def orbitPlot(self):
        result = self.result
        poleIdx = self.poleIndex
        sensIdx = self.sensorIndex
        spedIdx = self.speedIndex
        sensNum = self.numOfSensor
        spedNum = self.numOfSpeed
        poleNum = self.numOfPole
        rng = self.range
        mini = self.min
        maxi = self.max

        data = result[sensIdx]['data']
        angle = np.arange(poleNum)/poleNum*360
        radius = (rng*0.1+maxi) - data[:,spedIdx]
        x = np.cos(angle/180*np.pi)*radius
        y = np.sin(angle/180*np.pi)*radius
        self.curve_rotor.set_data(np.append(x,x[0]),np.append(y,y[0]))

        xm = x.mean()
        ym = y.mean()
        self.eccent_x.setText('%.2f' % xm)
        self.eccent_y.setText('%.2f' % ym)
        lm = np.absolute(xm+ym*1j)
        self.eccent_l.setText('%.2f' % lm)
        self.curve_eccent.set_xdiameter(xm,ym,xm,ym)

        angle = np.array([])
        for i in range(1,sensNum+1):
            agl = np.arange(result[i-1]['angle'],result[i]['angle'])
            angle = np.append(angle,agl)
        xp = [r['angle'] for r in result]
        yp = [r['data'][poleIdx,spedIdx] for r in result]
        radius = np.interp(angle,xp,yp) - mini+rng
        x = np.cos(angle/180*np.pi)*radius
        y = np.sin(angle/180*np.pi)*radius
        self.curve_stator.set_data(np.append(x,x[0]),np.append(y,y[0]))

        # self.curve_plot.plot.do_autoscale()
        self.speed_label.setText(
            '%.2f' % result[sensIdx]['speed'][spedIdx]
        )