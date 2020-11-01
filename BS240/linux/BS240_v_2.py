import tkinter as tk
import tkinter.ttk as ttk
from cryptography.fernet import Fernet
import serial
import repeatedTimer
import serial.tools.list_ports
import serial.urlhandler
import os
import sys
import time
import threading
import pyodbc
import platform
import socket
py3 = True


'''this class is responsible for uploading results on database'''
class Db_Update():
    '''
        DO NOT ADJUST FOR A DIFFERENT DEVICE; THIS FUNCTIONG NEED TO BE ADJUSTED ACCORDING TO THE CHANGES IN THE
        PARAMETERS OF THE DATABASE
    '''
    def read_parameters(self):
        try:
            self.main_win.set()
            db = open(self.main_win.file_path + '/'+self.main_win.device_name+'/run/' + 'db_parameters', 'rb')
            x = db.read()
            x = [i.decode() for i in x.split(b'|')]
            self.main_win.server = x[0]
            self.main_win.psw = x[1]
            del x
        except:
           self.main_win.show('\nERROR, there is no initialization data base parameters')

    '''DO NOT ADJUST'''
    def __init__(self,main_win):
        self.main_win = main_win

    localCode = {'037':'037','053':'053','041':'041' }

    '''
        THIS FUNCTION SHOULD NOT BE CHANGED FOR DIFFERENT DEVICE BUT IT NEEDS!!!
        TO BE ALTERED DEPENDING ON DATABASE
    '''
    def run(self):
        print('writing to db')
        print(self.main_win.unwritten_results)
        try:
            while self.main_win.unwritten_results:
                string_to_write = self.main_win.resultReader(self.main_win.unwritten_results[0])
                print(string_to_write)
                CaseNo = self.main_win.unwritten_results[0]
                print(CaseNo)
                cnxn = pyodbc.connect(
                    'DRIVER={SQL Server};SERVER=SRV-001\SQLEXP2014;DATABASE=TMC-LAB2;UID=sa;PWD=tmc$qL123')
                print('connected to db')
                cursor = cnxn.cursor()
                print('cursor create')
                cursor.execute("select CaseID from CaseTBL where CaseNo = \'" + CaseNo + "\'")
                Case_ID = []
                for row in cursor:
                    Case_ID.append(row[0])
                print('case id', Case_ID)
                cursor.execute('''
                                select AnalysisCode
                                from Analysis as a
                                inner join Case_Analysis_Link as CAL
                                on a.AnalysisID=CAL.AnalysisID
                                inner join CaseTBL as CBL
                                on CAL.CaseID=CBL.CaseID
                                where CBL.CaseID=''' + str(Case_ID[0]) + ''' and a.Device = 'AIA360';
                                ''')
                Analysis_code = []
                for row in cursor:
                    Analysis_code.append(row[0])
                print(Analysis_code)
                cursor.commit()
                for analysis in range(len(Analysis_code)):
                    if not Analysis_code[analysis]:
                        del Analysis_code[analysis]
                for analysis in Analysis_code:
                    cursor.execute('''
                                    select  CaseAnalysisID
                                    from Analysis a
                                    inner join Case_Analysis_Link cal on a.AnalysisID=cal.AnalysisID
                                    where AnalysisCode=\'''' + analysis + '''\' and CaseID=''' + str(Case_ID[0])
                                   )
                    Case_Analysis_ID = []
                    for row in cursor:
                        Case_Analysis_ID.append(row[0])
                    print(Case_Analysis_ID)
                    cursor.commit()
                    try:
                        cursor.execute('''
                                        insert into Result (AnalysisResult,CaseAnalysisID) VALUES (\'''' + string_to_write[
                            'measurement'+self.localCode[analysis]] + '''\',''' + str(
                            Case_Analysis_ID[0]) + ''')
                                        '''
                                       )
                        cursor.commit()
                    except KeyError:
                        print('key error')
                cursor.close()
                cnxn.close()
                del self.main_win.unwritten_results[0]
                del string_to_write
        except:
            print('no DB')

