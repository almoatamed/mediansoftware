import tkinter as tk
import tkinter.ttk as ttk
import requests
import serial
import serial.tools.list_ports
import serial.urlhandler
import os
import requests
import sys
import time
import platform
import sqlite3
import threading
from threading import Timer
import base64

py3 = True


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
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


class Toplevel1:
    # the device name
    device_name = 'Mindray-BC2800'

    frames = [''.encode('ascii')]
    repeatingInterval = 0.2
    results = {}
    last_result = {}

    # port specifications
    port_description = None
    port = serial.Serial()
    rate = 9600
    bitlength = serial.EIGHTBITS
    parity = serial.PARITY_NONE
    stopbit = serial.STOPBITS_ONE

    # api parameters
    sampleid = b'sample_code'
    apigetter = 'http://165.22.27.138/lims/v1/sample/tests'
    apisetter = 'http://165.22.27.138/lims/v1/results/devices/submit'
    writing = False
    daemon = True

    # reutuns an instance of the serial connection
    # the serial connection established is
    # based on the parameters specified at the begenning of the class
    def get_port(self):
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if self.port_entry.get() in p.description:
                try:
                    s = serial.Serial(p.device, self.rate, self.bitlength, self.parity, self.stopbit)
                except:
                    self.show('ERROR: error while trying to open the port')
                    return None
                if not s.is_open:
                    s.open()
                return s
        self.show('ERROR: port has not been found')
        return None

    # turns of the connect button
    # gets serial connection and if the serial is valid
    # then enables the disconnect button
    # initialize frame
    # and start the repeated timer for loap function instance with a given repeating interval
    def run(self):
        self.connect_button.configure(state='disabled')
        self.port = self.get_port()
        if self.port:
            self.show('connecting...')
            self.disconnect_button.configure(state='enable')
            self.frames = [''.encode('ascii')]
            self.running = True
            self.Thread = threading.Thread(target=self.looper)
            self.Thread.start()
        else:
            self.show('ERROR: there is no connection')
            self.connect_button.configure(state='enable')

    # if the port is open it will stop repeated timer loap function
    # and the closes the port and enables the connect button
    # finally disabled the disconnect button
    def disconnect(self):
        try:
            if self.port.is_open:
                self.running = False
                self.port.close()
                self.show('disconnected')
                self.connect_button.configure(state='enable')
                self.disconnect_button.configure(state='disable')
        except:
            self.show('ERROR: there is no port to be closed')

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
                self.testsetuploaded(sample[0])
                print(resp.json())
                return 'done'
            else:
                print(resp.status_code)
                print(resp.content.decode())
                return 'connection error'
        except:
                return 'upload: connection error'


    # craete a connection
    def dbc(self, d=''):
        # print(d)
        os.chdir(self.path + self.device_name)
        # print('dbc', os.getcwd())
        if d:
            with sqlite3.connect('median.db') as cnxn:
                # print('first with')
                c = cnxn.cursor()
                x = list(c.execute(d))
                c.close()
            return x

    # update counter where counter is used as the test id
    def cset(self):
        self.dbc('update counter set count = ' + str(self.cget() + 1) + \
             ' where id = 1 ')
        return True

    # gets counter
    def cget(self):
        x = self.dbc('select count from counter where id = 1 ')[0][0]
        return x

    # inserts test that currespond to a given barcode to the database
    def testset(self, result):
        self.dbc('insert into test(test_id,barcodeid,results) values('
                 '' + str(self.cget()) + ',"' + result['id'] + '","' + str(result['result']) + '");')
        self.cset()
        return True

    # gets the test result for a sample
    def testget(self, barcode):
        return self.dbc('select * from test where barcodeid="' + str(barcode)+'"')

    # upload the state of given test to uploaded
    def testseterror(self, test):
        print('setting uploaded')
        if self.dbc('update test set uploadstate = "e" where test_id = ' + str(test)):
            return True
        else:
            return False

    # upload the state of given test to uploaded
    def testsetuploaded(self, test):
        print('setting uploaded')
        if self.dbc('update test set uploadstate = "y" where test_id = ' + str(test)):
            return True
        else:
            return False

    # upload the last test result and
    # try to upload unuploaded tests
    def writer(self, result):
        print('Writer: result,',result)
        self.testset(result)
        self.attemptUpload()

    # write clicked create connection
    # and gets test results where the upload state is "n"
    # which means not uploaded
    def attemptUpload(self):
        samples = self.dbc('select * from test where uploadstate =\
            "n" order by created_at desc')
        # for i in samples:
        #     print(i)
        #     print('\n')
        if len(samples) == 0:
            return
        for sample in samples:
            parms = self.getSampleParameters(sample[1])
            if parms == 'nc':
                print('attemptUpload: nc')
                return
            # this condition check is the test code it within the parms
            # brought from the api LIMS
            # for the given barcode
            # note that test[1] is the barcode it self
            if parms:
                print(sample[2])
                string = sample[2][1:-1].split(',')
                print(string)
                testlist = []
                for test in string:
                    test = test.split(':')
                    print(test)
                    testlist.append({test[0].strip()[1:-1]: \
                         test[1].strip()[1:-1]})
                print(testlist)
                samplelist = []
                samplelist.append(sample[0])
                samplelist.append(sample[1])
                samplelist.append(testlist)
                print(samplelist)
                self.upload(samplelist)
            else:
                self.testseterror(sample[0])

    # the main loap that check if something is to be read from the serial port and if it is it starts
    # while loop that reads byte by byte and
    def looper(self):
        # \x05 -> ENQ or the code the instrument sends to establish a connection
        # \x06 -> ACK or acknowoledged which indicate every thing is ready and we're listening
        # \x15 -> NACK or written to serial that data is not acknowledged which indicate failure in the checksum
        # \x0A -> LF or indicate the end of frame
        # \x04 -> EOT or indicate close the link (the end of the communication)
        try:
            try:
                if not self.string1:
                    pass
            except:
                self.string1 = b''
            while True:
                d = self.port.read(1)
                if not self.running:
                    return False
                if d == b'\x10':
                    print('looper: ack')
                    self.port.write(b'\x06')
                    time.sleep(0.1)
                    continue
                self.string1 += d
                if len(self.string1)>10:
                    if self.string1[-3:] == b'\x08\x04\n':
                        startTime= time.time()
                        print('looper: end of frame')
                        try:
                            messages = self.string1.split(b'\x08\x04')
                            print('looper: message recieved')
                            for message in messages:
                                print('looper: message',message)
                            self.string1 = b''
                            if not ( b'CTR' in messages[0]):
                                print('looper: not a result message')
                                continue
                            result = {}
                            r = {
                                'id':messages[0][messages[0].index(b'SampleID') + 9:messages[0].index(b'\x08Mode')].decode()
                            }
                            for message in messages[1:]:
                                try:
                                    if b'Histo' in message:
                                        print('looper: message processing, histo message detected')
                                        result[message[:message.index(b'\x0c')].decode()] = base64.b64encode(message[message.index(b'HistoData\x16') + len(b'HistoData\x16'):]).decode()
                                    else:
                                        result[message[:message.index(b'\x0c')].decode()] = message[message.index(b'Val\x16')+4:message.index(b'\x08Low')].decode()
                                except:
                                    print('looper: error, error in message processing',message)
                                    pass
                            r['result'] = result
                            print('looper: writing result to DB and iuploading')
                            while self.writing == True:
                                print('looper: waiting for another thread to end')
                                time.sleep(1)
                            self.writing = True
                            self.writer(r)
                            self.writing = False
                            print('looper: message handling, finiished processing')
                        except:
                            print('looper: error occured in result processing')
                            pass
                        self.string1 = b''
                        finish = time.time() - startTime
                        print('Communicate: processing time is ',finish)
                        self.port.write(b'\x06')
        except serial.serialutil.SerialException:
            self.show('Looper: ERROR serial has been disconnected ')
            self.disconnect()

    # turns off the connect button and start the run function
    # this function only works if the connection button is active
    def connect(self, p1):
        if self.connect_button.state()[0] == 'active':
            self.show('starting')
            self.run()

    # exit1 is basically a disconnect button
    # it check if the disconnect button is active or not
    # and if it is it runs the disconnect button
    def exit1(self, p1):
        if self.disconnect_button.state()[0] == 'active':
            self.disconnect()

    # exit2 is basically a program close button it check is the exit button is working and then
    # it calls the disconnect and the root.destroy functions
    # and finally close the program with sys.close
    def exit2(self, p1):
        if self.exit_btn.state()[0] == 'active':
            self.disconnect()
            self.root.destroy()
            sys.exit()

    # show used to print strings on the connection state scrolled text box
    def show(self, string):
        self.connection_state_text.configure(state='normal')
        self.connection_state_text.insert(tk.END, '\n' + string)
        self.connection_state_text.configure(state='disabled')

    # list available port in the dropbox specified for that
    def initiate_port_entry(self):
        x = list(serial.tools.list_ports.comports())
        print('the list of ports', len(x), )
        list_values = []
        for i in x:
            list_values.append(i.description)
        self.port_entry.configure(values=list_values)

    # initializa interface and create database if not existing
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
        self.port_description_frame.configure(text='''serial_port''')
        self.port_description_frame.configure(width=400)

        self.portlist = tk.StringVar()
        self.port_entry = ttk.Combobox(self.port_description_frame)
        self.port_entry.place(relx=0.025, rely=0.444, relheight=0.467, relwidth=0.94, bordermode='ignore')
        self.port_entry.configure(takefocus="")
        self.port_entry.configure(textvariable=self.portlist)
        self.port_entry.configure(cursor="ibeam")
        self.initiate_port_entry()

        self.connect_button = ttk.Button(self.connection_parameter_frame)
        self.connect_button.place(relx=0.804, rely=0.34, height=25, width=76
                                  , bordermode='ignore')
        self.connect_button.configure(text='''connect''')
        self.connect_button.bind('<Button-1>', lambda e: self.connect(e))

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

        self.path = str(os.path.expanduser('~/'))
        os.chdir(self.path)
        try:
            os.mkdir(self.device_name)
        except FileExistsError:
            pass
        os.chdir(self.path + self.device_name)

        self.port_entry.insert(0, 'USB-SERIAL CH340')

        try:
            self.dbc('''
                    CREATE TABLE counter(
                    id unsigned int primary key not null default 1,
                    count unsigned int not null default 1
                    )
                ''')
            self.dbc('insert into counter(id,count) values(1,1);')
        except sqlite3.OperationalError as e:
            print('already exists')
            if str(e)[-6:] == 'exists':
                pass
            else:
                raise sqlite3.OperationalError

        try:
            self.dbc('''
                    CREATE TABLE test(
                    test_id unsigned int primary key not null,
                    barcodeid varchar(30) not null,
                    results varchar(10000) not null,
                    uploadstate varchar(1) default 'n',
                    created_at datetime not null default current_timestamp,
                    FOREIGN KEY(barcodeid) REFERENCES user(barcode)
                    );
                ''')
        except sqlite3.OperationalError as e:
            print('already exists')
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

        # self.configure(yscrollcommand=_autoscroll(vsb),
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
        widget.yview_scroll(-1 * int(event.delta / 120), 'units')
    elif platform.system() == 'Darwin':
        widget.yview_scroll(-1 * int(event.delta), 'units')
    else:
        if event.num == 4:
            widget.yview_scroll(-1, 'units')
        elif event.num == 5:
            widget.yview_scroll(1, 'units')


def _on_shiftmouse(event, widget):
    if platform.system() == 'Windows':
        widget.xview_scroll(-1 * int(event.delta / 120), 'units')
    elif platform.system() == 'Darwin':
        widget.xview_scroll(-1 * int(event.delta), 'units')
    else:
        if event.num == 4:
            widget.xview_scroll(-1, 'units')
        elif event.num == 5:
            widget.xview_scroll(1, 'units')


instance = Toplevel1()
instance.root.mainloop()