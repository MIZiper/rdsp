from enum import IntEnum
from rdsp import gl
from PyQt4 import QtGui
import uuid, numpy as np

class ModuleType(IntEnum):
    none = 0
    config = 1
    process = 2
    all = 3

class ModuleBase(object):
    ModuleName = 'ModuleName'
    ModuleType = ModuleType.all
    ContextMenu = []

    def __init__(self, guid, name, parent):
        self.guid = guid
        self.name = name
        self.parent = parent
        self.config = {}

    def configWindow(self, config=None):
        raise NotImplementedError

    def parseConfig(self, config):
        raise NotImplementedError

    def getProperty(self):
        # raise NotImplementedError
        return None

    def getFileConfig(self):
        raise NotImplementedError

    def getListConfig(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def setConfig(self):
        raise NotImplementedError

    def processNow(self):
        raise NotImplementedError

class SignalContainer(ModuleBase):
    ContextMenu = [
        {'title':'New Process', 'action':'addProcess'},
        {'title':'Delete', 'action':'delete'}
    ]

    def __init__(self, guid, name, parent):
        super().__init__(guid,name,parent)
        self.tracks = []
        self.process = []

    def getTrack(self, guid):
        # even though track may in self.tracks
        return self.parent.getTrack(guid)

    def getTracksList(self):
        # TODO: cache to avoid loop
        return [{
            'name':track.name,
            'guid':track.guid
        } for track in self.tracks]

    def addTracks(self, tracksConfig):
        tracks = self.parent.addTracks(tracksConfig)
        self.tracks += tracks
        return tracks

    def removeTracks(self, tracks):
        # assert tracks!=self.tracks
        for track in tracks:
            self.tracks.remove(track)
        self.parent.removeTracks(tracks)

    def addProcess(self):
        moduleName = gl.moduleManager.getModulesName()
        item, ok = QtGui.QInputDialog.getItem(None,'Select a Module','Module:',moduleName,editable=False)
        if ok and item:
            moduleClass = gl.moduleManager.getModule(item)
            guid = str(uuid.uuid4())
            module = moduleClass(guid, item, self)
            if module.configWindow():
                self.process.append(module)
                self.parent.refresh()

    def fillProcess(self, processConfig):
        for pc in processConfig:
            moduleClass = gl.moduleManager.getModule(pc['type'])
            if moduleClass is None:
                QtGui.QMessageBox.warning(None,'Module','No such Module Found! Your setting will lost!')
                continue
            if 'processed' in pc:
                prc = moduleClass(pc['guid'], pc['name'], self, pc['processed'])
            else:
                prc = moduleClass(pc['guid'], pc['name'], self)
            prc.parseConfig(pc['config'])
            self.process.append(prc)

    def removeProcess(self, process):
        self.process.remove(process)
        self.parent.refresh()

    def getListConfig(self):
        return {
            'type':self.ModuleName,
            'name':self.name,
            'object':self,
            'sub':[
                {
                    'type':'-',
                    'name':'Tracks List',
                    'object':None,
                    'sub':[
                        track.getListConfig() for track in self.tracks
                    ]
                }
            ] + [
                prc.getListConfig() for prc in self.process
            ]
        }

    def getFileConfig(self):
        return {
            'type':self.ModuleName,
            'guid':self.guid,
            'name':self.name,
            'config':{
                'tracks':[
                    track.guid for track in self.tracks
                ],
                'process':[
                    prc.getFileConfig() for prc in self.process
                ]
            }
        }

    def parseConfig(self, config):
        self.tracks = [
            self.parent.getTrack(guid) for guid in config['tracks']
        ]
        self.fillProcess(config['process'])

    def refresh(self):
        self.parent.refresh()

    def delete(self):
        for prc in self.process:
            prc.delete()
        # self.process.clear()
        self.parent.removeTracks(self.tracks)
        # self.tracks.clear()
        self.parent.removeProcess(self)

class SignalModule(SignalContainer):
    ModuleName = 'Signal'
    ModuleType = ModuleType.config

    def fillTracks(self, tracksConfig):
        for tc in tracksConfig:
            track = TrackModule(tc['guid'], tc['name'], self)
            track.parseConfig(tc['config'])
            self.tracks.append(track)

    def getFileConfig(self):
        return {
            'type':self.ModuleName,
            'guid':self.guid,
            'name':self.name,
            'config':self.config,
            'tracks':[
                track.getFileConfig() for track in self.tracks
            ],
            'process':[
                prc.getFileConfig() for prc in self.process
            ]
        }

    def getTrack(self, guid):
        # TODO: do some cache to avoid loop
        for track in self.tracks:
            if track.guid == guid:
                return track
        return None

    def addTracks(self, tracksConfig):
        tracks = []
        for tc in tracksConfig:
            guid = str(uuid.uuid4())
            track = TrackModule(guid, tc['name'], self, tc['data'])
            track.parseConfig(tc['config'])
            tracks.append(track)

        self.tracks += tracks
        self.parent.addTracks(tracks)
        return tracks

    def parseConfig(self, config):
        self.config = config

class TrackModule(ModuleBase):
    ModuleName = 'Track'
    ModuleType = ModuleType.config

    ContextMenu = [
        {'title':'Plot', 'action':'plot'}
    ]

    def __init__(self, guid, name, parent, data=None):
        super().__init__(guid,name,parent)
        self.data = data
        self.dataLoaded = data is not None

    def getData(self):
        if not self.dataLoaded:
            self.data = gl.projectManager.loadTrack(self.guid)
            self.dataLoaded = True
        return self.data

    def getListConfig(self):
        return {
            'type':self.ModuleName,
            'name':self.name,
            'object':self
        }
        # in fact, the 'object' contains type/name info,
        # so technically, return 'object' is enough,
        # but to custom the display, such as KeyPhasor, use a dict

    def getFileConfig(self):
        return {
            'type':self.ModuleName,
            'guid':self.guid,
            'name':self.name,
            'config':self.config
        }

    def parseConfig(self, config):
        self.config = config

    def getPlotData(self):
        data = self.getData()
        l = data.size / (self.config['bandwidth']*2.56)
        xs = np.linspace(0,l,data.size,False)
        return (xs,data[0])

    def plot(self):
        xy = self.getPlotData()
        tw = gl.plotManager.plotNew(xy)