class Database_setting(threading.Thread):
    daemon = True

    '''DO NOT ADJUST AT ALL;'''
    def set(self,main_win):
        self.main_win = main_win

    '''
        DO NOT ADJUST AT ALL EXCEPT IF THERE WERE CHANGES ON DB PARAMETERS; this function is responsible for saving
        data base parameters encrypted in a file saved in run
    '''
    def set_clicked(self,p1):
        self.main_win.set()
        self.main_win.path_changer('main')
        self.main_win.path_changer('run')
        db = open(self.main_win.file_path + '/'+self.main_win.device_name+'/run/' + 'db_parameters', 'wb+')
        db.write(b'')
        db.close()
        db = open(self.main_win.file_path + '/'+self.main_win.device_name+'/run/' + 'db_parameters', 'ab+')
        parms =[i.encode() for i in [self.server_entry.get(),self.psw_entry.get(),self.table_entry.get(),self.uid_entry.get(),self.database_entry.get()]]
        db.write(b'|'.join(parms))
        db.close()
        del parms

    '''
        DO NOT ADJUST AT ALL EXCEPT IF THERE WERE CHANGES ON DB PARAMETERS;
        this one puts data base parameters in the entries
    '''
    def database_initialize(self):
        try:
            self.main_win.set()
            db = open(self.main_win.file_path + '/'+self.main_win.device_name+'/run/' + 'db_parameters', 'rb')
            x = db.read()
            x = [i.decode() for i in x.split(b'|')]
            self.server_entry.insert(0,x[0])
            self.psw_entry.insert(0,x[1])
            self.table_entry.insert(0,x[2])
            self.uid_entry.insert(0,x[3])
            self.database_entry.insert(0,x[4])
            del x
        except:
           self.main_win.show('\nERROR, there is no initialization data base parameters')
       #     return

    '''DO NOT ADJUST AT ALL'''
    '''initialize the main database parameters'''
    def connect_clicked(self,p1):
        self.main_win.db_writer.read_parameters()
        print('here i am')
        self.root.destroy()

    '''DO NOT ADJUST AT ALL'''
    def cancel_clicked(self,p1):
        self.root.destroy()
    '''THIS IS RESPONSIBLE FOR CREATING INITIALIZING THE WINDOW'''
    def run(self,):
        '''This class configures and populates the toplevel window.
           top is the toplevel containing window.'''
        _bgcolor = '#d9d9d9'  # X11 color: 'gray85'
        _fgcolor = '#000000'  # X11 color: 'black'
        _compcolor = '#d9d9d9' # X11 color: 'gray85'
        _ana1color = '#d9d9d9' # X11 color: 'gray85'
        _ana2color = '#ececec' # Closest X11 color: 'gray92'

        self.root = tk.Tk()
        self.root.geometry("319x365+605+218")
        self.root.title("data base parameter")
        self.root.configure(background="#d9d9d9")
        self.root.configure(highlightbackground="#d9d9d9")
        self.root.configure(highlightcolor="black")
        self.root.protocol('WM_DELETE_WINDOW',lambda e = '':self.cancel_clicked(e))

        self.data_base_frame = tk.LabelFrame(self.root)
        self.data_base_frame.place(relx=0.031, rely=0.027, relheight=0.945
                , relwidth=0.94)
        self.data_base_frame.configure(relief='groove')
        self.data_base_frame.configure(foreground="black")
        self.data_base_frame.configure(text='''data base parameter''')
        self.data_base_frame.configure(background="#d9d9d9")
        self.data_base_frame.configure(highlightbackground="#d9d9d9")
        self.data_base_frame.configure(highlightcolor="black")
        self.data_base_frame.configure(width=300)

        self.UID_frame = tk.LabelFrame(self.data_base_frame)
        self.UID_frame.place(relx=0.033, rely=0.058, relheight=0.13
                , relwidth=0.933, bordermode='ignore')
        self.UID_frame.configure(relief='groove')
        self.UID_frame.configure(foreground="black")
        self.UID_frame.configure(text='''UID''')
        self.UID_frame.configure(background="#d9d9d9")
        self.UID_frame.configure(highlightbackground="#d9d9d9")
        self.UID_frame.configure(highlightcolor="black")
        self.UID_frame.configure(width=280)

        self.uid_entry = tk.Entry(self.UID_frame)
        self.uid_entry.place(relx=0.036, rely=0.333, height=20, relwidth=0.943
                , bordermode='ignore')
        self.uid_entry.configure(background="white")
        self.uid_entry.configure(disabledforeground="#a3a3a3")
        self.uid_entry.configure(font="-family {Courier New} -size 10")
        self.uid_entry.configure(foreground="#000000")
        self.uid_entry.configure(highlightbackground="#d9d9d9")
        self.uid_entry.configure(highlightcolor="black")
        self.uid_entry.configure(insertbackground="black")
        self.uid_entry.configure(selectbackground="#c4c4c4")
        self.uid_entry.configure(selectforeground="black")

        self.PWD_frame = tk.LabelFrame(self.data_base_frame)
        self.PWD_frame.place(relx=0.033, rely=0.203, relheight=0.13
                , relwidth=0.933, bordermode='ignore')
        self.PWD_frame.configure(relief='groove')
        self.PWD_frame.configure(foreground="black")
        self.PWD_frame.configure(text='''passwod''')
        self.PWD_frame.configure(background="#d9d9d9")
        self.PWD_frame.configure(highlightbackground="#d9d9d9")
        self.PWD_frame.configure(highlightcolor="black")
        self.PWD_frame.configure(width=280)

        self.psw_entry = tk.Entry(self.PWD_frame)
        self.psw_entry.place(relx=0.036, rely=0.333, height=20, relwidth=0.943
                , bordermode='ignore')
        self.psw_entry.configure(background="white")
        self.psw_entry.configure(disabledforeground="#a3a3a3")
        self.psw_entry.configure(font="-family {Courier New} -size 10")
        self.psw_entry.configure(foreground="#000000")
        self.psw_entry.configure(highlightbackground="#d9d9d9")
        self.psw_entry.configure(highlightcolor="black")
        self.psw_entry.configure(insertbackground="black")
        self.psw_entry.configure(selectbackground="#c4c4c4")
        self.psw_entry.configure(selectforeground="black")
        self.psw_entry.configure(validate="key")
        self.psw_entry.configure(show='*')

        self.server__frame = tk.LabelFrame(self.data_base_frame)
        self.server__frame.place(relx=0.033, rely=0.348, relheight=0.13
                , relwidth=0.933, bordermode='ignore')
        self.server__frame.configure(relief='groove')
        self.server__frame.configure(foreground="black")
        self.server__frame.configure(text='''server''')
        self.server__frame.configure(background="#d9d9d9")
        self.server__frame.configure(highlightbackground="#d9d9d9")
        self.server__frame.configure(highlightcolor="black")
        self.server__frame.configure(width=280)

        self.server_entry = tk.Entry(self.server__frame)
        self.server_entry.place(relx=0.036, rely=0.333, height=20, relwidth=0.943
                , bordermode='ignore')
        self.server_entry.configure(background="white")
        self.server_entry.configure(disabledforeground="#a3a3a3")
        self.server_entry.configure(font="-family {Courier New} -size 10")
        self.server_entry.configure(foreground="#000000")
        self.server_entry.configure(highlightbackground="#d9d9d9")
        self.server_entry.configure(highlightcolor="black")
        self.server_entry.configure(insertbackground="black")
        self.server_entry.configure(selectbackground="#c4c4c4")
        self.server_entry.configure(selectforeground="black")

        self.database_frame = tk.LabelFrame(self.data_base_frame)
        self.database_frame.place(relx=0.033, rely=0.493, relheight=0.13
                , relwidth=0.933, bordermode='ignore')
        self.database_frame.configure(relief='groove')
        self.database_frame.configure(foreground="black")
        self.database_frame.configure(text='''database''')
        self.database_frame.configure(background="#d9d9d9")
        self.database_frame.configure(highlightbackground="#d9d9d9")
        self.database_frame.configure(highlightcolor="black")
        self.database_frame.configure(width=280)

        self.database_entry = tk.Entry(self.database_frame)
        self.database_entry.place(relx=0.036, rely=0.333, height=20
                , relwidth=0.943, bordermode='ignore')
        self.database_entry.configure(background="white")
        self.database_entry.configure(disabledforeground="#a3a3a3")
        self.database_entry.configure(font="-family {Courier New} -size 10")
        self.database_entry.configure(foreground="#000000")
        self.database_entry.configure(highlightbackground="#d9d9d9")
        self.database_entry.configure(highlightcolor="black")
        self.database_entry.configure(insertbackground="black")
        self.database_entry.configure(selectbackground="#c4c4c4")
        self.database_entry.configure(selectforeground="black")

        self.table_frame = tk.LabelFrame(self.data_base_frame)
        self.table_frame.place(relx=0.033, rely=0.638, relheight=0.13
                , relwidth=0.933, bordermode='ignore')
        self.table_frame.configure(relief='groove')
        self.table_frame.configure(foreground="black")
        self.table_frame.configure(text='''table''')
        self.table_frame.configure(background="#d9d9d9")
        self.table_frame.configure(highlightbackground="#d9d9d9")
        self.table_frame.configure(highlightcolor="black")
        self.table_frame.configure(width=280)

        self.table_entry = tk.Entry(self.table_frame)
        self.table_entry.place(relx=0.036, rely=0.333, height=20, relwidth=0.943
                , bordermode='ignore')
        self.table_entry.configure(background="white")
        self.table_entry.configure(disabledforeground="#a3a3a3")
        self.table_entry.configure(font="-family {Courier New} -size 10")
        self.table_entry.configure(foreground="#000000")
        self.table_entry.configure(highlightbackground="#d9d9d9")
        self.table_entry.configure(highlightcolor="black")
        self.table_entry.configure(insertbackground="black")
        self.table_entry.configure(selectbackground="#c4c4c4")
        self.table_entry.configure(selectforeground="black")

        self.set_btn = tk.Button(self.data_base_frame)
        self.set_btn.place(relx=0.6, rely=0.783, height=24, width=97
                , bordermode='ignore')
        self.set_btn.configure(activebackground="#ececec")
        self.set_btn.configure(activeforeground="#000000")
        self.set_btn.configure(background="#d9d9d9")
        self.set_btn.configure(disabledforeground="#a3a3a3")
        self.set_btn.configure(foreground="#000000")
        self.set_btn.configure(highlightbackground="#d9d9d9")
        self.set_btn.configure(highlightcolor="black")
        self.set_btn.configure(pady="0")
        self.set_btn.configure(text='''save''')
        self.set_btn.configure(width=97)
        self.set_btn.bind('<Button-1>',lambda e:self.set_clicked(e))


        self.connect_btn = tk.Button(self.data_base_frame)
        self.connect_btn.place(relx=0.6, rely=0.900, height=24, width=97
                , bordermode='ignore')
        self.connect_btn.configure(activebackground="#ececec")
        self.connect_btn.configure(activeforeground="#000000")
        self.connect_btn.configure(background="#d9d9d9")
        self.connect_btn.configure(disabledforeground="#a3a3a3")
        self.connect_btn.configure(foreground="#000000")
        self.connect_btn.configure(highlightbackground="#d9d9d9")
        self.connect_btn.configure(highlightcolor="black")
        self.connect_btn.configure(pady="0")
        self.connect_btn.configure(text='''set''')
        self.connect_btn.configure(width=97)
        self.connect_btn.bind('<Button-1>',lambda e:self.connect_clicked(e))


        self.cancel_btn = tk.Button(self.data_base_frame)
        self.cancel_btn.place(relx=0.1, rely=0.783, height=24, width=97
                , bordermode='ignore')
        self.cancel_btn.configure(activebackground="#ececec")
        self.cancel_btn.configure(activeforeground="#000000")
        self.cancel_btn.configure(background="#d9d9d9")
        self.cancel_btn.configure(disabledforeground="#a3a3a3")
        self.cancel_btn.configure(foreground="#000000")
        self.cancel_btn.configure(highlightbackground="#d9d9d9")
        self.cancel_btn.configure(highlightcolor="black")
        self.cancel_btn.configure(pady="0")
        self.cancel_btn.configure(text='''cancel''')
        self.cancel_btn.configure(width=97)
        self.cancel_btn.bind('<Button-1>',lambda e:self.cancel_clicked(e))


        self.write_btn = tk.Button(self.data_base_frame)
        self.write_btn.place(relx=0.1, rely=0.900, height=24, width=97
                , bordermode='ignore')
        self.write_btn.configure(activebackground="#ececec")
        self.write_btn.configure(activeforeground="#000000")
        self.write_btn.configure(background="#d9d9d9")
        self.write_btn.configure(disabledforeground="#a3a3a3")
        self.write_btn.configure(foreground="#000000")
        self.write_btn.configure(highlightbackground="#d9d9d9")
        self.write_btn.configure(highlightcolor="black")
        self.write_btn.configure(pady="0")
        self.write_btn.configure(text='''write''')
        self.write_btn.configure(width=97)
        self.write_btn.bind('<Button-1>',lambda e:self.main_win.write_clicked(e))
        self.database_initialize()
        self.root.mainloop()

