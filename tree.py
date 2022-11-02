from __future__ import annotations
from pprint import pprint
from PyQt5.QtWidgets import (
    QMainWindow, QApplication,
    QLabel, QCheckBox, QComboBox, QLineEdit,
    QLineEdit, QSpinBox, QDoubleSpinBox, QSlider,
    QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGraphicsScene, QGraphicsView, QGraphicsItem
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, pyqtProperty, 
    QPropertyAnimation, QPoint, QEasingCurve,
    QParallelAnimationGroup, QObject
)
from PyQt5.QtGui import (
    QBrush, QPainter, QPen, QPixmap, QPolygonF
)
from PyQt5 import QtCore, QtGui
from PyQt5.uic import loadUi
import typing
import numpy as np 
import sys
import random
from copy import deepcopy
from typing import Callable, List
import enum
from collections import deque, namedtuple
from board import Board

Coord = namedtuple("Coord", "r c")

class mode(enum.Enum):
    BFS = 1 # breadth-first search
    UCS = 2 # uniform-cost search
    BestFS = 3  # Best-first search
    AS  = 4     # A*

class heur(enum.Enum):
    h1 = 1 # missed cells
    h2 = 2 # sum manhattan dist

class State:
    def __init__(self, table : np.ndarray, empty: Coord = None) -> None:
        self.table = table

        if empty is None:
            self.empty : Coord = self.find_empty(self.table)
        else: 
            self.empty = empty

    def find_empty(self, table) -> Coord:
        for r, row in enumerate(table):
            for c, el in enumerate(row):
                if el is None:
                    return Coord(r,c)
        raise Exception

    def moves(self) -> Coord:
        r,c = self.empty
        if r > 0:
            yield Coord(r-1, c)
        if r < 2:
            yield Coord(r+1, c)
        if c > 0:
            yield Coord(r, c-1)
        if c < 2:
            yield Coord(r, c+1)

    def __eq__(self, __o: State) -> bool:
        return np.array_equal(self.table, __o.table)

class Node:
    def __init__(
            self, 
            state : State, 
            parent : Node = None, 
            children : List[Node] = [], 
            depth : int = 0,
            target : State = None) -> None:
        self.state = state
        self.parent = parent
        self.children : List[Node] = []
        self.correct_child = None
        self.depth = depth
        self.target = target

        self.h1 : int = missed_count(self.state.table, self.target.table)
        self.h2 : int = mht_dist(self.state.table, self.target.table)

        self.g : int = depth

    def possible_nodes(self) -> List[Node]:
        nodes = []
        self.children.clear()
        r,c = self.state.empty
        for i in self.state.moves():
            table = np.copy(self.state.table)
            table[r][c], table[i.r][i.c] = table[i.r][i.c], table[r][c]
            node = Node(
                State(table, i), 
                parent=self, 
                depth=self.depth+1,
                target=self.target)
            # node.h1 = missed_count(self.state.table,self.target.table)
            # node.h2 = mht_dist(self.state.table,self.target.table)
            
            nodes.append(node)
            self.children.append(node)
        return nodes

    def astar_value(self, heur: heur):
        if heur == heur.h1:
            return self.g + self.h1
        elif heur == heur.h2:
            return self.g + self.h2

class PathFinder(QObject):
    finished = pyqtSignal()
    changeParam = pyqtSignal(int,int)
    def __init__(self, start: State, end: State, nextStep: Callable[[deque[Node],heur], Node], heur:heur = heur.h1) -> None:
        super().__init__()
        self.fringer : deque[Node] = None
        self.start_state = start
        self.end_state = end
        self.next_step_fcn = nextStep

        self.depth : int = None
        self.mem : int = None
        self.time : int = None

        self.no_solution : bool = False

        self.correct_path : List[Node] = []
        self.root : Node = None

        self.heur = heur

        self.no_abort = True

        self.emit_time = 0
        pass

    def makeTree(self):
        self.depth = 1
        self.mem = 1
        self.time = 0
        self.no_solution = False
        self.correct_path = []

        self.root = Node(self.start_state,target=self.end_state)
        self.fringer = deque([self.root])

        revealed = set()

        while len(self.fringer) and self.no_abort:
            node : Node = self.next_step_fcn(self.fringer, self.heur)


            hash_state = node.state.table.data.tobytes()
            if node.state == self.end_state:
                break
            if hash_state in revealed:
                continue
            
            revealed.add(hash_state)
            
            self.time += 1
            if self.time % 1000 == 0:
                self.changeParam.emit(len(revealed)+len(self.fringer), self.time)

            for next_node in node.possible_nodes():
                self.fringer.append(next_node)
            
        else:
            self.no_solution = True
            # raise Exception('No solution')
            self.finished.emit()
            return
        
        while node.parent is not None:
            self.correct_path.append(node)
            node.parent.correct_child = node
            node = node.parent
            # pprint(vars(node))
        self.correct_path.append(self.root)
        self.correct_path.reverse()

        self.mem = len(revealed) + len(self.fringer)
        self.depth = len(self.correct_path)

        self.finished.emit()
    
    def get_node_by_step(self, step: int):
        if not len(self.correct_path): return

        return self.correct_path[step]


def mht_dist(cur: np.ndarray, target: np.ndarray) -> int:
    table = [None]*Board.cols*Board.rows
    dist = 0

    for r, row in enumerate(target):
        for c, el in enumerate(row):
            if el is not None:
                table[el-1] = (r,c)
    for r, row in enumerate(cur):
        for c, el in enumerate(row):
            if el is not None:
                tr, tc = table[el-1]
                dist += abs(r-tr) + abs(c-tc)
    return dist

def missed_count(cur: np.ndarray, target: np.ndarray) -> int:
    cnt = 0
    for r, row in enumerate(cur):
        for c, el in enumerate(row):
            if el is not None:
                if el != target[r][c]:
                    cnt += 1
    return cnt

def bfs(fringer : deque[Node]) -> Node: 
    return fringer.popleft()

def ucs(fringer : deque[Node]) -> Node:
    min_node = fringer[0]
    min_idx = 0
    for idx, node in enumerate(fringer):
        if node.depth < min_node.depth:
            min_node = node
            min_idx = idx
    fringer.remove(min_node)
    return min_node

def bestFC(fringer : deque[Node], heur: heur) -> Node:
    min_node = fringer[0]
    for idx, node in enumerate(fringer):
        if node.h1 < min_node.h1 and heur == heur.h1 or node.h2 < min_node.h2 and heur == heur.h2:
            min_node = node
            min_idx = idx
    fringer.remove(min_node)
    return min_node
    

def astar(fringer : deque[Node], heur: heur) -> Node:
    min_node = fringer[0]
    for idx, node in enumerate(fringer):
        if node.astar_value(heur) < min_node.astar_value(heur):
            min_node = node
            min_idx = idx
    fringer.remove(min_node)
    return min_node


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback) 
    sys.exit(1)

def main():
    sys._excepthook = sys.excepthook 
    
    sys.excepthook = exception_hook



if __name__ == '__main__':
    main()
