#-*- coding:utf-8 -*-
from lib import *

class Protocol(object):
    def connection_made(self, transport):
        pass

    def data_received(self, data):
        pass

    def connection_lost(self, exc):
        if isinstance(exc, Exception):
            raise exc


class ReaderThread(threading.Thread):
    def __init__(self, serial_instance, protocol_factory):
        super(ReaderThread, self).__init__()
        self.daemon = True
        self.serial = serial_instance
        self.protocol_factory = protocol_factory
        self.alive = True
        self._lock = threading.Lock()
        self._connection_made = threading.Event()
        self.protocol = None

    def stop(self):
        self.alive = False
        try:
            if hasattr(self.serial, 'cancel_read'):
                self.serial.cancel_read()
            self.join(2)
        except Exception as e:
            pass


    def run(self):
        global token
        if not hasattr(self.serial, 'cancel_read'):
            self.serial.timeout = 1
        self.protocol = self.protocol_factory()
        try:
            self.protocol.connection_made(self)
        except Exception as e:
            self.alive = False
            self.protocol.connection_lost(e)
            self._connection_made.set()
            return
        error = None
        self._connection_made.set()
        while self.alive and self.serial.isOpen() and token != 2:
            try:
                data = self.serial.read(1)
            except serial.SerialException as e:
                error = e
                #print("run()-1", str(e))
                break
            else:
                if data:
                    try:
                        self.protocol.data_received(data)
                    except Exception as e:
                        error = e
                        #print("run()-2", str(e))
                        #break
        self.alive = False
        self.protocol.connection_lost(error)
        self.protocol = None

    def write(self, data):
        with self._lock:
            print(data)
            self.serial.write(data)

    def close(self):
        with self._lock:
            self.stop()
            self.serial.close()

    def connect(self):
        if self.alive:
            self._connection_made.wait()
            if not self.alive:
                raise RuntimeError('connection_lost already called')
            return (self, self.protocol)
        else:
            raise RuntimeError('already stopped')

    def __enter__(self):
        self.start()
        self._connection_made.wait()
        if not self.alive:
            raise RuntimeError('connection_lost already called')
        return self.protocol

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class rawProtocal(Protocol):
    def __init__(self):
        self.no = 0
        self.sw = 0
        self.canframe = []
        self.count = 0
        self.CANList = []
        self.CAN_static_dynamic_List = []
        self.OBD_PID_List = []

    # 연결 시작시 발생
    def connection_made(self, transport):
        self.transport = transport
        self.running = True

    # 연결 종료시 발생
    def connection_lost(self, exc):
        self.transport = None
        self.running = False

    def push_canframe(self):
        end = time.perf_counter()
        can_time = end - start
        canid = '0x'+hex(int.from_bytes((self.canframe[0] + self.canframe[1]), byteorder='big'))[2:].zfill(3)
        dlc = int.from_bytes(self.canframe[2], byteorder='big')
        canframe2 = ["{:.12f}".format(can_time), canid, dlc] + list('0x'+hex(int.from_bytes(self.canframe[i], byteorder='big'))[2:].zfill(2) for i in range(3, len(self.canframe)))
        self.CANList.append(canframe2)
        if len(self.CANList) > 30000:
            self.CAN_static_dynamic_List += self.CANList
            for CANmsg in self.CANList:
                line = ''
                for a in CANmsg[:-1]:
                    line += str(a).strip()+"\t"
                line += CANmsg[-1]
                fw.write(line+'\n')
            self.CANList.clear()
        if canid == '0x7e8':
            OBDList.append(canframe2)

    def data_received(self, data):
        global token, start
        if self.count > 80 and data != b'\xff' and self.sw == 0:
            self.sw, token = 1, 1
            start = time.perf_counter()
            logger.debug("CAN data receive start")
            self.canframe.append(data)
        elif data == b'\xff' and self.sw == 0:
            self.count = self.count+1
        elif self.sw == 1 and len(self.canframe) == 11:
            self.push_canframe()
            self.canframe = [data]
        elif self.sw == 1 and len(self.canframe) < 11:
            self.canframe.append(data)
        else:
            count = 0

    # 데이터 보낼 때 함수
    def write(self,data):
        print(data)
        self.transport.write(data)

    # 종료 체크
    def isDone(self):
        return self.running

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
f_hdlr = logging.FileHandler('log.txt')
fmt = logging.Formatter("[%(asctime)s - %(lineno)d] %(threadName)s: %(message)s")
f_hdlr.setFormatter(fmt)
f_hdlr.setLevel(logging.DEBUG)
s_hdlr = logging.StreamHandler()
s_hdlr.setFormatter(fmt)
s_hdlr.setLevel(logging.INFO)
logger.addHandler(f_hdlr)
logger.addHandler(s_hdlr)
start = 0