class looper(threading.Thread):
    def __init__(self, main_win):
        threading.Thread.__init__(self)
        self.main_win = main_win
        self.daemon = True

    def makeHeader(self, type):
        return b'MSH|' + b'^~\&' + 7 * b'|' + type + b'|1|P|2.3.1||||||ASCII|||\r'
    def MSA(self):
        return b'MSA|AA|1|Message accepted|||0|\r'
    def ERR(self,code = b'0'):
        return b'ERR|' + code + b'|\r'
    def QAK(self,state = b'OK'):
        return b'QAK|SR|' + state + b'|\r'
    def QRD(self):
        return self.data.split(b'\r')[1] + b'\r'
    def QRF(self):
        return self.data.split(b'\r')[2] + b'\r'

    def accept(self,ack = b''):
        print(b'\x0b'+self.makeHeader(b'QCK^Q02') + self.MSA() + self.ERR() + self.QAK() + b'\x1c\r')
        self.cliant.send(b'\x0b'+self.makeHeader(b'ACK^R01') + self.MSA() + self.ERR() + self.QAK() + b'\x1c\r')
        self.main_win.show('\nhandler: accepted... ' + str(self.makeHeader(b'ACK') + b'\rMSA|AA|2|||||\r'))

    def oru(self):
        self.accept(b'^R01')
        segments = [segment.split(b'|') for segment in self.data.split(b'\r') if segment]
        print(segments[2][15])
        patient = {}
        if segments[1][8]:
            patient['blood'] = segments[1][8].decode()
        patient['ID'] = segments[2][2].decode()
        if segments[2][15]:
            patient['sampleType'] = segments[2][15].decode()
        if segments[3][3]:
            patient['testNo'] = segments[3][3].decode()
        if segments[3][4]:
            patient['testName'] = segments[3][4].decode()
        if segments[3][5]:
            patient['result'] = segments[3][5].decode()
        if segments[3][6]:
            patient['testUnit'] = segments[3][6].decode()
        print(patient)
        self.main_win.writer(patient)

    def grap_patient(self,barcode):
        return {'name': b'mohammed elmasri', 'blood': b'O', 'birthday': b'19961111000000', 'gender': b'M', 'barCode': barcode.encode(), 'sampleType': b'serum', 'tests':
                [b'1', b'2', b'3']}
        # patient info must be returned encoded.
    def reply(self, patient):
        if patient:
            massage = b'\x0b'+self.makeHeader(b'QCK^Q02') + self.MSA() + self.ERR() + self.QAK() + b'\x1c\r'
            print(massage)
            self.cliant.send(massage)
            massage = b'\x0b' + self.makeHeader(b'DSR^Q03') + self.MSA() + self.ERR()+ self.QAK() + self.QRD() + self.QRF()
            dictionary = {
                4:  patient['birthday'], 5: patient['gender'], 21: patient['barCode'], 26: patient['sampleType']
                , 6: patient['blood'], 24: b'N'
                }
            for i in range(1,29):
                if i in dictionary:
                    massage += b'DSP|' + str(i).encode() + b'||' + dictionary[i] + b'|||\r'
                else:
                    massage += b'DSP|' + str(i).encode() + b'|||||\r'
            for i in range(len(patient['tests'])):
                massage += b'DSP|' + str(i+29).encode() + b'||' + patient['tests'][i] + b'^^^|||\r'
            massage += b'DSC||\r\x1c\r'
            print(massage)
            self.cliant.send(massage)
        else:
            massage = b'\x0b' + self.makeHeader(b'DSR^Q02') + self.MSA() + self.ERR() + self.QAK(b'NF') + b'\x1c\r'
            self.cliant.send(massage)
    def qry(self):
        patient_barCode = self.data.split(b'\r')[1].split(b'|')[8]
        print(patient_barCode)
        if patient_barCode:
            patient = self.grap_patient(patient_barCode.decode())
            self.reply(patient)
        else:
            self.reply('')

    def handler(self):
        print('handler: starting... there is connection')
        try:
            while True:
                self.main_win.show('\nhandler: in waiting' + str(self.cliant))
                self.data = self.cliant.recv(8192)
                self.main_win.show('\nhandler: ' + str(self.data))
                if not self.data:
                    self.main_win.show('\nhandler: disconnected')
                    self.cliant.close()
                    return
                if b'ORU' in self.data:
                    print('oru')
                    self.oru()
                elif b'QRY' in self.data:
                    print('QRY')
                    self.qry()
        except ConnectionResetError:
            self.main_win.show('\nhandler: ERROR, disconnected')
        except ConnectionAbortedError:
            self.main_win.show('\nhandler: ERROR, disconnected')
        finally:
            self.cliant.close()
            self.main_win.show('\nhandler: exiting handler')

    def run(self):
        while True:
            self.main_win.show(
                '\n\nserver : accepting' + '\nserver: ' + str((self.main_win.ip, self.main_win.portnumber)))
            try:
                self.cliant, self.cliantAddress = self.main_win.connection.accept()
            except:
                self.main_win.show('\nforced to close before connection')
                return
            self.main_win.show('\nserver: client detected' + str(self.cliantAddress))
            self.handler()

