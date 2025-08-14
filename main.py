import chess
import json
import pandas as pd
import chess.pgn
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit
)
from PyQt5.QtGui import QPixmap
import chess.svg
import cairosvg

# Load data
with open("data.json", "r") as f:
    data = json.load(f)

# ---------- Your ELO logic ----------
def _who_won(pgn_path):
    with open(pgn_path) as pgn:
        game = chess.pgn.read_game(pgn)
        result = game.headers["Result"]
        if result == "1-0":
            return 1.0, 0.0
        elif result == "0-1":
            return 0.0, 1.0
        else:
            return 0.5, 0.5

def _expected_score(playerA, playerB):
    diff = (playerB - playerA) / 400
    odds = 10 ** diff
    eA = 1 / (1 + odds)
    eB = 1 - eA
    return eA, eB

def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))

def underdog_fac(playerA,playerB):
    D=400
    F_MAX = 1.5
    diff = playerB-playerA
    _underdog_factor = 1+clamp(diff/D,0,F_MAX-1)
    return _underdog_factor

def _k_factor(R,RO):
    k_min=5
    k_max=20
    r_m=2000
    s_c = 150 #controls the steepness of the curve
    k_base = k_min+(k_max-k_min)/(1+((2.718)**(R-r_m)/s_c))
    #k_base 

    underdog_factor=underdog_fac(R,RO)

    k = clamp(k_min,k_base*underdog_factor,k_max)
    return k

def _new_rating(k, rating_of_a, expected_of_a, white, rating_of_b, expected_of_b, black):
    new_rating_of_a = rating_of_a + k * (white - expected_of_a)
    new_rating_of_b = rating_of_b + k * (black - expected_of_b)
    return new_rating_of_a, new_rating_of_b

def update_elo_from_pgn(pgn_path):
    with open("data.json", "r") as f:
        data = json.load(f)

    base_playerA = data["player1_elo_rating"]
    base_playerB = data["player2_elo_rating"]
    white, black = _who_won(pgn_path)
    ea, eb = _expected_score(base_playerA, base_playerB)
    k = _k_factor(base_playerA,base_playerB)
    updated_rating_a, updated_rating_b = _new_rating(
        k, base_playerA, ea, white, base_playerB, eb, black
    )
    data["player1_elo_rating"] = updated_rating_a
    data["player2_elo_rating"] = updated_rating_b

    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

    return updated_rating_a, updated_rating_b





#
#
#
#
# ---------- UI Code ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Elo")
        self.setGeometry(100, 100, 900, 600)
        self.pgn_path = None  # Store uploaded PGN path

        # Main container
        container = QWidget()
        layout = QHBoxLayout(container)

        # ----- Left: Chess board -----
        self.board_label = QLabel()
        layout.addWidget(self.board_label, stretch=3)

        # ----- Right: Info panel -----
        right_panel = QVBoxLayout()

        # Player ELO labels
        self.player1_label = QLabel(f"Player 1 ELO: {data['player1_elo_rating']}")
        self.player2_label = QLabel(f"Player 2 ELO: {data['player2_elo_rating']}")
        self.player1_label.setStyleSheet("font-size: 18px;")
        self.player2_label.setStyleSheet("font-size: 18px;")
        right_panel.addWidget(self.player1_label)
        right_panel.addWidget(self.player2_label)

        # Upload & Start buttons
        upload_btn = QPushButton("Upload PGN")
        upload_btn.clicked.connect(self.upload_pgn)
        right_panel.addWidget(upload_btn)

        start_btn = QPushButton("Start")
        start_btn.clicked.connect(self.start_game)
        right_panel.addWidget(start_btn)

        # Manual ELO change section
        right_panel.addWidget(QLabel("Change Player 1 ELO:"))
        self.player1_input = QLineEdit(str(data['player1_elo_rating']))
        right_panel.addWidget(self.player1_input)

        right_panel.addWidget(QLabel("Change Player 2 ELO:"))
        self.player2_input = QLineEdit(str(data['player2_elo_rating']))
        right_panel.addWidget(self.player2_input)

        save_btn = QPushButton("Save ELO Changes")
        save_btn.clicked.connect(self.save_elo_changes)
        right_panel.addWidget(save_btn)

        right_panel.addStretch()
        layout.addLayout(right_panel, stretch=1)

        self.setCentralWidget(container)
        self.update_board_display()

    def update_board_display(self):
        board = chess.Board()
        svg_code = chess.svg.board(board=board, size=500)
        cairosvg.svg2png(bytestring=svg_code.encode("utf-8"), write_to="board.png")
        pixmap = QPixmap("board.png")
        self.board_label.setPixmap(pixmap)

    def upload_pgn(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PGN File", "", "PGN Files (*.pgn)")
        if file_path:
            self.pgn_path = file_path
            print(f"PGN Uploaded: {file_path}")

    def start_game(self):
        if self.pgn_path:
            new_a, new_b = update_elo_from_pgn(self.pgn_path)
            self.player1_label.setText(f"Player 1 ELO: {new_a}")
            self.player2_label.setText(f"Player 2 ELO: {new_b}")
            print(f"ELO Updated: Player 1 = {new_a}, Player 2 = {new_b}")
        else:
            print("No PGN uploaded.")

    def save_elo_changes(self):
        try:
            new_a = float(self.player1_input.text())
            new_b = float(self.player2_input.text())
            with open("data.json", "r") as f:
                data = json.load(f)
            data["player1_elo_rating"] = new_a
            data["player2_elo_rating"] = new_b
            with open("data.json", "w") as f:
                json.dump(data, f, indent=4)
            self.player1_label.setText(f"Player 1 ELO: {new_a}")
            self.player2_label.setText(f"Player 2 ELO: {new_b}")
            print(f"ELO Manually Updated: Player 1 = {new_a}, Player 2 = {new_b}")
        except ValueError:
            print("Invalid ELO value entered.")

if __name__ == "__main__":
    app = QApplication([])
    mw = MainWindow()
    mw.show()
    app.exec()