conf_file = 'config.ini'
config = configparser.ConfigParser()
config.read(conf_file, encoding='utf-8')

ser = serial.serial_for_url(config.get('Setting', 'port'), baudrate=115200, timeout=1)
token = 0
current_OBD = -1
OBDList = []
CAN_analysis_dict = {}
fw = None
next_num = None
raw_filename = None

def can_log_setting():
    global fw, next_num, raw_filename
    can_data_log_path = config.get('CANdata_log', 'path')
    filelist = os.listdir('CANdata_log')
    filelist2 = os.listdir('Backup_CANdata_log')
    numbers = set()
    if len(filelist) >= 6:
        for file in filelist:
            shutil.move('./CANdata_log/'+file, './Backup_CANdata_log/'+file)
    if len(filelist) == 0:
        next_num = 1
    else:
        for file in filelist:
            try:
                if file[0] != '~':
                    numbers.add(int(file.split('.')[0]))
            except Exception as e:
                print("LOG_SETTING ERROR", str(e), 'exit')
                exit(0)
        for file in filelist2:
            if file[0] != '~':
                numbers.add(int(file.split('.')[0]))
        next_num = max(numbers) + 1
    raw_filename = config.get('CANdata_log', 'raw_messages_filename')
    fw = open(can_data_log_path[2:]+"/%s. %s_%s.txt" % (next_num, raw_filename, datetime.datetime.now().strftime('%Y-%m-%d')), 'w')

def start_can():
    global token
    while token == 0:
        ser.write(b'\xff')
        time.sleep(1)

def end_can():
    global token, ser, p
    if token == 1:
        logger.info("CAN Communication Finish")
        try:
            token = 2
            ser.close()
        except Exception as e:
            pass


def load_csv():
    with open('./OBD_II.csv','r') as f:
        data = f.readlines()
        return data


def OBD_info(csv_data, PID):
    for row in csv_data:
        field = row.split(',')
        try:
            if int(field[0], 16) == PID:
                return field[0], int(field[1]), int(field[2]), field[3]
        except Exception as e:
            print(field[0], PID)
            print(str(e))
            exit(0)


def makeTable(_field_names, _Datafield):
    x = PrettyTable(padding_width=0)
    #Datafield = []
    x.field_names = _field_names
    for row in _Datafield:
        x.add_row(row)
    x.sortby = "CAN ID"
    return str(x)

def generate_Xlsx(_worksheet, _stationary_info):
    row, col = 0, 0
    _worksheet.set_column(1, 8, 22)
    for key, val in _stationary_info.items():
        col = 0
        _worksheet.write(row, col, key, wrap)
        col = col + 1
        for for_row in _stationary_info[key]:
            elements_list = list(for_row)
            i, input_string = 1, ''
            for element in elements_list:
                if i % 5 == 0:
                    input_string += element + '\n'
                else:
                    input_string += element + ' '
                i = i + 1
                _worksheet.write(row, col, input_string, wrap)
            col = col + 1
        row += 1

def analysis_exit(_analysis_time):
    return time.time()-_analysis_time


def loadSetting():
    return [config.get('CANdata_log', 'path'), open('config.ini', 'r').readlines()]