class Toplevel1():
    device_name = 'BS240'
    psw = ''
    server = ''
    database = ''
    UID = ''
    table = ''
    frames = [''.encode('ascii')]
    results = {}
    last_result = {}
    file_path = None
    port_description = None
    port = serial.Serial()
    state_of_connection = False
    unwritten_results = []
    daemon = True

    '''DO NOT ADJUST FOR ALL; responsible for creating result dictionary by reading result file'''
    def resultReader(self,file_name):
        file = open(self.file_path + '\\' + self.device_name + '\\' + file_name + '.txt', 'r')
        lines = file.read()
        lines = lines.split('\n')
        string_to_write = {}
        for line in lines:
            if line:
                x = line.split(':')
                string_to_write[x[0]] = x[1]
        del lines
        return string_to_write

    '''DO NOT ADJUST FOR ALL; this is responsiple for openning db setting window.'''
    def db_clicked(self,p1):
        if self.db_button.state()[0] == 'active':
            self.db_button.configure(state='disable')
            self.dw = Database_setting()
            self.dw.set(self)
            self.dw.start()

    '''DO NOT ADJUST FOR ALL; these are responsible for creating directories (folders).'''
    def directory_creater_and_changer(self, ldir, wdir):
        print(os.getcwd())
        os.chdir(self.file_path + wdir)
        try:
            if not os.path.exists(ldir):
                os.mkdir(ldir)
        except:
            self.show('\n' + 'error occurred while trying to create folder')
            return
    def path_changer(self, dir):
        if dir == 'main':
            self.set()
            self.directory_creater_and_changer(self.device_name, '')
        if dir == 'run':
            self.set()
            self.directory_creater_and_changer('run', '/' + self.device_name)

    '''DO NOT ADJUST FOR TCP DEVICES;
     this function is responsible for getting file_path and port description from entries.'''
    def set(self):
        self.file_path = self.file_path_entry.get()
        self.ip = self.ip_entry.get()
        self.portnumber = int(self.port_entry.get())

    '''DO NOT ADJUST FOR TCP; this is respnsible for openning serial ports.'''
    def get_connection(self):
        self.set()
        s = socket.socket()
        try:
            print((self.ip, self.portnumber))
            s.bind((self.ip, self.portnumber))
            self.show('\n' + 'connection has been created')
            s.listen(1)
            self.state_of_connection = True
            return s
        except:
            s.close()
            self.show('\nthere is problem while creating connection')
        return None

    '''DO NOT ADJUST FOR TCP; responsible for starting connection with device.'''
    def run(self):
        self.connect_button.configure(state='disabled')
        self.db_button.configure(state='disabled')
        self.show('\n' + 'connecting')
        self.connection = self.get_connection()
        if self.state_of_connection and self.connection:
            self.disconnect_button.configure(state='enable')
            self.looper = looper(self)
            self.looper.start()
        else:
            self.show('\n' + 'there is no connection\n')
            self.connect_button.configure(state='enable')

    """DO NOT ADJUST FOR TCP; this method is responsible for cutting the loop and ending  connection"""
    def disconnect(self):
        if self.connection:
            self.state_of_connection = False
            try:
                self.looper.cliant.close()
                del self.looper
            except AttributeError:
                pass
            self.connection.close()
            self.show('\ndisconnected')
            self.connect_button.configure(state='enable')
            self.disconnect_button.configure(state='disable')

    '''___________________THIS PORTION OF THE CODE IS ADJUSTABLE__________________'''

    '''
        DO NOT ADJUST; responsible for reading unwritten results from a file the only use is in
        read_unwritten_results()
    '''
    def read_unwritten_results(self):
        try:
            new_file = open(self.file_path + '\\' + self.device_name + '\\' + '\\run\\unwritten_results', 'r')
            self.unwritten_results = new_file.readlines()
            self.unwritten_results = [i[:-1] for i in self.unwritten_results]
            new_file.close()
        except FileNotFoundError:
            self.show('\nERROR there is no initialization')

    '''DO NOT ADJUST; responsible for writing data on data base'''
    def write_clicked(self,p1):
        self.read_unwritten_results()
        self.db_writer.read_parameters()
        self.db_writer.run()
        lines = '\n'.join(self.unwritten_results)
        new_file = open(self.file_path + '\\'+self.device_name+'\\' + '\\run\\unwritten_results','w+' )
        new_file.write(lines)
        new_file.close()

    '''
        DO NOT ADJUST; responsible for writing result in text file
        named depending on the result ID, then the ID is logged into unwritten results
        at last the function calls write_clicked which responsible for writing on database
    '''
    def writer(self,result):
        self.last_result = result
        file_name = self.last_result['ID']
        new_file = open(self.file_path + '\\'+self.device_name+'\\' + str(file_name) + '.txt', 'w+')
        for i in self.last_result:
            new_file.write(i + ':' + self.last_result[i] + '\n')
        new_file.close()
        new_file = open(self.file_path + '\\'+self.device_name+'\\' + '\\run\\unwritten_results','a+' )
        new_file.write(self.last_result['ID'] + '\n\n')
        new_file.close()
        del new_file
        self.write_clicked('')

    '''starts connection when connect_button is clicked'''
    def start1(self,p1):
        if self.connect_button.state()[0] == 'active' :
            self.path_changer('main')
            self.path_changer('run')
            self.show('\nstarting')
            self.run()

    '''disconnecting and stop the loop when clicking the disconnect_button'''
    def exit1(self,p1):
        if self.disconnect_button.state()[0] == 'active' :
            self.disconnect()

    '''this function is responsible for ending the entire program'''
    def exit2(self,p1):
        if self.exit_btn.state()[0] == 'active' :
            self.disconnect()
            self.root.destroy()
            sys.exit()

    '''______________________________________________________________________'''
    '''show used to print strings on the connection state scrolled text box'''
    def show(self,string):
        self.connection_state_text.configure(state = 'normal')
        self.connection_state_text.insert(tk.END,string)
        self.connection_state_text.configure(state = 'disabled')

    '''initiate port entry is used to insert the comports to the port dropbox'''
    def initiate_port_entry(self):
        x = list(serial.tools.list_ports.comports())
        list_values = []
        for i in x:
            list_values.append(i.description)
        self.port_entry.configure(values = list_values)

    '''initialize the main window'''
    def __init__(self):
        self.root = tk.Tk()
        '''This class configures and populates the toplevel window.
           top is the toplevel containing window.'''
        _bgcolor = '#d9d9d9'  # X11 color: 'gray85'
        _fgcolor = '#000000'  # X11 color: 'black'
        _compcolor = '#d9d9d9'  # X11 color: 'gray85'
        _ana1color = '#d9d9d9'  # X11 color: 'gray85'
        _ana2color = '#ececec'  # Closest X11 color: 'gray92'
        self.style = ttk.Style()
        if sys.platform == "win32":
            self.style.theme_use('winnative')
        self.style.configure('.', background=_bgcolor)
        self.style.configure('.', foreground=_fgcolor)
        self.style.configure('.', font="TkDefaultFont")
        self.style.map('.', background=
        [('selected', _compcolor), ('active', _ana2color)])

        self.root.geometry("595x600+422+80")
        self.root.title(self.device_name)
        self.root.configure(background="#d9d9d9")
        self.root.configure(highlightbackground="#d9d9d9")
        self.root.configure(highlightcolor="black")

        self.connection_parameter_frame = ttk.Labelframe(self.root)
        self.connection_parameter_frame.place(relx=0.017, rely=0.02
                                              , relheight=0.274, relwidth=0.941)
        self.connection_parameter_frame.configure(relief='')
        self.connection_parameter_frame.configure(text='''connection_parameter''')
        self.connection_parameter_frame.configure(width=560)

        self.file_path_frame = ttk.Labelframe(self.connection_parameter_frame)
        self.file_path_frame.place(relx=0.018, rely=0.148, relheight=0.333
                                   , relwidth=0.714, bordermode='ignore')
        self.file_path_frame.configure(relief='')
        self.file_path_frame.configure(text='''file_path''')
        self.file_path_frame.configure(width=400)

        self.file_path_entry = ttk.Entry(self.file_path_frame)
        self.file_path_entry.place(relx=0.025, rely=0.444, relheight=0.467
                                   , relwidth=0.94, bordermode='ignore')
        self.file_path_entry.configure(takefocus="")

        self.port_description_frame = ttk.Labelframe(self.connection_parameter_frame)
        self.port_description_frame.place(relx=0.018, rely=0.519, relheight=0.333
                                          , relwidth=0.714, bordermode='ignore')
        self.port_description_frame.configure(relief='')
        self.port_description_frame.configure(text='''port_description''')
        self.port_description_frame.configure(width=400)

        self.port_entry = ttk.Entry(self.port_description_frame)
        self.port_entry.place(relx=0.025, rely=0.444, relheight=0.467, relwidth=0.33, bordermode='ignore')
        self.port_entry.configure(takefocus="")

        self.ip_entry = ttk.Entry(self.port_description_frame)
        self.ip_entry.place(relx=0.37, rely=0.444, relheight=0.467, relwidth=0.596, bordermode='ignore')
        self.ip_entry.configure(takefocus="")

        self.connect_button = ttk.Button(self.connection_parameter_frame)
        self.connect_button.place(relx=0.804, rely=0.34, height=25, width=76
                                  , bordermode='ignore')
        self.connect_button.configure(text='''connect''')
        self.connect_button.configure(command=lambda e='': self.start1(e))

        self.db_button = ttk.Button(self.connection_parameter_frame)
        self.db_button.place(relx=0.804, rely=0.14, height=25, width=76
                             , bordermode='ignore')
        self.db_button.configure(text='''database''')
        self.db_button.configure(command=lambda e='': self.db_clicked(e))

        self.disconnect_button = ttk.Button(self.connection_parameter_frame)
        self.disconnect_button.place(relx=0.804, rely=0.54, height=25, width=76
                                     , bordermode='ignore')
        self.disconnect_button.configure(takefocus="")
        self.disconnect_button.configure(text='''disconnect''')
        self.disconnect_button.configure(state='disable')
        self.disconnect_button.configure(command=lambda e='': self.exit1(e))

        self.exit_btn = ttk.Button(self.connection_parameter_frame)
        self.exit_btn.place(relx=0.804, rely=0.74, height=25, width=76
                            , bordermode='ignore')
        self.exit_btn.configure(takefocus="")
        self.exit_btn.configure(text='''exit''')
        self.exit_btn.configure(command=lambda e='': self.exit2(e))

        self.connection_state = ttk.Labelframe(self.root)
        self.connection_state.place(relx=0.017, rely=0.304, relheight=0.68
                                    , relwidth=0.941)
        self.connection_state.configure(relief='')
        self.connection_state.configure(text='''connection_state''')
        self.connection_state.configure(width=560)

        self.connection_state_text = ScrolledText(self.connection_state)
        self.connection_state_text.place(relx=0.018, rely=0.06, relheight=0.928
                                         , relwidth=0.966, bordermode='ignore')
        self.connection_state_text.configure(background="white")
        self.connection_state_text.configure(state='disabled')
        self.connection_state_text.configure(font="TkTextFont")
        self.connection_state_text.configure(foreground="black")
        self.connection_state_text.configure(highlightbackground="#d9d9d9")
        self.connection_state_text.configure(highlightcolor="black")
        self.connection_state_text.configure(insertbackground="black")
        self.connection_state_text.configure(insertborderwidth="3")
        self.connection_state_text.configure(selectbackground="#c4c4c4")
        self.connection_state_text.configure(selectforeground="black")
        self.connection_state_text.configure(width=254)
        self.connection_state_text.configure(wrap="none")

        '''the following two statements used to initiate the port entry and file path entry'''
        self.file_path_entry.insert(0, '/home/pi/Desktop')
        self.ip_entry.insert(0, socket.gethostbyname(socket.gethostname()))
        self.port_entry.insert(0, '5152')
        self.path_changer('main')
        self.path_changer('run')
        self.db_writer = Db_Update(self)
        self.db_writer.read_parameters()


