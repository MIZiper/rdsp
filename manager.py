import os, sys, importlib
from os import path, listdir
import json, uuid
from rdsp.module import ModuleType, SignalModule, TrackModule
from scipy.io import loadmat
import numpy as np

class ProjectManager(object):
    ListWidget = None
    DEFAULTCONFIG = 'project.json'
    RESULTDIR = 'result/'
    SOURCEDIR = 'source/'
    EXTENSION = '.npy'

    @staticmethod
    def RegisterListWidget(listWidget):
        ProjectManager.ListWidget = listWidget

    def __init__(self, fdPath):
        self.signals = []

        if path.isdir(fdPath):
            # new project folder
            configFile = path.join(fdPath, ProjectManager.DEFAULTCONFIG)
            resultDir = path.join(fdPath, ProjectManager.RESULTDIR)
            sourceDir = path.join(fdPath, ProjectManager.SOURCEDIR)
            
            try:
                os.mkdir(resultDir)
                os.mkdir(sourceDir)
            except Exception:
                pass
            data = []
        else:
            # open existed config
            # TODO: check if the file is OK
            configFile = fdPath
            resultDir = path.join(path.dirname(fdPath), ProjectManager.RESULTDIR)
            sourceDir = path.join(path.dirname(fdPath), ProjectManager.SOURCEDIR)
            with open(fdPath) as fp:
                data = json.load(fp)

        self.configFile = configFile
        self.resultDir = resultDir
        self.sourceDir = sourceDir
        self.parseConfig(data)
        self.refresh(False)

    def importOrosMat(self, matpath):
        mat = loadmat(matpath)
        i = 1
        tracks = []

        while ('Track%d' % i) in mat:
            i += 1
        n = i-1
        guid = str(uuid.uuid4())
        name = path.basename(matpath)
        signal = SignalModule(guid, name, self)
        self.signals.append(signal)

        for i in np.arange(n)+1:
            tracks.append({
                'name':mat['Track%d_Name' % i][0],
                'config':{
                    'bandwidth':int(mat['Track%d_TrueBandWidth' % i][0,0]),
                    'c1':float(mat['Track%d_Sensitivity' % i][0,0]),
                    'c0':float(mat['Track%d_Offset' % i][0,0]),
                    'x-unit':mat['Track%d_X_Magnitude' % i][0],
                    'y-unit':mat['Track%d_Y_Magnitude' % i][0]
                },
                'data':mat['Track%d' % i]
            })

        signal.parseConfig({
            'date':mat['RecordDate'][0]
        })
        signal.addTracks(tracks)

    def importInternalSignal(self, intSig):
        pass

    def saveProject(self):
        with open(self.configFile, mode='w') as fp:
            json.dump(self.getFileConfig(), fp, indent=2)

    def parseConfig(self, data):
        # self.signals.clear()
        # it should be clear
        for dt in data:
            # assert dt['type'] == 'Signal'
            signal = SignalModule(dt['guid'], dt['name'], self)
            signal.fillTracks(dt['tracks'])
            signal.fillProcess(dt['process'])
            signal.parseConfig(dt['config'])
            self.signals.append(signal)

    def getFileConfig(self):
        return [signal.getFileConfig() for signal in self.signals]

    def addTracks(self, tracks):
        for track in tracks:
            np.save(path.join(self.sourceDir,track.guid+ProjectManager.EXTENSION),track.getData())
        self.refresh()

    def removeTracks(self, tracks):
        for track in tracks:
            os.remove(path.join(self.sourceDir,track.guid+ProjectManager.EXTENSION))
        self.refresh()

    def removeProcess(self, process):
        # in fact, process is SignalModule
        self.signals.remove(process)
        self.refresh()

    def refresh(self, save=True):
        # TODO: refine for save
        # will refresh many times when there's deletion
        ProjectManager.ListWidget.clear()
        for signal in self.signals:
            ProjectManager.ListWidget.addNode(signal.getListConfig())
        if save: self.saveProject()

    def loadTrack(self, guid):
        return np.load(path.join(self.sourceDir,guid+ProjectManager.EXTENSION))

    def loadResult(self, guid):
        return np.load(path.join(self.resultDir,guid+ProjectManager.EXTENSION))

    def saveResult(self, guid, result):
        np.save(path.join(self.resultDir,guid+ProjectManager.EXTENSION),result)

    def removeResult(self, guid):
        os.remove(path.join(self.resultDir,guid+ProjectManager.EXTENSION))

class ModuleManager(object):
    def __init__(self, mdPath):
        self.modules = {}
        self.modulesName = []

        self.registerModule(SignalModule)
        self.registerModule(TrackModule)
        self.loadModules(mdPath)

    def registerModule(self, moduleClass):
        self.modules[moduleClass.ModuleName] = moduleClass
        if (moduleClass.ModuleType & ModuleType.process):
            self.modulesName.append(moduleClass.ModuleName)

    def getModule(self, moduleClassName):
        try:
            return self.modules[moduleClassName]
        except Exception:
            return None

    def getModulesName(self):
        return self.modulesName

    def loadModules(self, mdPath):
        # WARN: path will be appended multi-times if more instance created
        sys.path.append(mdPath)
        dirNames = listdir(mdPath)
        for dirName in dirNames:
            if dirName!='__pycache__' and path.isdir(path.join(mdPath,dirName)):
                module = importlib.import_module(dirName)
                if module.ISREADY:
                    self.registerModule(module.RDSP_Module)
                    if hasattr(module, 'RDSP_Modules'):
                        for mod in module.RDSP_Modules:
                            self.registerModule(mod)

class ProgressManager(object):
    def __init__(self, mainWidget):
        pass

class PlotManager(object):
    def __init__(self, plotWidget):
        self.plotWidget = plotWidget

    def addWidget(self, name, widget):
        self.plotWidget.addWidget(name, widget)