def finding_obd_queries():
    supported_OBD_List_str = config.get('Finding available OBD-II PID queries', 'supported_OBD_List').split(',')
    Supported_OBD_PIDs, hex_Supported_OBD_PIDs = [], []
    if ',' in supported_OBD_List_str:
        OBD_Supported_PIDs_List = [int(PID.strip()) for PID in supported_OBD_List_str]
        Supported_OBD_PIDs, hex_Supported_OBD_PIDs = OBD_Supported_PIDs_List, [hex(pid) for pid in OBD_Supported_PIDs_List]
    else:
        Finding_available_OBD_II_time = float(
            config.get('Finding available OBD-II PID queries', 'finding_supported_OBD_PID_time'))
        Request_PID_LIST, Find_PID_LIST = list(i * 32 for i in range(0, 7)), []
        OBD_Supported_PIDs_List = []
        start_time = time.time()
        while Finding_available_OBD_II_time > time.time() - start_time:
            for PID in Request_PID_LIST:
                ser.write(PID.to_bytes(1, byteorder='big'))
                logger.info("PID %s Send(delay: %s)" % (hex(PID), request_delay_time))
                time.sleep(request_delay_time)
            templist = p.CANList
            for temp in templist:
                PID = int(temp[5], 16)
                if temp[1] == '0x7e8' and PID % 32 == 0:
                    try:
                        if PID in Request_PID_LIST:
                            Request_PID_LIST.remove(PID)
                            Find_PID_LIST.append(PID)
                    except Exception as e:
                        print("ERROR-1", str(e), "exit(0)")
                        print(PID)
                        print(Request_PID_LIST)
                        exit(0)
                    if temp[1:] not in OBD_Supported_PIDs_List:
                        OBD_Supported_PIDs_List.append(temp[1:])
        Enabled_OBD_PIDs = '0' * 192
        Find_PID_LIST.sort()
        logger.info("PID: " + str(Find_PID_LIST))
        for CANframe in OBD_Supported_PIDs_List:
            base = int(CANframe[4], 16)
            temp = ''
            for i in range(5, 9):
                try:
                    if CANframe[i] == '0x0':
                        temp += ''.zfill(8)
                    elif len(CANframe[i]) == 3:
                        temp += bin(int(CANframe[i][2], 16))[2:].zfill(4) + ''.zfill(4)
                    else:
                        temp += bin(int(CANframe[i][2], 16))[2:].zfill(4) + bin(int(CANframe[i][3], 16))[2:].zfill(4)
                except Exception as e:
                    print("ERROR-2", str(e))
                    exit(0)
            Enabled_OBD_PIDs = Enabled_OBD_PIDs[:base] + temp + temp[base:]
        for i in range(len(Enabled_OBD_PIDs)):
            if Enabled_OBD_PIDs[i] == '1':
                Supported_OBD_PIDs.append(i + 1)
                hex_Supported_OBD_PIDs.append(hex(i + 1))
    logger.info("Supported OBD PIDs: %s\n" % hex_Supported_OBD_PIDs)
    return Supported_OBD_PIDs, hex_Supported_OBD_PIDs

def input_each_PIDs(Supported_OBD_PIDs):
    PID_sleep_time = float(config.get('Input each OBD-II PID queries', 'PID_sleep_time'))
    analysis_PID_count = int(config.get('Input each OBD-II PID queries', 'analysis_PID_count'))
    if analysis_PID_count > 0:
        Supported_OBD_PIDs = Supported_OBD_PIDs[:analysis_PID_count]

    for PID in Supported_OBD_PIDs:
        ser.write(PID.to_bytes(1, byteorder='big'))
        time.sleep(PID_sleep_time)
        logger.info("PID %s[%s] Analysis" % (PID, hex(PID)))
        for temp in OBDList:
            if int(temp[5], 16) == PID:
                logger.info(str(temp).strip())
    logger.info("Finish!\n")


