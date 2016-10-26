from PyQt4.QtGui import (QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QSplashScreen, QPixmap, QProgressBar)
from PyQt4.QtCore import QSettings, Qt
from guidata.qthelpers import create_action, add_actions

from rdsp.widgets import ListWidget, PropertyWidget, PlotWidget
from rdsp.manager import ProjectManager, ModuleManager, ProgressManager, PlotManager
from rdsp import gl

from os import path

APPNAME = 'RDSP'

RECENT_PROJ = 'recentProj'
RECEN_MAT = 'recentMat'
MODULEDIR = 'modules/'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.recentSetting = QSettings('AHC','rdsp')
        self.initUI()
        self.resize(1024,768)

        gl.progressManager = ProgressManager(self.statusBar(),self.progress_bar)
        gl.plotManager = PlotManager(self.plot_widget)
        ProjectManager.RegisterListWidget(self.list_widget)

    def initUI(self):
        self.setWindowTitle(APPNAME)

        file_menu = self.menuBar().addMenu('File')
        new_proj_action = create_action(self, 'New Project', self.new_project)
        open_proj_action = create_action(self, 'Open Project', self.open_project)
        import_orosMat_action = create_action(self, 'Import Oros Mat', self.import_orosMat)
        quit_action = create_action(self, 'Quit', self.quit)
        add_actions(file_menu, (
            new_proj_action,open_proj_action,
            None,import_orosMat_action,None,quit_action
        ))

        progress_bar = QProgressBar(self)
        progress_bar.setFixedWidth(200)
        progress_bar.setTextVisible(False)
        progress_bar.setVisible(False)
        self.progress_bar = progress_bar
        self.statusBar().addPermanentWidget(progress_bar)

        main_widget = QWidget(self)
        main_layout = QGridLayout(main_widget)
        side_layout = QGridLayout()
        plot_widget = PlotWidget(main_widget)
        self.plot_widget = plot_widget

        list_widget = ListWidget()
        prop_widget = PropertyWidget()
        list_widget.registerPropertyWindow(prop_widget)
        side_layout.addWidget(list_widget,0,0)
        side_layout.addWidget(prop_widget,1,0)
        side_layout.setRowStretch(0,2)
        side_layout.setRowStretch(1,1)
        self.list_widget = list_widget

        main_layout.addLayout(side_layout,0,0)
        main_layout.addWidget(plot_widget,0,1)
        main_layout.setColumnStretch(0,1)
        main_layout.setColumnStretch(1,3)

        self.setCentralWidget(main_widget)

    def quit(self):
        self.close()

    def new_project(self):
        projFolder = QFileDialog.getExistingDirectory(self, 'Select a Folder',
            directory=self.recentSetting.value(RECENT_PROJ,''))
        if not projFolder: return

        self.recentSetting.setValue(RECENT_PROJ,projFolder)
        gl.projectManager = ProjectManager(projFolder)

    def open_project(self):
        filename = QFileDialog.getOpenFileName(self, 'Open Project File',
            filter='JSON File (*.json);;All (*.*)',
            directory=self.recentSetting.value(RECENT_PROJ,''))
        if not filename: return

        self.recentSetting.setValue(RECENT_PROJ,path.dirname(filename))
        gl.projectManager = ProjectManager(filename)

    def import_orosMat(self):
        if gl.projectManager is None:
            QMessageBox.warning(self, 'Import File', 'Open a project or create a new one first.')
            return

        filename = QFileDialog.getOpenFileName(self, 'Import Oros Mat File',
            filter='Matlab File (*.mat);;All (*.*)',
            directory=self.recentSetting.value(RECEN_MAT,''))
        if not filename: return

        self.recentSetting.setValue(RECEN_MAT,path.dirname(filename))
        gl.projectManager.importOrosMat(filename)

def progressTest(loi):
    # import time

    # # loi[5,0,0]
    # for i in range(5):
    #     time.sleep(1)
    #     loi[1] += 1

    # # loi[0,0,0]
    # time.sleep(5)

    gl.moduleManager = ModuleManager(
        path.join(path.dirname(__file__),MODULEDIR)
    )

    loi[2] = 1

def main():
    from guidata import qapplication
    app = qapplication()
    splash = QSplashScreen(QPixmap('test/splash.png'))
    splash.show()
    app.processEvents()
    win = MainWindow()
    win.show()
    splash.finish(win)
    gl.progressManager.startNewProgress('Loading Modules',progressTest,[0,0,0])
    app.exec()

if __name__ == '__main__':
    import sys
    sys.exit(int(main() or 0))