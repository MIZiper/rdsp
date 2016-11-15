from guiqwt.tools import BaseCursorTool
from guiqwt.shapes import XRangeSelection, Marker
from guiqwt.builder import make
from guiqwt.label import ObjectInfo

import numpy as np
from rdsp import gl

class MofRange(ObjectInfo):
    def __init__(self, xrange, txy):
        self.xrange = xrange
        self.txy = txy

    def get_text(self):
        tt, xx, yy = self.txy
        x0, x1 = self.xrange.get_range()
        idx0 = np.searchsorted(xx,x0)
        idx1 = np.searchsorted(xx,x1)
        a = yy[idx0:idx1]
        return '%s: %f - %f' % (tt,a.min(),a.max())

class RangePickerTool(BaseCursorTool):
    TITLE = 'Range Picker'
    ICON = 'xrange.png'
    SWITCH_TO_DEFAULT_TOOL = True

    def create_shape(self):
        self.label = None
        return XRangeSelection(0,0)

    def end_move(self, filter, event):
        plot = filter.plot
        TXYs = gl.plotManager.getTXYs()
        comps = [MofRange(self.shape,txy) for txy in TXYs]
        label = make.info_label('TL',comps,'Min - Max')
        plot.add_item(label)

        if self.shape is not None:
            # TODO: popup context menu and act
            self.shape.detach()
            self.shape = None
            self.SIG_TOOL_JOB_FINISHED.emit()

from spyderlib.widgets.variableexplorer import arrayeditor
class RangeValueTool(BaseCursorTool):
    TITLE = 'Range Value'
    ICON = 'imagestats.png'
    SWITCH_TO_DEFAULT_TOOL = True

    def create_shape(self):
        return XRangeSelection(0,0)

    def end_move(self, filter, event):
        if self.shape is not None:
            plot = filter.plot
            TXYs = gl.plotManager.getTXYs()
            if len(TXYs)==1:
                editor = arrayeditor.ArrayEditor()
                tt,xx,yy = TXYs[0]
                x0,x1 = self.shape.get_range()
                idx0 = np.searchsorted(xx,x0)
                idx1 = np.searchsorted(xx,x1)
                a = np.array([xx[idx0:idx1],yy[idx0:idx1]])
                if editor.setup_and_check(a,tt):
                    editor.exec()

            self.shape.detach()
            self.shape = None
            self.SIG_TOOL_JOB_FINISHED.emit()

    # def update_status(self, plot):
    #     if gl.plotManager is None:
    #         self.action.setEnabled(False)
    #     else:
    #         txys = gl.plotManager.getTXYs()
    #         self.action.setEnabled(len(txys)==1)

class YofX(ObjectInfo):
    def __init__(self, xMark, txy):
        self.mark = xMark
        self.txy = txy

    def get_text(self):
        tt, xx, yy = self.txy
        x, y = self.mark.get_pos()
        if x<0 or x>xx[-1]:
            return 'Out'
        idx = np.searchsorted(xx,x)
        if xx[idx+1]==x: idx+=1

        return '%s: %f' % (tt,yy[idx])

class VCursorTool(BaseCursorTool):
    TITLE = 'VCursor'
    ICON = 'vcursor.png'
    SWITCH_TO_DEFAULT_TOOL = True

    def create_shape(self):
        self.label = None
        marker = Marker()
        marker.set_markerstyle('|')
        return marker

    def move(self, filter, event):
        super().move(filter, event)
        if self.label is None:
            plot = filter.plot
            TXYs = gl.plotManager.getTXYs()
            comps = [YofX(self.shape,txy) for txy in TXYs]
            label = make.info_label('TL',comps,'Ys')
            label.attach(plot)
            label.setZ(plot.get_max_z()+1)
            label.setVisible(True)
            self.label = label

    def end_move(self, filter, event):
        if self.label is not None:
            self.label.detach()
            self.label = None
        if self.shape is not None:
            self.shape.detach()
            self.shape = None
            self.SIG_TOOL_JOB_FINISHED.emit()
