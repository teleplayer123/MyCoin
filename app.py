from PyQt5 import QtWidgets as widgets 
from PyQt5 import QtCore as core 
from PyQt5 import QtGui as gui 
import json
import sys

from miner import Miner
from storage.binbc import BlockchainStorage
from services.client import Client
from config import config
from tools.encrypt_decrypt_pwd import encrypt, decrypt
from storage.mempool import Mempool
from storage.user_data import PasswordPool
from storage.peers import Peers
from wallet import Transaction, Wallet


host = config["network"]["host"]
port = config["network"]["port"]
blockpool = BlockchainStorage()
peers = Peers()
mempool = Mempool()
client = Client(peers)
mine = Miner()


class App(widgets.QMainWindow):

    def new_wallet(self):
        self.setCentralWidget(CreateNewWallet())

    def new_transaction(self):
        self.setCentralWidget(NewTransaction())
        
    def create_account(self):
        self.setCentralWidget(AccountSetup())
    
    def tree_view(self):
        self.setCentralWidget(TreeView())

    def __init__(self):
        super().__init__()
        self.title = "My Coin"
        self.left = 100
        self.top = 100
        self.width = 600
        self.height = 550
        
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setCentralWidget(AccountSetup())

        mainMenu = self.menuBar()
        file = mainMenu.addMenu("File")

        new_user = widgets.QAction("Ceate Account", self)
        file.addAction(new_user)
        new_user.triggered.connect(self.create_account)

        new_keys = widgets.QAction("New Wallet", self)
        file.addAction(new_keys)
        new_keys.triggered.connect(self.new_wallet)

        new_trans = widgets.QAction("New Transaction", self)
        file.addAction(new_trans)
        new_trans.triggered.connect(self.new_transaction)

        home = widgets.QAction("View Transactions", self)
        file.addAction(home)
        home.triggered.connect(self.tree_view)
        
        exitButton = widgets.QAction(gui.QIcon("exit24.png"), "Exit", self)
        exitButton.setShortcut("Ctrl+Q")
        exitButton.setStatusTip("Exit Application")
        exitButton.triggered.connect(self.close)
        file.addAction(exitButton)
    
    
class TreeView(widgets.QWidget):

    TXT_HASH, SENDER, AMOUNT, TIME = range(4)

    def __init__(self):
        super().__init__()
        self.group_box = widgets.QGroupBox("Transactions")
        self.data_view = widgets.QTreeView()
        self.data_view.setRootIsDecorated(False)
        self.data_view.setAlternatingRowColors(True)
 
        data_layout = widgets.QHBoxLayout()
        data_layout.addWidget(self.data_view)
        self.group_box.setLayout(data_layout)

        self.model = self.createModel(self)
        self.data_view.setModel(self.model)

        trans = blockpool.get_trans_from_last_block()
        for t in trans:
            self.set_data(t["txt_hash"], t["sender_address"], t["amount"], t["timestamp"])
        

        main_layout = widgets.QVBoxLayout() 
        main_layout.addWidget(self.group_box)
        self.setLayout(main_layout)

    def createModel(self, parent):
        model = gui.QStandardItemModel(0, 4, parent)
        model.setHeaderData(self.TXT_HASH, core.Qt.Horizontal, "Text Hash")
        model.setHeaderData(self.SENDER, core.Qt.Horizontal, "Sender")
        model.setHeaderData(self.AMOUNT, core.Qt.Horizontal, "Amount")
        model.setHeaderData(self.TIME, core.Qt.Horizontal, "Time")
        return model

    def set_data(self, txt_hash, sender, amount, time):
        model = self.model
        model.insertRow(0)
        model.setData(model.index(0, self.TXT_HASH), txt_hash)
        model.setData(model.index(0, self.SENDER), sender)
        model.setData(model.index(0, self.AMOUNT), amount)
        model.setData(model.index(0, self.TIME), time)