with ReaderThread(ser, rawProtocal) as p:
    can_log_setting()
    start_can()
    request_delay_time = float(config.get('Finding available OBD-II PID queries', 'request_delay_time'))
    if p.isDone():
        return_value = loadSetting()
        can_data_log_path, config_lines = return_value[0], return_value[1]
        analysis_time = time.time()
        report_filename = config.get('CANdata_log', 'analysis_filename')
        report_filename2 = can_data_log_path[2:] + "/%s. %s_%s.xlsx" % (next_num, report_filename, datetime.datetime.now().strftime('%Y-%m-%d'))
        workbook = xlsxwriter.Workbook('%s' % report_filename2)
        worksheet = workbook.add_worksheet('Config')
        config_row_index, config_col_index = 0, 0
        for config_row in config_lines:
            worksheet.write(config_row_index, config_col_index, str(config_row.strip()))
            config_row_index += 1

    logger.info("1. Finding available OBD-II PID queries")
    Supported_OBD_PIDs, Hex_Supported_OBD_PIDs = finding_obd_queries()

    logger.info("2.1. Input each OBD-II PID queries\n")
    input_each_PIDs(Supported_OBD_PIDs)

    logger.info("2.2. analysis OBD-II PID and CAN ID\n")
    logger.info("Analyze CAN ID Count: %s" % len(p.CANList))
    for CANmsg in p.CANList:
        line = ''
        for a in CANmsg[:-1]:
            line += str(a).strip() + "\t"
        line += CANmsg[-1]
        fw.write(line + '\n')
    fw.close()
    file_name = "/%s. %s_%s.txt" % (next_num, raw_filename, datetime.datetime.now().strftime('%Y-%m-%d'))
    fr_raw_file = open(can_data_log_path[2:] + file_name, 'r')
    data_lines = fr_raw_file.read().split('\n')[:-1]
    OBDList_timestamp = []
    OBDList_timestamp_num = []
    for OBD in OBDList:
        OBDList_timestamp.append(OBD[0])
    for i in range(len(data_lines)):
        if data_lines[i].split('\t')[0] in OBDList_timestamp:
            #logger.info("%sth %s" % (i, data_lines[i]))
            OBDList_timestamp_num.append(str(i)+'\t'+data_lines[i])
    temp_list = []

    analysis_CAN_data_count = int(config.get('Input each OBD-II PID queries', 'analysis_CAN_data_count'))
    obd_dict = {}
    for row in Hex_Supported_OBD_PIDs:
        obd_dict[row] = []
    for OBD_PID in Hex_Supported_OBD_PIDs:
        for row in OBDList_timestamp_num:
            row_split = row.split('\t')
            if OBD_PID == row_split[6]:
                obd_dict[OBD_PID].append(row)
    found_obd_pid, not_found_obd_pid = [], []
    for key, value in obd_dict.copy().items():
        if len(value) >= 1:
            found_obd_pid.append(key)
        else:
            not_found_obd_pid.append(key)
            if key in obd_dict: del obd_dict[key]
    logger.info("found: %s" % found_obd_pid)
    logger.info("Not found: %s" % not_found_obd_pid)
    csv_data = load_csv()

    analysis_pid_dict, analysis_pid_dict2 = {}, {}

    for key, value in obd_dict.items():
        analysis_pid_dict[key] = []

    for key, value in obd_dict.items():
        logger.info("Analysis PID: %s" % str(key))
        analysis_list = value
        PID_hex, PID_int, Return_Bytes_Cnt, PID_name = OBD_info(csv_data, int(key, 16))
        PID_hex = '0x'+PID_hex
        for row in analysis_list:
            data_field = row.split('\t')[4:]
            obd_pid_count_offset = int(row.split('\t')[0])
            analysis_data_lines = data_lines[obd_pid_count_offset-analysis_CAN_data_count:obd_pid_count_offset+analysis_CAN_data_count]
            Return_Bytes = data_field[3:3 + Return_Bytes_Cnt]
            if Return_Bytes == ['0x00'] or Return_Bytes == ['0x00', '0x00'] or Return_Bytes == ['0x00', '0x00', '0x00'] or \
                Return_Bytes == ['0x00', '0x00', '0x00', '0x00'] or Return_Bytes == ['0x00', '0x00', '0x00', '0x00', '0x00']:
                continue
            elif Return_Bytes != Return_Bytes[::-1]:
                all_Return_Bytes = [Return_Bytes, Return_Bytes[::-1]]
            else:
                all_Return_Bytes = Return_Bytes
            for i in range(len(analysis_data_lines)):
                if analysis_data_lines[i].split('\t')[1] != '0x7e8':
                    data_field = analysis_data_lines[i].split('\t')[3:]
                    mark = 0
                    for analysis_return_bytes in all_Return_Bytes:
                        if type(analysis_return_bytes) is str:
                            analysis_return_bytes = [analysis_return_bytes]
                        for j in range(len(data_field)):
                            if analysis_return_bytes == data_field[j:j+Return_Bytes_Cnt]:
                                if mark == 0:
                                    matching_type = 'forward'
                                else:
                                    matching_type = 'reverse'
                                if j+Return_Bytes_Cnt >= 8:
                                    end_pos = 7
                                else:
                                    end_pos = j+Return_Bytes_Cnt-1
                                data = (str(analysis_data_lines[i]), str(analysis_return_bytes), matching_type, str(j) + '-' + str(end_pos))
                                logger.info("FOUND / " + str(analysis_data_lines[i]) + ' / ' +str(analysis_return_bytes) +' / ' + matching_type)
                                analysis_pid_dict[key].append(data)
                                break
                        mark = mark + 1
    logger.info(analysis_pid_dict)

    for key, value in analysis_pid_dict.items():
        if len(value) >= 1:
            analysis_pid_dict2[key] = []

    for key, value in analysis_pid_dict.items():
        if len(value) >= 1:
            for row in value:
                can_id = row[0].split('\t')[1]
                data_field = row[0].split('\t')[3:]
                location = row[3]
                analysis_pid_dict2[key].append((can_id, data_field, location))

    analysis_pid_dict3 = {}
    for key, value in analysis_pid_dict2.items():
        temp = value
        temp_dict = {}
        for row in value:
            print(row)
            temp_dict[row[0]+','+row[2]] = 0
        for row in value:
            temp_dict[row[0] + ',' + row[2]] += 1
        temp_dict = sorted(temp_dict.items(), key=operator.itemgetter(1), reverse=True)
        analysis_pid_dict3[key] = temp_dict

    worksheet = workbook.add_worksheet('CAN msg candidates related PID')

    worksheet_row_index, worksheet_col_index = 0, 0
    worksheet.write(worksheet_row_index, worksheet_col_index, 'PID'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'CAN ID'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'Data Byte Offset'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'Count'); worksheet_col_index = 0; worksheet_row_index += 1

    for key, value in analysis_pid_dict3.items():
        for row in value:
            worksheet.write(worksheet_row_index, worksheet_col_index, str(key.strip()))
            worksheet.write(worksheet_row_index, worksheet_col_index + 1, str(row[0].split(',')[0]))
            worksheet.write(worksheet_row_index, worksheet_col_index + 2, str(row[0].split(',')[1]))
            worksheet.write(worksheet_row_index, worksheet_col_index + 3, str(row[1]))
            worksheet_row_index += 1
        worksheet_row_index += 1

    for key, value in analysis_pid_dict3.items():
        print_line = key+' / '+str(value[0])
        logger.info(print_line)

    worksheet = workbook.add_worksheet('CAN msg related PID')

    worksheet_row_index, worksheet_col_index = 0, 0
    worksheet.write(worksheet_row_index, worksheet_col_index, 'PID'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'CAN ID'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'Data Byte Offset'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'Count'); worksheet_col_index = 0; worksheet_row_index += 1

    for key, value in analysis_pid_dict3.items():
        worksheet.write(worksheet_row_index, worksheet_col_index, str(key.strip()))
        worksheet.write(worksheet_row_index, worksheet_col_index+1, str(value[0][0].split(',')[0]))
        worksheet.write(worksheet_row_index, worksheet_col_index+2, str(value[0][0].split(',')[1]))
        worksheet.write(worksheet_row_index, worksheet_col_index+3, str(value[0][1]))
        worksheet_row_index += 1

    injection_time = float(config.get('CAN messages injection to real vehicles', 'injection_time'))

    ser.write(b'\xfe')

    worksheet = workbook.add_worksheet('CAN injection result')
    worksheet_row_index, worksheet_col_index = 0, 0
    worksheet.write(worksheet_row_index, worksheet_col_index, 'PID'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'Description'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'CAN ID'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'Data Field(Offset)'); worksheet_col_index += 1
    worksheet.write(worksheet_row_index, worksheet_col_index, 'Vehicle Status'); worksheet_col_index = 0;
    worksheet_row_index += 1

    for key, value in analysis_pid_dict3.items():
        worksheet_col_index = 0
        logger.info("PID: %s/injection time: %s" % (key, injection_time))
        logger.info(str(value[0]))
        start_pos, end_pos = value[0][0].split(',')[1].split('-')
        PID_INT = int(key, 16)
        injection_msg_0 = int(PID_INT / 100)
        injection_msg_1 = PID_INT % 100

        start_time = time.time()
        while injection_time >= time.time() - start_time:
            ser.write(injection_msg_0.to_bytes(1, byteorder='big'))
            ser.write(injection_msg_1.to_bytes(1, byteorder='big'))
            for i in range(0, 8):
                pass
                if int(start_pos) <= i <= int(end_pos):
                    ser.write(b'\xff')
                else:
                    ser.write(b'\x00')
            time.sleep(0.001)
        vehicle_status = input("input vehicle status: ")
        PID_hex, PID_int, Return_Bytes_Cnt, PID_name = OBD_info(csv_data, int(key, 16))
        worksheet.write(worksheet_row_index, worksheet_col_index, key); worksheet_col_index += 1
        worksheet.write(worksheet_row_index, worksheet_col_index, PID_name); worksheet_col_index += 1
        worksheet.write(worksheet_row_index, worksheet_col_index, value[0][0].split(',')[0]); worksheet_col_index += 1
        worksheet.write(worksheet_row_index, worksheet_col_index, value[0][0].split(',')[1]); worksheet_col_index += 1
        worksheet.write(worksheet_row_index, worksheet_col_index, vehicle_status); worksheet_col_index += 1
        worksheet_row_index += 1
    workbook.close()
    end_can()