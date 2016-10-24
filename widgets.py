from rdsp import gl

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from guidata.qthelpers import create_action, add_actions
import functools

class ListWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(('Type','Name'))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

        self.propertyWindow = None
        self.currentItemChanged.connect(self.showProperty)

    def contextMenu(self, position):
        items = self.selectedItems()
        if len(items)>0:
            boundObject = items[0].data(0,33)
            if boundObject is None: return
            moduleClassName = boundObject.ModuleName
            moduleClass = gl.moduleManager.getModule(moduleClassName)
            if moduleClass is None: return

            menu = QtGui.QMenu()
            actions = (
                create_action(
                    menu,action['title'],
                    functools.partial(
                        getattr(moduleClass,action['action']),
                        boundObject
                    )
                ) for action in moduleClass.ContextMenu
            )
            add_actions(menu, actions)
            menu.exec_(self.viewport().mapToGlobal(position))

    def showProperty(self, item):
        if self.propertyWindow is None: return
        prop = None
        if  item is not None:
            boundObject = item.data(0,33)
            if boundObject is not None:
                prop = boundObject.getProperty()
        # should use try/catch instead of if/else?
        self.propertyWindow.showProperty(prop)

    def registerPropertyWindow(self, propWin):
        self.propertyWindow = propWin
 
    def appendNode(self, parent, node):
        item = QtGui.QTreeWidgetItem(parent)
        item.setText(0,node['type'])
        item.setText(1,node['name'])
        item.setData(0,33,node['object'])
        if 'sub' in node:
            for subNode in node['sub']:
                self.appendNode(item, subNode)

    def addNode(self, node):
        self.appendNode(self, node)

class PropertyWidget(QtGui.QListWidget):
    def showProperty(self, prop):
        self.clear()
        if prop is None: return
        for (k,v) in prop.items():
            self.addItem(k)
            self.addItem(' '+str(v))

class PlotWidget(QtGui.QTabWidget):
    def addWidget(self, name, widget):
        self.addTab(widget, name)
        self.setCurrentIndex(self.count()-1)

    # self.setTabsClosable(True)
    # self.setTabPosition(QtGui.QTabWidget.South)

class DisplayRangePicker(QtGui.QDialog):
    def __init__(self, maxFreq = None, maxTime = None):
        super().__init__()
        self.setWindowTitle('Range Picker')
        self.maxFreq = maxFreq
        self.maxTime = maxTime
        self.useAll = False
        self.initUI()

    def initUI(self):
        layout = QtGui.QVBoxLayout(self)

        buttonBox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok |
            QtGui.QDialogButtonBox.Cancel
        )
        btnUseAll = buttonBox.addButton('All',QtGui.QDialogButtonBox.ResetRole)
        btnUseAll.clicked.connect(self.useAllHandler)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        if self.maxTime:
            grpTime = QtGui.QGroupBox('Time')
            upperTime = QtGui.QSlider(Qt.Horizontal)
            upperTime.setMaximum(self.maxTime)
            upperTime.setValue(self.maxTime)
            lblUpperTime = QtGui.QLabel('%d' % self.maxTime)
            lowerTime = QtGui.QSlider(Qt.Horizontal)
            lowerTime.setMaximum(self.maxTime)
            lowerTime.setValue(0)
            lblLowerTime = QtGui.QLabel('%d' % 0)
            upperTime.valueChanged.connect(lambda x: lblUpperTime.setText('%d' % x))
            lowerTime.valueChanged.connect(lambda x: lblLowerTime.setText('%d' % x))
            grpTimeLayout = QtGui.QGridLayout(grpTime)
            grpTimeLayout.addWidget(lowerTime,0,0)
            grpTimeLayout.addWidget(upperTime,1,0)
            grpTimeLayout.addWidget(lblLowerTime,0,1)
            grpTimeLayout.addWidget(lblUpperTime,1,1)
            layout.addWidget(grpTime)

            self.upperTime = upperTime
            self.lowerTime = lowerTime

        if self.maxFreq:
            grpFreq = QtGui.QGroupBox('Frequency')
            upperFreq = QtGui.QSlider(Qt.Horizontal)
            upperFreq.setMaximum(self.maxFreq)
            upperFreq.setValue(self.maxFreq)
            lblUpperFreq = QtGui.QLabel('%d' % self.maxFreq)
            lowerFreq = QtGui.QSlider(Qt.Horizontal)
            lowerFreq.setMaximum(self.maxFreq)
            lowerFreq.setValue(0)
            lblLowerFreq = QtGui.QLabel('%d' % 0)
            upperFreq.valueChanged.connect(lambda x: lblUpperFreq.setText('%d' % x))
            lowerFreq.valueChanged.connect(lambda x: lblLowerFreq.setText('%d' % x))
            grpFreqLayout = QtGui.QGridLayout(grpFreq)
            grpFreqLayout.addWidget(lowerFreq,0,0)
            grpFreqLayout.addWidget(upperFreq,1,0)
            grpFreqLayout.addWidget(lblLowerFreq,0,1)
            grpFreqLayout.addWidget(lblUpperFreq,1,1)
            layout.addWidget(grpFreq)
            
            self.upperFreq = upperFreq
            self.lowerFreq = lowerFreq

        layout.addWidget(buttonBox)

    def useAllHandler(self):
        self.useAll = True
        self.accept()

    def getResult(self):
        result = {}
        if self.maxFreq:
            lowerFreq = self.lowerFreq.value()
            upperFreq = self.upperFreq.value()
            freq = (lowerFreq, upperFreq) if upperFreq>=lowerFreq else (upperFreq, lowerFreq)
            result['freq'] = None if self.useAll else freq
        if self.maxTime:
            lowerTime = self.lowerTime.value()
            upperTime = self.upperTime.value()
            time = (lowerTime, upperTime) if upperTime>=lowerTime else (upperTime, lowerTime) 
            result['time'] = None if self.useAll else time

        return result