# The following code is added to facilitate the Scrolled widgets you specified.
class AutoScroll(object):
    '''Configure the scrollbars for a widget.'''

    def __init__(self, master):
        #  Rozen. Added the try-except clauses so that this class
        #  could be used for scrolled entry widget for which vertical
        #  scrolling is not supported. 5/7/14.
        try:
            vsb = ttk.Scrollbar(master, orient='vertical', command=self.yview)
        except:
            pass
        hsb = ttk.Scrollbar(master, orient='horizontal', command=self.xview)

        #self.configure(yscrollcommand=_autoscroll(vsb),
        #    xscrollcommand=_autoscroll(hsb))
        try:
            self.configure(yscrollcommand=self._autoscroll(vsb))
        except:
            pass
        self.configure(xscrollcommand=self._autoscroll(hsb))

        self.grid(column=0, row=0, sticky='nsew')
        try:
            vsb.grid(column=1, row=0, sticky='ns')
        except:
            pass
        hsb.grid(column=0, row=1, sticky='ew')

        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        # Copy geometry methods of master  (taken from ScrolledText.py)
        if py3:
            methods = tk.Pack.__dict__.keys() | tk.Grid.__dict__.keys() \
                  | tk.Place.__dict__.keys()
        else:
            methods = tk.Pack.__dict__.keys() + tk.Grid.__dict__.keys() \
                  + tk.Place.__dict__.keys()

        for meth in methods:
            if meth[0] != '_' and meth not in ('config', 'configure'):
                setattr(self, meth, getattr(master, meth))

    @staticmethod
    def _autoscroll(sbar):
        '''Hide and show scrollbar as needed.'''
        def wrapped(first, last):
            first, last = float(first), float(last)
            if first <= 0 and last >= 1:
                sbar.grid_remove()
            else:
                sbar.grid()
            sbar.set(first, last)
        return wrapped

    def __str__(self):
        return str(self.master)


