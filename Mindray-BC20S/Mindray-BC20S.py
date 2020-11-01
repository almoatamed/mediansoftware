import tkinter as tk
import tkinter.ttk as ttk
import os
import sys
import requests
import time
import threading
from threading import Timer
import platform
import socket
import sqlite3
py3 = True


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class looper(threading.Thread):
    running = True

    # initialization which inherets the threading functionality and the toploevel one instance
    def __init__(self, main_win):
        threading.Thread.__init__(self)
        self.main_win = main_win
        self.daemon = True

    #  tries to accept a client on the connection socket and if succeed then call handler
    def run(self):
        while True:
            if not self.running:
                return
            print('sleeping')
            time.sleep(5)
            self.main_win.show(
                '\n\nserver : connecting' + '\nserver: ' + str((self.main_win.ip, 5100)))
            try:
                s = socket.socket()
                s.connect((self.main_win.ip,5100))
            except TimeoutError:
                self.main_win.show(
                    'server-run: Timeout while trying to connect to Instrument ' + self.main_win.device_name + ''
                    ' ,check ip'
                )
                self.main_win.disconnect()
                return
            except:
                self.main_win.show('server: Error occured please try again!')
                self.main_win.disconnect()
                return
            self.handler(s)

    def handler(self,s):
        print('handler')
        data= b''
        while True:
            if not self.running:
                return
            time.sleep(2)
            bytes = s.recv(999999)
            bytes = bytes.replace(b'\x02',b'')
            if bytes == '\n':
                s.close()
                del s
                return
            if len(bytes)<50:
                print(bytes)
            else:
                print(bytes[0:40])
            if bytes:
                data+=bytes
                if len(data)>4:
                    if data[-3:] == b'\r\x1c\r':
                        print('true signal')
                        records = []
                        try:
                            for message in data.split(b'\x0b'):
                                if not message:
                                    continue
                                records.append([])
                                for line in message.split(b'\r'):
                                    records[-1].append([])
                                    for segment in line.split(b'|'):
                                        print(segment)
                                        records[-1][-1].append(segment)
                            print(' is true and loop finished successfully')
                            for message in records:
                                if message[0][8] == b'ORU^R01':
                                    print('oru message')
                                    r = {}
                                    r['result'] = {}
                                    for line in message:
                                        if line[0] == b'OBR':
                                            r['id'] = line[3].decode()
                                        elif line[0] == b'OBX':
                                            r['result'][line[3].split(b'^')[1].decode()] = line[5].decode()
                                    if r['result'] and 'id' in r:
                                        self.main_win.writer(r)
                        except:
                            pass
                        data = b''
                print('test signal')
                continue