class AccountSetup(widgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = widgets.QVBoxLayout()
        group_box = widgets.QGroupBox()
        layout = widgets.QFormLayout()

        self.username = widgets.QLineEdit(self)
        self.password1 = widgets.QLineEdit(self)
        self.password2 = widgets.QLineEdit(self)
        question_combo = widgets.QComboBox(self)
        self.secret = widgets.QLineEdit(self)
        self.question_label = widgets.QLabel(self)

        question_combo.addItem("Name of your first pet?")
        question_combo.addItem("Name of elementry school you went to?")
        question_combo.addItem("Name of first street lived on?")
        question_combo.addItem("Mothers maiden name?")        

        question_combo.activated[str].connect(self.onActivated)

        self.button = widgets.QPushButton("submit", self)

        layout.addRow(widgets.QLabel("Enter username"), self.username)
        layout.addRow(widgets.QLabel("Enter password: "), self.password1)
        layout.addRow(widgets.QLabel("Verify password: "), self.password2)
        layout.addRow(question_combo)
        layout.addRow(self.question_label, self.secret)
        layout.addRow(self.button)
        
        group_box.setLayout(layout)
        main_layout.addWidget(group_box)
        self.setLayout(main_layout)

        self.button.clicked.connect(self.on_click)
    
    def clear(self):
        self.username.clear
        self.password1.clear
        self.password2.clear
        self.secret.clear

    def onActivated(self, text):
        self.question_label.setText(text)
        
    def on_click(self): 
        if self.password1.text() != self.password2.text():
            widgets.QMessageBox.information(self, "msg", "passwords did not match", widgets.QMessageBox.Ok)

        password = self.password1.text()
        username = self.username.text()
        question = self.question_label.text()
        secret = self.secret.text()
        data, key = encrypt(password, secret)
        pool = PasswordPool()
        pool.store_data(username, question, key, data)
        widgets.QMessageBox.information(self, "msg", "Account Created", widgets.QMessageBox.Ok)


class CreateNewWallet(widgets.QWidget):
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = widgets.QVBoxLayout()
        group_box = widgets.QGroupBox()
        layout = widgets.QFormLayout()

        self.wallet_name = widgets.QLineEdit(self)
        self.password = widgets.QLineEdit(self)
        self.password.setEchoMode(widgets.QLineEdit.EchoMode.Password)

        self.button = widgets.QPushButton("Create Wallet")

        layout.addRow(widgets.QLabel("Wallet Name: "), self.wallet_name)
        layout.addRow(widgets.QLabel("Create Password: "), self.password)
        layout.addRow(self.button)

        group_box.setLayout(layout)
        main_layout.addWidget(group_box)
        self.setLayout(main_layout)

        self.button.clicked.connect(self.new_wallet)

    def new_wallet(self):
        wallet_name = self.wallet_name.text()
        password = self.password.text()
        verify_pass = self.get_input("Verify password: ")
        wallet = Wallet(wallet_name)
        res = wallet.create_wallet(password, verify_pass)
        widgets.QMessageBox.information(self, "msg", str(res), widgets.QMessageBox.Ok)
        self.wallet_name.setText("")
        self.password.setText("")
        return 

    def get_input(self, msg):
        text, ok = widgets.QInputDialog.getText(self, "Get Text", msg, widgets.QLineEdit.EchoMode.Password)
        if ok and text != "":
            return text


class NewTransaction(widgets.QWidget):

    def __init__(self):
        super().__init__() 
        layout = widgets.QVBoxLayout()
        group_box = widgets.QGroupBox()
        form_layout = widgets.QFormLayout()

        self.recipient_line = widgets.QLineEdit(self)
        self.amount_line = widgets.QLineEdit(self)
        self.wallet_name_line = widgets.QLineEdit(self)

        button = widgets.QPushButton("New Transaction", self) 
        button.clicked.connect(self.on_click)

        form_layout.addRow(widgets.QLabel("Recipient Address: "), self.recipient_line)
        form_layout.addRow(widgets.QLabel("Amount: "), self.amount_line)
        form_layout.addRow(widgets.QLabel("Wallet Name: "), self.wallet_name_line)

        group_box.setLayout(form_layout)
        layout.addWidget(group_box)
        layout.addWidget(button)
        self.setLayout(layout)

    def on_click(self):
        rv = self.recipient_line.text()
        av = self.amount_line.text()
        wv = self.wallet_name_line.text()
        wallet = Wallet(wv)
        pwd = self.get_input("Enter password: ")
        trans = wallet.new_transaction(rv, int(av), pwd)
        res = client.broadcast_unconfirmed_transaction(trans)
        if res.status_code == 201:
            choice = widgets.QMessageBox.question(self, "msg", "Another Transaction?", widgets.QMessageBox.Yes|widgets.QMessageBox.No)
            if choice == widgets.QMessageBox.Yes:
                self.recipient_line.setText("")
                self.amount_line.setText("")
                self.wallet_name_line.setText("")    
                return
            else:
                #todo: change to home page
                self.recipient_line.setText("")
                self.amount_line.setText("")
                self.wallet_name_line.setText("") 
                return

    def get_input(self, msg):
        text, ok = widgets.QInputDialog.getText(self, "Get Text", msg, widgets.QLineEdit.EchoMode.Password)
        if ok and text != "":
            return text


if __name__ == "__main__":
    app = widgets.QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())