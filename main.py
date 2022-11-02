
from pprint import pprint
from time import sleep
from PyQt5.QtWidgets import (
    QMainWindow, QApplication,
    QLabel, QCheckBox, QComboBox, QLineEdit,
    QLineEdit, QSpinBox, QDoubleSpinBox, QSlider,
    QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QMessageBox
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, pyqtProperty, 
    QPropertyAnimation, QPoint, QEasingCurve,
    QParallelAnimationGroup , QSize, QRunnable, QThreadPool,
    QThread
)
from PyQt5 import QtCore, QtTest
from PyQt5.uic import loadUi
import typing
import numpy as np 
import sys
import random
from copy import deepcopy
from typing import Union 
import enum
from board import Board, Cell
from tree import mode, heur
import tree

class brds(enum.Enum):
    Start   = 1
    Cur     = 2
    End     = 3



class Main(QWidget):
    
    # self.steps_lbl : QLabel
    # self.cur_step_le : QLineEdit
    # self.slider : QSlider
    # bfs_btn : QPushButton
    # as_btn : QPushButton
    # self.sw_shuffle_btn : QPushButton
    # self.ew_shuffle_btn : QPushButton
    # self.sw_reset_btn : QPushButton
    # self.ew_reset_btn : QPushButton
    # self.prev_btn : QPushButton
    # self.next_btn : QPushButton
    # self.memory_lbl: QLabel
    # self.time_lbl: QLabel
    # self.calc_btn : QPushButton
    
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('main.ui', self)
        bl = QVBoxLayout()
        self.mw.setLayout(bl)
        self.b = Board(selectable=False)
        bl.addWidget(self.b)

        bl_s = QVBoxLayout()
        self.sw.setLayout(bl_s)
        self.start_board = Board()
        bl_s.addWidget(self.start_board)

        bl_e = QVBoxLayout()
        self.ew.setLayout(bl_e)
        self.end_board = Board()
        bl_e.addWidget(self.end_board)

        self.resetTables(True)

        #self.btn.clicked.connect(lambda : self.b.ChangeTo())
        self.mode = mode.BestFS
        self.heur = heur.h1

        self.pathFinder : tree.PathFinder = None

        self.curStep = 0
        self.inCalc : bool = False

        self.node : tree.Node = None

        self.sw_shuffle_btn.clicked.connect(lambda _ : self.shuffleTable(brds.Start))
        self.ew_shuffle_btn.clicked.connect(lambda _ : self.shuffleTable(brds.End))
        self.sw_reset_btn.clicked.connect(lambda _ : self.resetTable(brds.Start))
        self.ew_reset_btn.clicked.connect(lambda _ : self.resetTable(brds.End))
        self.calc_btn.clicked.connect(self.calc)
        self.bfs_btn.clicked.connect(lambda : self.changeMode(mode.BestFS))
        self.as_btn.clicked.connect(lambda : self.changeMode(mode.AS))
        self.mc_btn.clicked.connect(lambda : self.changeHeur(heur.h1))
        self.mht_btn.clicked.connect(lambda : self.changeHeur(heur.h2))

        self.start_board.boardChanged.connect(self.resetCur)
        self.start_board.boardChanged.connect(self.updateInv)
        self.end_board.boardChanged.connect(self.resetCur)
        self.end_board.boardChanged.connect(self.updateInv)

        self.slider : QSlider
        self.slider.valueChanged.connect(self.on_slider_changed)
        self.cur_step_le.editingFinished.connect(self.on_le_edit)

        self.prev_btn.clicked.connect(lambda: self.changeStep(self.curStep-1,-1))
        self.next_btn.clicked.connect(lambda: self.changeStep(self.curStep+1, 1))

        self.b.cellPressed.connect(self.cellPressed)
        self.back_btn.clicked.connect(self.on_back_btn_press)
    
    def on_back_btn_press(self):
        if self.node is None: return
        if self.node.parent is None: return

        if self.node is self.node.parent.correct_child:
            self.changeStep(self.curStep-1,-1)
        else:
            self.force_node(self.node.parent)


    def cellPressed(self, cell: Cell, point:QPoint):
        # pprint(vars(cell))
        if cell.hidden_text is None: return
        for i in self.node.children:
            if i.state.table[point.y()][point.x()] != self.b.table[point.y()][point.x()]:
                if self.node.correct_child is i:
                    self.changeStep(self.curStep+1,1)
                else:
                    self.force_node(i)
                return

    def updateInv(self):
        self.st_inv_lbl.setText(str(self.start_board.inv_count()))
        self.en_inv_lbl.setText(str(self.end_board.inv_count()))

    def on_slider_changed(self, value):
        if value == self.curStep: return
        
        # self.skipSteps(self.curStep, value)
        self.changeStep(value)
        self.curStep = value

    def on_le_edit(self):
        if self.pathFinder is None: return
        if self.pathFinder.no_solution: return
        # self.cur_step_le : QLineEdit
        s = self.cur_step_le.text()
        if s.isnumeric() and 0 <= int(s) < self.pathFinder.depth:
            # self.changeStep(int(s))
            self.skipSteps(self.curStep, int(s))
        else:
            self.cur_step_le.setText("")

    def skipSteps(self, from_step, to_step):
        # tables = []
        # one_step = 1 if from_step < to_step else -1
        # for i in range(from_step, to_step+one_step, one_step):
        #     tables.append(self.pathFinder.get_node_by_step(i).state.table)
        # self.b.sequence_anim(tables, QEasingCurve.OutCubic,500,from_step,one_step,self.on_step_anim, self)
        # self.curStep = to_step
        # return
        if (from_step == to_step): return
        one_step = 1 if from_step < to_step else -1
        maxT = 5000
        max_anim_step = 250
        t = min(int(maxT/(abs(to_step-from_step))), max_anim_step)
        for i in range(from_step, to_step+one_step, one_step):
            self.changeStep(i, time=t)
            # QThread.msleep(int(500/(abs(to_step-from_step))))
            QtTest.QTest.qWait(t)
            # while self.b.animGroup.duration() < self.b.animGroup.totalDuration(): ...
            self.curStep = i

        self.curStep = to_step
        pass
    def on_step_anim(obj, self, step: int, time):
        if self.pathFinder is None: return
        if self.pathFinder.no_solution: return

        if not 0 <= step < self.pathFinder.depth: return

        node = self.pathFinder.get_node_by_step(step)
        
        for i in self.b.widgets:
            i.setColor(bg='',bc='')
        
        
        if step != 0:
            par = node.parent
            zipped = np.dstack((node.state.table, par.state.table))
            for _ in zipped:
                for cur, old in _:
                    if cur != old and cur is not None:
                        self.b.widgets[cur-1].setColor(bg = "",bc="lightgreen")
        if step != self.pathFinder.depth-1:
            ch : tree.Node = node.correct_child
            zipped = np.dstack((node.state.table, ch.state.table))
            for _ in zipped:
                for cur, nxt in _:
                    if cur != nxt and cur is not None:
                        self.b.widgets[cur-1].setColor(bg = "",bc="lightyellow")
        
        self.force_node(node, False)
        # self.b.ChangeTo(node.state.table, curve=QEasingCurve.OutCubic, time=time)
        self.slider.blockSignals(True)
        self.slider.setValue(step)
        self.slider.blockSignals(False)
        self.cur_step_le.setText(str(step))

    def changeStep(self, step: int, change_step : int = 0, time:int = 500):
        if self.pathFinder is None: return
        if self.pathFinder.no_solution: return

        if not 0 <= step < self.pathFinder.depth: return

        node = self.pathFinder.get_node_by_step(step)
        
        for i in self.b.widgets:
            i.setColor(bg='',bc='')
        
        
        if step != 0:
            par = node.parent
            zipped = np.dstack((node.state.table, par.state.table))
            for _ in zipped:
                for cur, old in _:
                    if cur != old and cur is not None:
                        self.b.widgets[cur-1].setColor(bg = "",bc="lightgreen")
        if step != self.pathFinder.depth-1:
            ch : tree.Node = node.correct_child
            zipped = np.dstack((node.state.table, ch.state.table))
            for _ in zipped:
                for cur, nxt in _:
                    if cur != nxt and cur is not None:
                        self.b.widgets[cur-1].setColor(bg = "",bc="lightyellow")
        
        self.force_node(node, time=time)
        # self.b.ChangeTo(node.state.table, curve=QEasingCurve.OutCubic, time=time)
        self.slider.blockSignals(True)
        self.slider.setValue(step)
        self.slider.blockSignals(False)
        self.cur_step_le.setText(str(step))
        self.curStep += change_step
        

    def resetInfo(self):
        self.steps_lbl.setText("---")
        self.cur_step_le.setText("")
        self.slider.setValue(0)
        self.slider.setMaximum(0)
        self.memory_lbl.setText("---")
        self.time_lbl.setText("---")
    
    def resetTable(self, board : Union[Board, brds], silent : bool = False):
        if silent:
            if board is self.start_board or board is brds.Start:
                self.start_board.SetTo(Board.start_pos)
                self.resetInfo()
            elif board is self.end_board or board is brds.End:
                self.end_board.SetTo(Board.end_pos)
                self.resetInfo()
            elif board is self.b or board is brds.Cur:
                self.b.SetTo(self.start_board.table)
                for i in self.b.widgets:
                    i.setColor(bg='', bc = '')
                self.b.hoverable = False
            return

        if board is self.start_board or board is brds.Start:
            self.start_board.ChangeTo(Board.start_pos)
            self.resetInfo()
        elif board is self.end_board or board is brds.End:
            self.end_board.ChangeTo(Board.end_pos)
            self.resetInfo()
        elif board is self.b or board is brds.Cur:
            self.b.ChangeTo(self.start_board.table)
            for i in self.b.widgets:
                i.setColor(bg='', bc = '')
            self.b.hoverable = False

    def resetTables(self, silent : bool = False):
        self.resetTable(brds.Start, silent)
        self.resetTable(brds.End, silent)
        self.resetTable(brds.Cur, silent)
        self.updateInv()

    def resetCur(self):
        self.resetTable(brds.Cur)
        self.resetInfo()

    def shuffleTable(self, board : Union[Board, brds]):
        if board is self.start_board or board is brds.Start:
            self.start_board.ChangeTo()
            self.resetInfo()
        elif board is self.end_board or board is brds.End:
            self.end_board.ChangeTo()
            self.resetInfo()
        elif board is self.b or board is brds.Cur:
            self.b.ChangeTo()
    def changeHeur(self, heur : heur):
        if heur is heur.h1:
            self.mc_btn.setChecked(True)
            self.mht_btn.setChecked(False)
        elif heur is heur.h2:
            self.mht_btn.setChecked(True)
            self.mc_btn.setChecked(False)
        if heur != self.heur:
            self.heur = heur    
            self.resetInfo()
            self.resetTable(brds.Cur)

    def changeMode(self, mode : mode):
        if mode is mode.BestFS:
            if not self.bfs_btn.isChecked():    # enable as
                self.as_btn.setChecked(True)
                self.mode = mode.AS
            else:                               # enable BestFS
                self.as_btn.setChecked(False)
                self.mode = mode.BestFS
        elif mode is mode.AS:  
            if not self.as_btn.isChecked():    # enable BestFS
                self.bfs_btn.setChecked(True)
                self.mode = mode.BestFS
            else:                               # enable as
                self.bfs_btn.setChecked(False)
                self.mode = mode.AS
        self.resetInfo()
        self.resetTable(brds.Cur)
        


    def calc(self):
        if self.inCalc:
            self.pathFinder.no_abort = False
            # if not self.thread.wait(5000):
            #     self.thread.terminate()
            #     print("here")
            #     self.thread.wait()
            #     print("and here")
            return

        func = None
        if self.mode == mode.BestFS:
            func = tree.bestFC
        elif self.mode == mode.AS:
            func = tree.astar

        self.pathFinder = tree.PathFinder(
            tree.State(self.start_board.table),
            tree.State(self.end_board.table),
            func,
            heur=self.heur
        )
        self.thread = QThread()
        self.pathFinder.moveToThread(self.thread)
        
        self.thread.started.connect(self.pathFinder.makeTree)
        self.pathFinder.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.on_thread_finish)
        self.thread.finished.connect(self.thread.deleteLater)
        self.pathFinder.changeParam.connect(self.changeTreeParam)

        self.inCalc = True
        self.calc_btn.setText("Cancel")
        self.thread.start()
        # self.pathFinder.makeTree()

    def changeTreeParam(self, mem, time):
        self.memory_lbl.setText(str(mem))
        self.time_lbl.setText(str(time))
    
    def on_thread_finish(self):
        self.inCalc = False
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowTitle("Solution finder")
        if self.pathFinder.no_solution:
            msgBox.setText("No solution :(")
        else:
            msgBox.setText("Solution found")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.exec()

        self.calc_btn.setText("Calc")
        self.initInfo()

    def initInfo(self):
        self.b.hoverable = False
        if self.pathFinder is None: return
        if self.pathFinder.no_solution: return

        self.curStep = 0
        self.memory_lbl.setText(str(self.pathFinder.mem))
        self.time_lbl.setText(str(self.pathFinder.time))
        self.slider.setMaximum(self.pathFinder.depth-1)
        self.slider.setMinimum(0)
        self.slider.setValue(self.curStep)
        self.steps_lbl.setText(str(self.pathFinder.depth-1))
        self.cur_step_le.setText(str(self.curStep))

        self.b.hoverable = True
        self.force_node(self.pathFinder.root)

    def force_node(self, node: tree.Node, need_change : bool = True, time : int = 500):
        if node is None: return
        self.node = node
        if need_change:
            self.b.ChangeTo(node.state.table, QEasingCurve.OutCubic, time)
        for i in self.b.widgets:
            i.hidden_text = None
            i.setColor(bg='',bc='')
        if len(node.children) == 0 : return
        for n in node.children:
            for r, row in enumerate(node.state.table):
                for c, el in enumerate(row):
                    if el is not None:
                        if el != n.state.table[r][c]:

                            h = n.h1 if self.heur is heur.h1 else n.h2
                            bc = ''
                            if node.correct_child is not None and n is node.correct_child:
                                self.b.widgets[el-1].setColor(bc="lightgreen",bg='')
                                bc = 'lightyellow'
                            col_num = 100
                            if self.mode is mode.BestFS:
                                col_num = int( 255 * (8-n.h1) / 8)
                                self.b.widgets[el-1].hidden_text = \
                                    f"h(n) = {h}"
                            elif self.mode is mode.AS:
                                fst = self.pathFinder.correct_path[0]
                                last = self.pathFinder.correct_path[-1]
                                mx = last.g + (last.h1 if  self.heur is heur.h1 else last.h2)
                                cur = n.g + h
                                if (mx):
                                    col_num = int(cur * 255.0 / mx )
                                else:
                                    print(mx)
                                self.b.widgets[el-1].hidden_text = \
                                    f"g(n) = {n.g}\n" + \
                                    f"h(n) = {h}\n" + \
                                    f"f(n) = {n.g + h}"
                            # print(col_num)
                            hx = f'#30{col_num:0>2X}30'
                            self.b.widgets[el-1].setColor(bc=bc, bg = hx)

        pass

def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback) 
    sys.exit(1)

def main():
    sys._excepthook = sys.excepthook 

    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    b = Main()
    b.show()
    app.exec()



if __name__ == '__main__':
    main()
