import tkinter as tk
import tkinter.ttk as ttk
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
            db = open(self.main_win.file_path + '/'+self.main_win.instrumentName+'/run/' + 'db_parameters', 'rb')
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
        db = open(self.main_win.file_path + '/'+self.main_win.instrumentName+'/run/' + 'db_parameters', 'wb+')
        db.write(b'')
        db.close()
        db = open(self.main_win.file_path + '/'+self.main_win.instrumentName+'/run/' + 'db_parameters', 'ab+')
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
            db = open(self.main_win.file_path + '/'+self.main_win.instrumentName+'/run/' + 'db_parameters', 'rb')
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
        self.write_btn.bind('<Button-1>',lambda e:self.main_win.attemptUpload(e))
        self.database_initialize()
        self.root.mainloop()


class Toplevel1():
    instrumentName = 'sysmax'
    psw = ''
    server = ''
    database = ''
    UID = ''
    table = ''
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
        file = open(self.file_path + '/' + self.instrumentName + '/' + file_name + '.txt', 'r')
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

    # region directory linux

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
            self.directory_creater_and_changer(self.instrumentName, '')
        if dir == 'run':
            self.set()
            self.directory_creater_and_changer('run', '/' + self.instrumentName)

    # endregion directory linux

    '''DO NOT ADJUST FOR SERIAL DEVICES;
     this function is responsible for getting file_path and port description from entries.'''
    def set(self):
        self.file_path = self.file_path_entry.get()
        self.port_description = self.port_entry.get()

    '''DO NOT ADJUST FOR SERIALS; this is respnsible for openning serial ports.'''
    def getPort(self, description):
        self.set()
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if description in p.description:
                try:
                    s = serial.Serial(p.device, 9600, serial.SEVENBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)
                except:
                    self.show( '\n' + 'error while trying to open the port')
                    self.state_of_connection = False
                    return None
                if not s.is_open:
                    s.open()
                self.state_of_connection = True
                return s

        self.state_of_connection = False
        self.getting_port = False
        self.show( '\n' + 'the port has not been found')
        return None

    '''DO NOT ADJUST FOR SERIALS; responsiple for starting connection with device.'''
    def run(self):
        print('running')
        self.connect_button.configure(state= 'disabled')
        self.db_button.configure(state= 'disabled')
        self.port = self.getPort(self.port_description)
        if self.state_of_connection and self.port:
            self.show('\n' + 'connecting...')
            self.disconnect_button.configure(state='enable')
            self.timerThread = repeatedTimer.RepeatedTimer(0.2,self.looper)
        else:
            self.show( '\n' + 'ERROR, there is no connection\n')
            self.connect_button.configure(state='enable')

    """DO NOT ADJUST FOR SERIALS; this method is responsible for cutting the loop and ending  connection"""
    def disconnect(self):
        try:
            if self.port.is_open:
                self.state_of_connection = False
                self.timerThread.stop()
                self.port.close()
                self.show( '\ndisconnected')
                self.connect_button.configure(state='enable')
                self.disconnect_button.configure(state='disable')
        except:
            self.show('\nERROR, there is no port to be closed')

    '''___________________THIS PORTION OF THE CODE IS ADJUSTABLE__________________'''


    '''
        DO NOT ADJUST; responsible for reading unwritten results from a file the only use is in 
        read_unwritten_results()
    '''
    def read_unwritten_results(self):
        try:
            new_file = open(self.file_path + '/' + self.instrumentName + '/' + '/run/unwritten_results', 'r')
            self.unwritten_results = new_file.readlines()
            self.unwritten_results = [i[:-1] for i in self.unwritten_results]
            new_file.close()
        except FileNotFoundError:
            self.show('\nERROR there is no initialization')

    '''DO NOT ADJUST; responsible for writing data on data base'''
    def attemptUpload(self,p1):
        self.read_unwritten_results()
        print(self.unwritten_results)
        self.db_writer.read_parameters()
        self.db_writer.run()
        lines = '\n'.join(self.unwritten_results)
        new_file = open(self.file_path + '/'+self.instrumentName+'/' + '/run/unwritten_results','w+' )
        new_file.write(lines)
        new_file.close()

    '''
        DO NOT ADJUST; responsible for writing result in text file 
        named depending on the result ID, then the ID is logged into unwritten results
        at last the function calls attemptUpload which responsible for writing on database
    '''
    def writer(self,result):
        self.last_result = result
        self.last_result['ID'] = '127'
        file_name = self.last_result['ID']
        new_file = open(self.file_path + '/'+self.instrumentName+'/' + str(file_name) + '.txt', 'w+')
        for i in self.last_result:
            new_file.write(i + ':' + self.last_result[i] + '\n')
        new_file.close()
        new_file = open(self.file_path + '/'+self.instrumentName+'/' + 'run/unwritten_results','a+' )
        print("writer: result", result)
        new_file.write(self.last_result['ID'] + '\n\n')
        new_file.close()
        del new_file
        self.attemptUpload('')

    def cbc_text(self,text):
        return {'textIdentifier': text[1:3], 'Date': text[4:8] + '/' + text[8:10] + '/' + text[10:12],
                'ID': text[13:28], 'WBC': text[35:38] + '.' + text[38], 'Flag1': text[39],
                'RBC': text[40:42] + '.' + text[42:44], 'Flag2': text[44], 'HGB': text[45:48] + '.' + text[48],
                'Flag3': text[49], 'HCT': text[50:53] + '.' + text[53], 'Flag4': text[54],
                'MCV': text[55:58] + '.' + text[58], 'Flag5': text[59], 'MCH': text[60:63] + '.' + text[63],
                'Flag6': text[64], 'MCHC': text[65:68] + '.' + text[68], 'Flag7': text[69], 'PLT': text[70:74],
                'Flag8': text[74], 'Lym%': text[75:78] + '.' + text[78], 'Flag9': text[79],
                'MXD%': text[80:83] + '.' + text[83], 'Flag10': text[84], 'NEUT%': text[85:88] + '.' + text[88],
                'Flag11': text[89], 'Lym#': text[90:93] + '.' + text[93], 'Flag12': text[94],
                'MXD#': text[95:98] + '.' + text[98], 'Flag13': text[99], 'NEUT#': text[100:103] + '.' + text[103],
                'Flag14': text[104], 'RDW-SD': text[105:108] + '.' + text[108], 'Flag15': text[109],
                'RDW-CV': text[110:113] + '.' + text[113], 'Flag16': text[114], 'PDW': text[115:118] + '.' + text[118],
                'Flag17': text[119], 'MPV': text[120:123] + '.' + text[123], 'Flag18': text[124],
                'P-LCR': text[125:128] + '.' + text[128], 'Flag19': text[129]}

    ''' starting loop that reads from serial port'''
    def looper(self):
        try:
            try:
                if not self.frameString:
                    self.frameString = ''
            except:
                pass
            while self.port.in_waiting > 0:
                d = self.port.read(1)
                if d.decode('ascii') and d != b'\x03':
                    self.frameString += d.decode('ascii')
                if d == b'\x03':
                    self.port.write(b'\x06')
                    self.last_result = self.cbc_text(self.frameString)
                    self.frameString = ''
                    self.writer(self.last_result)
        except:
            self.show('\nERROR while looping')
            self.disconnect()

    '''DO NOT ADJUST AT ALL; starts connection when connect_button is clicked'''
    def connect(self,p1):
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

    # region init linux

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
        self.root.title(self.instrumentName)
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
        self.file_path_entry.insert(0, '/home/pi/Desktop')

        self.port_description_frame = ttk.Labelframe(self.connection_parameter_frame)
        self.port_description_frame.place(relx=0.018, rely=0.519, relheight=0.333
                                          , relwidth=0.714, bordermode='ignore')
        self.port_description_frame.configure(relief='')
        self.port_description_frame.configure(text='''port_description''')
        self.port_description_frame.configure(width=400)

        self.portlist = tk.StringVar()
        self.port_entry = ttk.Combobox(self.port_description_frame)
        self.port_entry.place(relx=0.025, rely=0.444, relheight=0.467, relwidth=0.94, bordermode='ignore')
        self.port_entry.configure(takefocus="")
        self.port_entry.configure(textvariable=self.portlist)
        # self.port_entry.configure(cursor="ibeam")
        self.initiate_port_entry()

        self.connect_button = ttk.Button(self.connection_parameter_frame)
        self.connect_button.place(relx=0.804, rely=0.34, height=25, width=76
                                  , bordermode='ignore')
        self.connect_button.configure(text='''connect''')
        self.connect_button.bind('<Button-1>', lambda e: self.connect(e))

        self.db_button = ttk.Button(self.connection_parameter_frame)
        self.db_button.place(relx=0.804, rely=0.14, height=25, width=76
                             , bordermode='ignore')
        self.db_button.configure(text='''database''')
        self.db_button.bind('<Button-1>', lambda e: self.db_clicked(e))

        self.disconnect_button = ttk.Button(self.connection_parameter_frame)
        self.disconnect_button.place(relx=0.804, rely=0.54, height=25, width=76
                                     , bordermode='ignore')
        self.disconnect_button.configure(takefocus="")
        self.disconnect_button.configure(text='''disconnect''')
        self.disconnect_button.configure(state='disable')
        self.disconnect_button.bind('<Button-1>', lambda e: self.exit1(e))

        self.exit_btn = ttk.Button(self.connection_parameter_frame)
        self.exit_btn.place(relx=0.804, rely=0.74, height=25, width=76
                            , bordermode='ignore')
        self.exit_btn.configure(takefocus="")
        self.exit_btn.configure(text='''exit''')
        self.exit_btn.bind('<Button-1>', lambda e: self.exit2(e))

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
        # self.file_path_entry.insert(0, os.path.expanduser())
        self.port_entry.insert(0, 'USB-SERIAL CH340')
        self.set()
        self.path_changer('main')
        self.path_changer('run')
        self.db_writer = Db_Update(self)

        # endregion


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


instance = Toplevel1()
instance.root.mainloop()