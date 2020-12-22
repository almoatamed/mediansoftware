import tkinter as tk
import tkinter.ttk as ttk
import serial
import serial.tools.list_ports
import serial.urlhandler
import os
import requests
import sys
import time
import platform
import threading
import sqlite3
from threading import Timer

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
    instrumentName = 'Roche-Cobas-Integra-400-Plus'

    results = {}
    last_result = {}
    SC = 'n'
    IDLE =    b'\x01\n09_COBAS_INTEGRA   _00\n\x02\n\x03\n\x04\n'
    IDLE2 =   b'\x0114 COBAS INTEGRA400 00\x0A\x02\x0A\x03\x0A\x04\x0A'
    IDLEResponse = b'\x01\x0A09_INTEGRA\x2030-1051\x20_00\x0A\x02\x0A\x03\x0A1\x0A299\x0A\x04\x0A'
    RQ =      b'\x01\n09_COBAS_INTEGRA   _09\n\x02\n10_07\n\x03\n'
    OQ =      b'\x01\n09_COBAS_INTEGRA   _60\n\x02\n40_1\n\x03\n'
    RQready = b'\x01\n09_COBAS_INTEGRA   _09\n\x02\n10_07\n\x03\n0\n872\n\x04\n'
    LF = b'\n'

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

    daemon = True

    # reutuns an instance of the serial connection
    # the serial connection established is
    # based on the parameters specified at the begenning of the class
    def getPort(self):
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if self.port_entry.get() in p.description:
                try:
                    s = serial.Serial(p.device, self.rate, self.bitlength, self.parity, self.stopbit,timeout=10)
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
        print('run: running ')
        self.connect_button.configure(state='disabled')
        self.port = self.getPort()
        if self.port:
            print('run: port established')
            self.show('connecting...')
            self.disconnect_button.configure(state='enable')
            self.handling = False
            self.Thread = threading.Thread(target=self.communicate)
            self.Thread.start()
        else:
            self.show('ERROR: there is no connection')
            self.connect_button.configure(state='enable')

    def communicate(self):
        print('communicate')
        if not self.handling:
            print('handling')
            self.handling = True
            try:
                if not self.syncSC():
                    print('communicate: error no response from send receive at sync')
                    self.disconnect()
                    return False
                q = 0
                while True:
                    if not self.handling:
                        return False
                    if not q%2:
                        print('communicate: sending result request')
                        message = self.sendRecv(self.RQ)
                        print('Communicate: ',message)
                        if not message:
                            print('communicate: error no response from send reciee at result response')
                            self.disconnect()
                            return False
                        else:
                            msg = message[0]
                            msgType = message[1]
                            if b'00' in msgType:
                                time.sleep(30)
                                q = (q+1)%2
                            elif b'04' in msgType:
                                print('communicate: result have been found')
                                lines = [[i for i in j.split(b' ') if i] for j in msg.split(self.LF) if j]
                                for line in lines:
                                    print('communicate: line, ',line)
                                codes = {}
                                codekeys = [b'55',b'53',b'00']
                                print('communicate: code keys, ', codekeys)
                                for i,line in zip(range(len(lines)),lines):
                                    for key in codekeys:
                                        print('communicate: key of code keys,',key,'line',line,'i',i)
                                        if key in line[0:3]:
                                            codes[key] = i
                                print('Communicate: codes',codes)
                                if len(codes) != 3:
                                    print('Communicate: Error in line codes', codes)
                                    continue
                                try:
                                    TestCode = lines[codes[b'55']][1]
                                    SampleBarcode = lines[codes[b'53']][1]
                                    TestResult = lines[codes[b'00']][1]
                                    print('communicate: testcode',TestCode,'SampleBarcode',SampleBarcode)
                                    if (TestCode.decode() in self.l2g):
                                        r = {'id':SampleBarcode.decode(),'result':{self.l2g[TestCode.decode()]:TestResult.decode()}}
                                    else:
                                        r = {'id':SampleBarcode.decode(), 'result': {TestCode.decode(): TestResult.decode()}}
                                    self.writer(r)
                                    time.sleep(1)
                                except:
                                    continue
                            else:
                                self.disconnect()
                                return False
                    else:
                        print('communicate: OQ part')
                        message = self.sendRecv(self.OQ)
                        print('Communicate: OQ response',message)
                        if not message:
                            print('communicate: error no response from send reciee at order response')
                            self.disconnect()
                            return False
                        else:
                            msg = message[0]
                            msgType = message[1]
                            if b'62' in msgType:
                                print('Communicate: request is ordered.')
                                lines = [[i.strip() for i in j.split(b'_') if i.strip()] for j in msg.split(self.LF) if j and (b'42_' in j[0:4])]
                                for line in lines:
                                    print('communicate: 42_ requests given line', line)
                                    try:
                                        required_tests = self.getSampleParameters(line[4].decode())
                                    except:
                                        print('Communicate: OQ, Error while getting sample parameters')
                                        continue
                                    if required_tests == 'nc':
                                        continue
                                    if not required_tests:
                                        print('communicate: preparing order response, no such barcode found on LIMS')
                                        continue
                                    print('communicate: the giving tests required for this sample', required_tests)
                                    available_tests = []
                                    for test in required_tests:
                                        if test in self.g2l:
                                            available_tests.append(test)
                                        else:
                                            print('communication: test was not found in G2L')
                                    if not available_tests:
                                        print('communicate: preparing order response, no matching tests has been found')
                                        continue
                                    print('communicate: the following matching tests has been found')
                                    message = b'\x01\n09_COBAS_INTEGRA   _10\n\x02\n'
                                    message += b'53_' + line[4] + b' '*(15-len(line[4])) + b'_00/00/0000_   \n'
                                    message += b'54_000_00_S_' + b' '*21 + b'_' + b' '*21 + b'\n'
                                    i = 0
                                    for test in available_tests:
                                        i +=1
                                        if i == 50:
                                            print('communicate: setting tests, overloading, over 50 test')
                                            break
                                        message += b'55_' + b' '*(3-len(test)) + self.g2l[test].encode() + b'\n'
                                    message += b'\x03\n'
                                    print('communicate: order response, ', message)
                                    response = self.sendRecv(message)
                                    if not response:
                                        print('communicate: error no response from send reciee at order response')
                                        self.disconnect()
                                        return False
                                    else:
                                        msg = response[0]
                                        msgType = response[1]
                                        if b'19' in msgType:
                                            if b'\n96_00\n' in msg:
                                                print('communicate: order after response message, succesfull and no errors')
                                            else:
                                                print('communicate: order after response message, error occured')
                                            continue
                                        else:
                                            print('communicate: order after response, error no valid response')
                                            print('communicate: msg',msg)
                                            print('communicate: type',msgType)
                                            continue
                            else:
                                print('communicate: OQ response, not 62 block',msg)
                                q = (q+1)%2
                                time.sleep(15)
                                continue
            except serial.serialutil.SerialException:
                self.show('Looper: ERROR serial has been disconnected ')
                self.disconnect()

    l2g = {
        '893':'VALPM',
        '3':'UREL',
        '463':'UIBC',
        '615':'UA2',
        '10':'TRIGL',
        '163':'TPU3',
        '27':'TP2',
        '263':'TPC3',
        '757':'RF-II',
        '614':'PHOS2',
        '887':'PHNYM',
        '286':'PHNOM',
        '168':'NH3L',
        '601':'NA-U',
        '501':'NA-I',
        '401':'NA-D',
        '701':'MG-2',
        '59':'MG',
        '100':'LIPC',
        '404':'LI-D',
        '452':'LDLC3',
        '212':'LDHL',
        '607':'LDHI2',
        '606':'LACT2',
        '602':'K-U',
        '502':'K-I',
        '402':'K-D',
        '596':'IRON2',
        '77':'IGM',
        '276':'IGGT',
        '75':'IGA',
        '389':'HDLC4',
        '331':'HDLC3',
        '265':'HB-W3',
        '128':'HB-W2',
        '31':'GLUC3',
        '51':'GLU3C',
        '498':'GG2I2',
        '278':'FER2P',
        '293':'CRPL2',
        '33':'CRPHS',
        '279':'CRP4',
        '445':'CREJ2',
        '512':'CRE2U',
        '603':'CL-U',
        '503':'CL-I',
        '403':'CL-D',
        '324':'CKMBL',
        '57':'CKMB2',
        '323':'CKL',
        '45':'CK2',
        '586':'CHOL2',
        '282':'CARBM',
        '42':'CA2',
        '261':'C4-2',
        '280':'C3C-2',
        '712':'BILT3',
        '734':'BILD2',
        '494':'ASTL',
        '664':'ASO2',
        '609':'AMYL2',
        '495':'ALTL',
        '551':'ALP2S',
        '550':'ALP2L',
        '171':'ALBU2',
        '592':'ALB2',
        '266':'A1-W3',
        '228':'A1-W2',
    }
    g2l = {}

    def syncSC(self):
        x = 1
        while x < 8:
            self.port.write(self.IDLE)
            print('syncSC: ')
            message = self.messageReader()
            print('syncSC: message: ',message)
            if not message:
                return False
            print('syncSC: receiving msg')
            print('syncSC: checksum, ',message[0:-6], int(message.split(self.LF)[-3][0:3].replace(b' ', b'')))
            if not self.checkSum(message[0:-6], int(message.split(self.LF)[-3][0:3].replace(b' ',b''))):
                if x == 7:
                    self.show('syncSC: exiting, several times checksum error')
                    return False
                self.show('syncSC: checksum error')
                x += 1
                time.sleep(2)
                continue
            else:
                self.SC = (int(message.split(self.LF)[-4][0]) + 1) % 2
                return True

    # serial.Serial('COM4',9600,serial.EIGHTBITS,serial.PARITY_NONE,serial.STOPBITS_ONE)
    def sendRecv(self, sendmsg):
        x = 1
        while x < 8:
            print('sendRecv: sending message', sendmsg)
            scSendMsg = sendmsg + str(self.SC).encode() + b'\x0A'
            print('sendRecv: sending message with SC', scSendMsg)
            cksmSendMsg = self.checkSumCreator(scSendMsg)
            print('sendRecv: sending message with CkSM', cksmSendMsg)
            self.port.write(cksmSendMsg)
            print('sendRecv: receiving msg')
            message = self.messageReader()
            if not message:
                return False
            if not self.checkSum(message[0:-6], int(message.split(self.LF)[-3][0:3].replace(b' ',b''))):
                if x == 7:
                    return False
                print('checksum error')
                x += 1
                continue
            else:
                self.SC = (int(message.split(self.LF)[-4][0]) + 1) % 2
                print('SendRecv: SC, ',self.SC,(int(message.split(self.LF)[-4][0]) + 1) % 2)
                rcvMsgType = message.split(self.LF)[1][-3:].strip()
                print('SendRecv: rcvMsgType, ',rcvMsgType)
                return message, rcvMsgType

    # the main loap that check if something is to be read from the serial port and if it is it starts
    # while loop that reads byte by byte and
    def messageReader(self):
        message = b''
        while True:
            data = self.port.read(1)
            if data == b'':
                self.show('Reader: ERROR, no response from the instrument')
                return False
            if data == b'\x01':
                print('message reader: started receiving new message')
                message = data
            elif data == self.LF:
                message += data
                print('message reader: End of frame,',message)
                print('message reader: \\x04',message[-2])
                if b'\x04\n' in message:
                    return message
            elif data:
                message += data

    # if the port is open it will stop repeated timer loap function
    # and the closes the port and enables the connect button
    # finally disabled the disconnect button
    def disconnect(self):
        try:
            if self.port.is_open:
                self.Handling =False
                self.port.close()
                self.show('disconnected')
                self.connect_button.configure(state='enable')
                self.disconnect_button.configure(state='disable')
        except:
            self.show('ERROR: there is no port to be closed')

    # creating check sum for given serial message
    def checkSumCreator(self, msg):
        chksum = str(sum(msg) % 1000).encode()
        return msg + b'\x20'*(3-len(chksum)) + chksum + b'\x0A\x04\x0A'

    # check the check sume for given message
    def checkSum(self, message, checksum):
        print('checksum: message',message)
        print('checksum:',(sum(message) % 1000),checksum)
        return (sum(message) % 1000) == checksum

    # upload the last test result and
    # try to upload unuploaded tests
    def writer(self, result):
        self.last_result = result
        print('writer: result,',self.last_result)
        self.testset(self.last_result)
        self.attemptUpload()

    # write clicked create connection
    # and gets test results where the upload state is "n"
    # which means not uploaded
    def attemptUpload(self):
        print('attemptUpload: start')
        samples = self.dbc('select * from test where uploadstate = "n" order by created_at desc')
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
            # this condition check is the test code it within the parms brought from the api LIMS
            # for the given barcode
            # note that test[1] is the barcode it self
            if parms:
                print('attemptUpload: sample result string,',sample[2])
                string = sample[2][1:-1].split(',')
                testlist = []
                for test in string:
                    test = test.split(':')
                    testlist.append({test[0].strip()[1:-1]: test[1].strip()[1:-1]})
                samplelist = []
                samplelist.append(sample[0])
                samplelist.append(sample[1])
                samplelist.append(testlist)
                print('attemptUpload: sample result object,',samplelist)
                self.upload(samplelist)
            else:
                self.testseterror(sample[0])

    # contact the LIMS api through a given url and gets the sample data
    # using barcode
    def getSampleParameters(self, sampleBarCode):
        sampleBarCode = str(sampleBarCode)
        print('getSampleParameters:',self.sampleid + b'=' + sampleBarCode.encode())
        try:
            resp = requests.get(self.apigetter, params=self.sampleid + b'=' + sampleBarCode.encode(),timeout=2)
            if resp.status_code == 200:
                respjson = resp.json()
                print('getSampleParameters: respjson,',respjson)
                if 'error' in respjson:
                    return False
                required_tests = []
                for i in respjson[0]['parameters']:
                    required_tests.append(i['code'])
                print('getSampleParameters: required_tests,',required_tests)
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
        record = {'id': sample[1], 'instrument_code': self.instrumentName}
        print('uploader: recorde',record)
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
        print('uploader: final record,',record)
        try:
            resp = requests.post(self.apisetter, json=record)
            if resp.status_code == 200:
                self.testsetuploaded(sample[0])
                print('uloader: json response',resp.json())
                return 'done'
            else:
                print('uploader: Error Status code',resp.status_code)
                print('uploader: Error content',resp.content.decode())
                return 'connection error'
        except:
                return 'upload: connection error'

    # craete a connection
    def dbc(self, d=''):
        print('dbc: query',d)
        os.chdir(self.path + self.instrumentName)
        print('dbc: current working directory,', os.getcwd())
        if d:
            with sqlite3.connect('median.db') as cnxn:
                print('dbc: Establishing cnxn (First With)')
                c = cnxn.cursor()
                x = list(c.execute(d))
                c.close()
            return x

    # update counter where counter is used as the test id
    def cset(self):
        self.dbc('update counter set count = ' + str(self.cget() + 1) + ' where id = 1 ')
        return True

    # gets counter
    def cget(self):
        x = self.dbc('select count from counter where id = 1 ')[0][0]
        return x

    # inserts test that currespond to a given barcode to the database
    def testset(self, result):
        self.dbc('insert into test(test_id,barcodeid,results) values('
                 '' + str(self.cget()) + ',' + result['id'] + ',"' + str(result['result']) + '");')
        self.cset()
        return True

    # gets the test result for a sample
    def testget(self, barcode):
        return self.dbc('select * from test where barcodeid=' + str(barcode))

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

        for key in self.l2g:
            self.g2l[self.l2g[key]] = key

        print('__init__: l2g,',self.l2g)

        self.path = str(os.path.expanduser('~/'))
        os.chdir(self.path)
        try:
            os.mkdir(self.instrumentName)
        except FileExistsError:
            pass
        os.chdir(self.path + self.instrumentName)

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
            # print('already exists')
            if str(e)[-6:] == 'exists':
                pass
            else:
                raise sqlite3.OperationalError

        try:
            self.dbc('''
                    CREATE TABLE test(
                    test_id unsigned int primary key not null,
                    barcodeid unsigned int not null,
                    results varchar(10000) not null,
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
