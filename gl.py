moduleManager = None
projectManager = None
plotManager = None
progressManager = None

# this can be used not called by 'main', so in 'gl'
from PyQt4 import QtGui
def aw(self, w):
    self.addWidget(w)
    return self
setattr(QtGui.QLayout,'aw',aw)