class Toplevel1():
    device_name = 'Mindray-BC20S'
    localcode2globalcode = {}

    # creats a variable that holdt the inverse of the localcode2globalcode
    # called in init
    def globalCode2localCode(self):
        self.globalcode2localcode = {}
        for i in self.localcode2globalcode:
            self.globalcode2localcode[self.localcode2globalcode[i]] = i

    # connection parameters
    ip = 0
    port = '5122'

    # api parameters
    sampleid = b'sample_code'
    apigetter = 'http://165.22.27.138/lims/v1/sample/tests'
    apisetter = 'http://165.22.27.138/lims/v1/results/devices/submit'

    daemon = True

    # gets the right ip
    def getIP(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        s.connect(('8.8.8.8', 80))

        self.ip = s.getsockname()[0]

        s.close()

    # gets the connection ip and port for the local network instrument
    def set(self):
        self.ip = self.ip_entry.get()
        self.portnumber = int(self.port_entry.get())

    # disables connect button
    # shows connecting message
    # gets the connection instanse of of get_connection function
    # if connection is valid then create a looper instance and start the loop
    def run(self):
        self.connect_button.configure(state='disabled')
        self.show('connecting')
        self.disconnect_button.configure(state='enable')
        print('starting')
        self.set()
        self.looper = looper(self)
        print('looper is abbout to run')
        self.looper.start()

    # closes the looper instance and the connection sucket
    # enable the connect button and disable disconnect button
    def disconnect(self):
            try:
                self.looper.running = False
                del self.looper
            except AttributeError:
                pass
            self.show('disconnected\n')
            self.connect_button.configure(state='enable')
            self.disconnect_button.configure(state='disable')

    # contact the LIMS api through a given url and gets the sample data
    # using barcode
    def getSampleParameters(self, sampleBarCode):
        sampleBarCode = str(sampleBarCode)
        print(self.sampleid + b'=' + sampleBarCode.encode())
        try:
            resp = requests.get(self.apigetter, params=self.sampleid + b'=' + sampleBarCode.encode(),timeout=2)
            if resp.status_code == 200:
                respjson = resp.json()
                print(respjson)
                if 'error' in respjson:
                    return False
                required_tests = []
                for i in respjson[0]['parameters']:
                    required_tests.append(i['code'])
                print(required_tests)
                return required_tests
            else:
                print('getSampleParameters: invalid resp')
                return 'nc'
        except:
            print('getsampleParameters: error in requests')
            return 'nc'

    # uploads tests for the same api through different url
    def upload(self, sample):
        print('uploader')
        record = {'id': sample[1], 'instrument_code': self.device_name}
        print(record)
        parameters = []
        for test in sample[2]:
            parameters.append(
                {
                    'parameter': list(test.keys())[0],
                    'results': list(test.values())[0],
                    'status': 'null',
                    'flag': 'null'
                }
            )
        record['parameters'] = parameters
        print(record)
        try:
            resp = requests.post(self.apisetter, json=record)
            if resp.status_code == 200:
                self.testsetuploader(sample[0])
                print(resp.json())
                return 'done'
            else:
                print(resp.status_code)
                print(resp.content.decode())
                return 'connection error'
        except:
                return 'upload: connection error'


    # craete a connection
    def dbc(self,d=''):
        # print(d)
        os.chdir(self.path + self.device_name)
        # print('dbc',os.getcwd())
        if d:
            with sqlite3.connect('median.db') as cnxn:
                # print('first with')
                c = cnxn.cursor()
                x = list(c.execute(d))
                c.close()
            return x
    # inserts into samples tabel the barcode as new sample
    # it uses the sampleget function to check if the sample barcode
    # already exists.
    def sampleset(self, barcode):
        if self.sampleget(barcode):
            return False
        else:
            # print('inserting barcode')
            self.dbc('insert into sample(barcode) values(' + str(barcode) + ')')
            return True
    # returns the first sample from the database with given barcode
    # note that the barcode is unique value so it
    # should either return one or non.
    def sampleget(self, barcode):
        x = self.dbc('select * from sample where barcode = ' + str(barcode) + ';')
        # print(x)
        return x
        # return [i for i in c.execute('select * from sample ;')][0]
    # update counter where counter is used as the test id
    def cset(self):
        self.dbc('update counter set count = '+str(self.cget()+1)+' where id = 1 ')
        return True
    # gets counter
    def cget(self):
        x = self.dbc('select count from counter where id = 1 ')[0][0]
        return x
    # inserts test that currespond to a given barcode to the database
    def testset(self, result):
        #
        #     CREATE TABLE test(
        #     test_id unsigned int primary key not null,
        #     barcodeid unsigned int not null,
        #     testcode varchar(100) not null,
        #     result varchar(15) not null,
        #     abnormality varchar(10),
        #     status varchar(1),
        #     range varchar(20),
        #     uploadstate varchar(1) default 'n',
        #     created_at datetime not null default current_timestamp,
        #     FOREIGN KEY(barcodeid) REFERENCES user(barcode)
        #     );
        #
        # if self.sampleget(result['id']):
        self.dbc('insert into test(test_id,barcodeid,results) values('
                  ''+str(self.cget())+',"' + result['id'] + '","' + str(result['result']) + '");')
        self.cset()
        # else:
        #     raise sqlite3.OperationalError
        return True
    # gets the test result for a sample
    def testget(self,barcode):
        return self.dbc('select * from test where barcodeid="'+str(barcode)+'"')


    # upload the state of given test to uploaded
    def testsetuploader(self,test):
        # print('setting uploaded')
        if self.dbc('update test set uploadstate = "y" where test_id = ' + str(test)):
            return True
        else:
            return False

    # upload the state of given test to uploaded
    def testseterror(self,test):
        # print('setting uploaded')
        if self.dbc('update test set uploadstate = "e" where test_id = ' + str(test)):
            return True
        else:
            return False

    # upload the last test result and
    # try to upload unuploaded tests
    def writer(self,result):
        self.last_result = result
        # print(self.last_result)
        # self.sampleset(self.last_result['id'])
        self.testset(self.last_result)
        self.write_clicked()

    # write clicked create connection
    # and gets test results where the upload state is "n"
    # which means not uploaded
    def write_clicked(self):
        samples = self.dbc('select * from test where uploadstate = "n" order by created_at desc')
        # for i in samples:
            # print(i)
            # print('\n')
        if len(samples)==0:
            return
        for sample in samples:
            parms = self.getSampleParameters(sample[1])

            # this condition check is the test code it within the parms brought from the api LIMS
            # for the given barcode
            # note that test[1] is the barcode it self
            if parms:
                # print(sample[2])
                string = sample[2][1:-1].split(',')
                # print(string)
                testlist = []
                for test in string:
                    test = test.split(':')
                    # print(test)
                    testlist.append({test[0].strip()[1:-1]: test[1].strip()[1:-1]})
                # print(testlist)
                samplelist = []
                samplelist.append(sample[0])
                samplelist.append(sample[1])
                samplelist.append(testlist)
                # print(samplelist)
                self.upload(samplelist)
            else:
                self.testseterror(sample[0])

    # turns off the connect button and start the run function
    # this function only works if the connection button is active
    def start1(self,p1):
        # print('starting one')
        if self.connect_button.state()[0] == 'active' :
            self.show('starting')
            self.run()

    # exit1 is basically a disconnect button
    # it check if the disconnect button is active or not
    # and if it is it runs the disconnect button
    def exit1(self,p1):
        if self.disconnect_button.state()[0] == 'active' :
            self.disconnect()

    # exit2 is basically a program close button it check is the exit button is working and then
    # it calls the disconnect and the root.destroy functions
    # and finally close the program with sys.close
    def exit2(self,p1):
        if self.exit_btn.state()[0] == 'active' :
            self.disconnect()
            self.root.destroy()
            sys.exit()

    # show used to # print strings on the connection state scrolled text box
    def show(self,string):
        self.connection_state_text.configure(state = 'normal')
        self.connection_state_text.insert(tk.END,'\n'+string)
        self.connection_state_text.configure(state = 'disabled')

    # the initialization function
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

        self.port_description_frame = ttk.Labelframe(self.connection_parameter_frame)
        self.port_description_frame.place(relx=0.018, rely=0.519, relheight=0.333
                                          , relwidth=0.714, bordermode='ignore')
        self.port_description_frame.configure(relief='')
        self.port_description_frame.configure(text='''network_parameters''')
        self.port_description_frame.configure(width=400)

        self.port_entry = ttk.Entry(self.port_description_frame)
        self.port_entry.place(relx=0.025, rely=0.444, relheight=0.467, relwidth=0.33, bordermode='ignore')
        self.port_entry.configure(takefocus="")
        self.port_entry.configure(cursor="ibeam")

        self.ip_entry = ttk.Entry(self.port_description_frame)
        self.ip_entry.place(relx=0.37, rely=0.444, relheight=0.467, relwidth=0.596, bordermode='ignore')
        self.ip_entry.configure(takefocus="")
        self.ip_entry.configure(cursor="ibeam")

        self.connect_button = ttk.Button(self.connection_parameter_frame)
        self.connect_button.place(relx=0.804, rely=0.34, height=25, width=76
                                  , bordermode='ignore')
        self.connect_button.configure(text='''connect''')
        self.connect_button.configure(command=lambda e='': self.start1(e))

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
        self.getIP()
        self.ip_entry.insert(0, self.ip)
        self.port_entry.insert(0, self.port)
        self.path=str(os.path.expanduser('~/'))
        os.chdir(self.path)
        try:
            os.mkdir(self.device_name)
        except FileExistsError:
            pass
        os.chdir(self.path + self.device_name)
        # print(os.getcwd())
        self.globalCode2localCode()

        self.dbc()
        try:
            self.dbc('''
                    CREATE TABLE sample(
                    barcode unsigned int primary key,
                    created_at datetime not null default current_timestamp
                    )
                ''')
        except sqlite3.OperationalError as e:
            # print('already exists')
            if str(e)[-6:] == 'exists':
                pass
            else:
                raise sqlite3.OperationalError


        try:
            self.dbc('''
                    CREATE TABLE counter(
                    id unsigned int primary key not null default 1,
                    count unsigned int not null default 1
                    )
                ''')
            self.dbc('insert into counter(id,count) values(1,1);')
        except sqlite3.OperationalError as e:
            # print('already exists')
            if str(e)[-6:] == 'exists':
                pass
            else:
                raise sqlite3.OperationalError



        try:
            self.dbc('''
                    CREATE TABLE test(
                    test_id unsigned int primary key not null,
                    barcodeid varchar(30) not null,
                    results varchar(20000) not null,
                    uploadstate varchar(1) default 'n',
                    created_at datetime not null default current_timestamp,
                    FOREIGN KEY(barcodeid) REFERENCES user(barcode)
                    );
                ''')
        except sqlite3.OperationalError as e:
            # print('already exists')
            if str(e)[-6:] == 'exists':
                pass
            else:
                raise sqlite3.OperationalError


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

#
aia = Toplevel1()
aia.root.mainloop()