def _create_container(func):
    '''Creates a ttk Frame with a given master, and use this new frame to
    place the scrollbars and the widget.'''
    def wrapped(cls, master, **kw):
        container = ttk.Frame(master)
        container.bind('<Enter>', lambda e: _bound_to_mousewheel(e, container))
        container.bind('<Leave>', lambda e: _unbound_to_mousewheel(e, container))
        return func(cls, container, **kw)
    return wrapped


class ScrolledText(AutoScroll, tk.Text):
    '''A standard Tkinter Text widget with scrollbars that will
    automatically show/hide as needed.'''
    @_create_container
    def __init__(self, master, **kw):
        tk.Text.__init__(self, master, **kw)
        AutoScroll.__init__(self, master)


def _bound_to_mousewheel(event, widget):
    child = widget.winfo_children()[0]
    if platform.system() == 'Windows' or platform.system() == 'Darwin':
        child.bind_all('<MouseWheel>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Shift-MouseWheel>', lambda e: _on_shiftmouse(e, child))
    else:
        child.bind_all('<Button-4>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Button-5>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Shift-Button-4>', lambda e: _on_shiftmouse(e, child))
        child.bind_all('<Shift-Button-5>', lambda e: _on_shiftmouse(e, child))


def _unbound_to_mousewheel(event, widget):
    if platform.system() == 'Windows' or platform.system() == 'Darwin':
        widget.unbind_all('<MouseWheel>')
        widget.unbind_all('<Shift-MouseWheel>')
    else:
        widget.unbind_all('<Button-4>')
        widget.unbind_all('<Button-5>')
        widget.unbind_all('<Shift-Button-4>')
        widget.unbind_all('<Shift-Button-5>')


def _on_mousewheel(event, widget):
    if platform.system() == 'Windows':
        widget.yview_scroll(-1*int(event.delta/120),'units')
    elif platform.system() == 'Darwin':
        widget.yview_scroll(-1*int(event.delta),'units')
    else:
        if event.num == 4:
            widget.yview_scroll(-1, 'units')
        elif event.num == 5:
            widget.yview_scroll(1, 'units')


def _on_shiftmouse(event, widget):
    if platform.system() == 'Windows':
        widget.xview_scroll(-1*int(event.delta/120), 'units')
    elif platform.system() == 'Darwin':
        widget.xview_scroll(-1*int(event.delta), 'units')
    else:
        if event.num == 4:
            widget.xview_scroll(-1, 'units')
        elif event.num == 5:
            widget.xview_scroll(1, 'units')


aia = Toplevel1()
aia.root.mainloop()