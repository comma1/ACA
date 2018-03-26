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
        if hasattr(self.serial, 'cancel_read'):
            self.serial.cancel_read()
        self.join(2)

    def run(self):
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
        while self.alive and self.serial.isOpen():
            try:
                data = self.serial.read(1)
            except serial.SerialException as e:
                error = e
                break
            else:
                if data:
                    try:
                        self.protocol.data_received(data)
                    except Exception as e:
                        error = e
                        print(str(e))
                        break
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

ser = serial.serial_for_url(config.get('Setting','port'), baudrate=115200, timeout=1)
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
            except:
                print("HERE")
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
    global token
    if token == 1:
        logger.info("CAN 통신 종료")
        token = 0
    # while token == 1:
    #     ser.write(b'\xff')
    #     time.sleep(1)

def generateTable():
    time.sleep(static_dynamic_stationary_analysis_time)
    CANList = p.CANList + p.CAN_static_dynamic_List
    temp = dict()
    for CANmsg in CANList:
        try:
            CAN_analysis_dict[CANmsg[1]].append(CANmsg)
        except Exception as e:
            if CANmsg[0] not in CAN_analysis_dict.keys():
                CAN_analysis_dict[CANmsg[1]] = []
                CAN_analysis_dict[CANmsg[1]].append(CANmsg)
            else:
                logger.debug("ERROR-" + str(e))
    logger.info("CAN Message Count: %s / CAN ID Count: %s" % (len(CANList), len(CAN_analysis_dict.keys())))
    for key, value in CAN_analysis_dict.items():
        logger.debug("분석할 CAN ID: %s" % key)
        CANData_analysis = [set(), set(), set(), set(), set(), set(), set(), set()]
        for CANmsg in value:
            for i in range(3, 11):
                CANData_analysis[i - 3].add(CANmsg[i])
        logger.debug(CANData_analysis)
        temp[key] = CANData_analysis
    x = PrettyTable(padding_width=0)
    Datafield = []
    for i in range(1, 9):
        Datafield.append("DATA[%s]" % i)
    x.field_names = ['CAN ID'] + Datafield
    for k, v in temp.items():
        temp_list = []
        for items in v:
            str_temp = ''
            items = sorted(list(items))
            i = 1
            for item in items[:-1]:
                str_temp += item + ' '
                if i % 5 == 0:
                    str_temp += '\n'
                i = i + 1
            str_temp += items[-1]
            temp_list.append(str_temp)
        x.add_row([k] + temp_list)
    x.sortby = "CAN ID"
    return str(x), temp


def load_csv():
    with open('./OBD_II.csv','r') as f:
        data = f.readlines()
        return data


def OBD_info(csv_data, PID):
    for row in csv_data:
        field = row.split(',')
        if int(field[0]) == PID:
            return field[0], int(field[1]), int(field[2]), field[3]


def find_OBD_relevant_CANID(_data_lines, _Return_Bytes, _Return_Bytes_Cnt, _analysis_CAN_data_count, _index, _type):
    return_value = []
    if _index - _analysis_CAN_data_count >= 0:
        _start = _index - _analysis_CAN_data_count
    else:
        _start = 0
    for j in range(_start, _index):
        data_lines_split = _data_lines[j].split('\t')
        if data_lines_split[1] == '0x7e8':
            continue
        _CAN_Data_field = data_lines_split[3:]
        for byte_index in range(0, len(_CAN_Data_field) - _Return_Bytes_Cnt + 1):
            sw = 1
            byte_start = byte_index
            for l in range(_Return_Bytes_Cnt):
                try:
                    if _CAN_Data_field[byte_index + l] != _Return_Bytes[l]:
                        sw = 0
                        break
                    else:
                        pass
                except Exception as e:
                    logger.info("ERROR l:%s" % l)
                    logger.info("ERROR byte_index:%s " % byte_index)
                    logger.info("ERROR %s" % str(e))
                    exit(0)
            if sw == 1:
                return_value.append((_data_lines[j], _Return_Bytes, byte_start+1, byte_index+Return_Bytes_Cnt, _type))
                logger.debug("FIND: %s %s %s %s" % (_data_lines[j], _Return_Bytes, byte_start+1, byte_index+Return_Bytes_Cnt))
    return return_value

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
    return [int(config.get('static_dynamic', 'static_dynamic_stationary_analysis_time')),
            int(config.get('static_dynamic', 'static_dynamic_driving_analysis_time')),
            config.get('CANdata_log', 'path'),
            open('config.ini', 'r').readlines()]

with ReaderThread(ser, rawProtocal) as p:
    can_log_setting()
    start_can()

    while p.isDone():
        return_value = loadSetting()
        static_dynamic_stationary_analysis_time, static_dynamic_driving_analysis_time, can_data_log_path, config_lines =\
        return_value[0], return_value[1], return_value[2], return_value[3]
        analysis_time = time.time()
        report_filename = config.get('CANdata_log', 'analysis_filename')
        report_filename2 = can_data_log_path[2:] + "/%s. %s_%s.xlsx" % (next_num, report_filename, datetime.datetime.now().strftime('%Y-%m-%d'))
        workbook = xlsxwriter.Workbook('%s' % report_filename2)
        worksheet = workbook.add_worksheet('Config')
        config_row_index, config_col_index = 0, 0
        for config_row in config_lines:
            worksheet.write(config_row_index, config_col_index, str(config_row.strip()))
            config_row_index += 1

        wrap = workbook.add_format()
        wrap.set_text_wrap(); wrap.set_align('center'); wrap.set_align('vcenter')
        worksheet = workbook.add_worksheet('stationary_table')
        logger.info("1. Classifying static or dynamic field)")
        logger.info("1-1. [Stationary] CAN Analysis(%ss)" % static_dynamic_stationary_analysis_time)
        stationary_table, stationary_info = generateTable()
        generate_Xlsx(worksheet, stationary_info)
        p.CAN_static_dynamic_List.clear()
        p.CANList.clear()
        #input("driving state ready?")
        time.sleep(static_dynamic_driving_analysis_time)
        logger.info("1-2. [Driving] CAN Analysis(%ss)" % static_dynamic_driving_analysis_time)
        worksheet2 = workbook.add_worksheet('driving_table');
        row, col = 0, 0
        driving_table, driving_info = generateTable()
        generate_Xlsx(worksheet2, driving_info)
        p.CAN_static_dynamic_List.clear(); p.CANList.clear()

        # worksheet = workbook.add_worksheet("Static => Dynamic analysis")
        # worksheet.set_column(0, 0, 22)
        CAN_ID_associated_with_engine_dict = {}
        CAN_ID_associated_with_unless_dict = {}
        for key, val in driving_info.items():
            for i in range(len(val)):
                col = 0
                try:
                    if key in ('0x7e8', '0x7e9'):
                        worksheet.write(row, col, "[%s] Except CAN ID" % key)
                        row = row+1
                        break
                    elif val[i] != stationary_info[key][i]:
                        try:
                            CAN_ID_associated_with_engine_dict[key].append(i+1)
                        except:
                            CAN_ID_associated_with_engine_dict[key] = [i+1]
                        #worksheet.write(row, col, "[%s][%d] driving: %s" % (key, i+1, val[i])); row = row+1
                        #worksheet.write(row, col, "[%s][%d] stationary: %s" % (key, i + 1, stationary_info[key][i])); row = row + 1
                    elif val[i] == stationary_info[key][i] and len(val[i]) == 1 and len(val[i]) == 1:
                        try:
                            CAN_ID_associated_with_unless_dict[key].append(i + 1)
                        except:
                            CAN_ID_associated_with_unless_dict[key] = [i + 1]
                        # worksheet.write(row, col, "UNLESS(driving)");col = col + 1;
                        # worksheet.write(row, col, key);col = col + 1;
                        # worksheet.write(row, col, str(i+1));col = col + 1;
                        # worksheet.write(row, col, str(val[i]));col = col + 1;
                        # row = row + 1; col = 0
                        # worksheet.write(row, col, "UNLESS(stationary)");col = col +1;
                        # worksheet.write(row, col, key);col = col + 1;
                        # worksheet.write(row, col, str(i + 1));col = col + 1;
                        # worksheet.write(row, col, str(stationary_info[key][i]));col = col + 1;
                        # row = row + 1;
                except Exception as e:
                    print(str(e))
                    worksheet.write(row, col, "ERROR CAN ID: %s" % key);
                    exit(0)
                    row = row + 1
                    break

        worksheet = workbook.add_worksheet("CAN_ID_associated_with_engine")
        row, col = 0, 0
        for key, val in CAN_ID_associated_with_engine_dict.items():
            col = 0
            worksheet.write(row, col, str(key)); col = col+1
            worksheet.write(row, col, str(val))
            row = row + 1
        worksheet = workbook.add_worksheet("CAN_ID_associated_unless_dict")
        row, col = 0, 0
        for key, val in CAN_ID_associated_with_unless_dict.items():
            col = 0
            worksheet.write(row, col, str(key)); col = col + 1
            worksheet.write(row, col, str(val))
            row = row + 1
        analysis_time = analysis_exit(_analysis_time=analysis_time)
        workbook.worksheets_objs[0].write(config_row_index, config_col_index, 'analysis_time')
        config_col_index = config_col_index + 1
        workbook.worksheets_objs[0].write(config_row_index, config_col_index, analysis_time)
        workbook.close()

        print("");logger.info("2. Finding available OBD-II PID queries")
        OBD_Supported_PIDs_List = [int(PID.strip()) for PID in config.get('Finding available OBD-II PID queries', 'supported_OBD_List').split(',')]
        if len(OBD_Supported_PIDs_List) < 5:
            Finding_available_OBD_II_time = float(config.get('Finding available OBD-II PID queries', 'finding_supported_OBD_PID_time'))
            Request_PID_LIST = list(i*32 for i in range(0, 7))
            OBD_Supported_PIDs_List = []
            temp_time = time.time()
            for i in range(1, 5):
            #while Finding_available_OBD_II_time > time.time() - temp_time:
                logger.info(OBD_Supported_PIDs_List)
                for PID in Request_PID_LIST:
                    ser.write(PID.to_bytes(1, byteorder='big'))
                    logger.info("PID %s SEND.. sleep(2)" % PID)
                    time.sleep(1)
                templist = p.CANList
                for temp in templist:
                    PID = int(temp[5], 16)
                    if temp[1] == '0x7e8' and PID % 32 == 0:
                        try:
                            if PID in Request_PID_LIST:
                                Request_PID_LIST.remove(PID)
                        except:
                            print("ERROR-1")
                            print(PID)
                            print(Request_PID_LIST)
                            exit(0)
                        logger.info(temp)
                        if temp[1:] not in OBD_Supported_PIDs_List:
                            OBD_Supported_PIDs_List.append(temp[1:])

            Enabled_OBD_PIDs = '0'*192
            for CANframe in OBD_Supported_PIDs_List:
                base = int(CANframe[4],16)
                temp = ''
                for i in range(5, 9):
                    try:
                        if CANframe[i] == '0x0':
                            temp += ''.zfill(8)
                        elif len(CANframe[i]) == 3:
                            temp += bin(int(CANframe[i][2], 16))[2:].zfill(4) + ''.zfill(4)
                        else:
                            temp += bin(int(CANframe[i][2], 16))[2:].zfill(4) + bin(int(CANframe[i][3], 16))[2:].zfill(4)
                    except:
                        print("ERROR-2")
                        exit(0)
                Enabled_OBD_PIDs = Enabled_OBD_PIDs[:base]+temp+temp[base:]
            Supported_OBD_PIDs = []
            for i in range(len(Enabled_OBD_PIDs)):
                if Enabled_OBD_PIDs[i] == '1':
                    Supported_OBD_PIDs.append(i+1)
        else:
            Supported_OBD_PIDs = OBD_Supported_PIDs_List
        logger.info("Already Supported OBD PIDs: %s." % Supported_OBD_PIDs)

        logger.info("2.1. Input each OBD-II PID queries\n")
        PID_sleep_time = int(config.get('Input each OBD-II PID queries', 'PID_sleep_time'))
        analysis_PID_count = int(config.get('Input each OBD-II PID queries', 'analysis_PID_count'))
        if analysis_PID_count > 0:
            Supported_OBD_PIDs = Supported_OBD_PIDs[:analysis_PID_count]

        for PID in Supported_OBD_PIDs:
            ser.write(PID.to_bytes(1, byteorder='big'))
            time.sleep(PID_sleep_time)
            logger.info("PID %s[%s] 분석" % (PID, hex(PID)))
            for temp in OBDList:
                if int(temp[5], 16) == PID:
                    logger.info(temp)

        logger.info("2.2. analysis OBD-II PID and CAN ID\n")
        break
    #end_can()
    logger.info("분석할 CAN ID 개수: %s" % len(p.CANList))
    for CANmsg in p.CANList:
        line = ''
        for a in CANmsg[:-1]:
            line += str(a).strip() + "\t"
        line += CANmsg[-1]
        fw.write(line + '\n')
    fw.close()
    fr_raw_file = open(can_data_log_path[2:] + "/%s. %s_%s.txt" % (next_num, raw_filename, datetime.datetime.now().strftime('%Y-%m-%d')), 'r')
    data_lines = fr_raw_file.read().split('\n')[:-1]
    OBDList_timestamp = []
    OBDList_timestamp_num = []
    for OBD in OBDList:
        OBDList_timestamp.append(OBD[0])
    for i in range(len(data_lines)):
        if data_lines[i].split('\t')[0] in OBDList_timestamp:
            logger.info("%s번째 %s" % (i, data_lines[i]))
            OBDList_timestamp_num.append(str(i)+'\t'+data_lines[i])
    temp_list = []

    analysis_CAN_data_count = int(config.get('Input each OBD-II PID queries', 'analysis_CAN_data_count'))
    csv_data = load_csv()

    engine_info = config.get('static_dynamic', 'CAN_ID_associated_with_engine').split('-')
    engine_info_list = []
    for row in engine_info:
        row_field = row.split('>')
        CAN_ID = row_field[0].strip()
        info = [row.strip() for row in row_field[1].strip()[1:-1].split(',')]
        engine_info_list.append([CAN_ID, info])

    unless_candata_info = config.get('static_dynamic', 'CAN_ID_associated_with_unless_dict').split('-')
    unless_info_list = []
    for row in unless_candata_info:
        row_field = row.split('>')
        CAN_ID = row_field[0].strip()
        info = [row.strip() for row in row_field[1].strip()[1:-1].split(',')]
        unless_info_list.append([CAN_ID, info])

    for OBD in OBDList_timestamp_num:
        OBD_split_list = OBD.split("\t")
        index = int(OBD_split_list[0])
        logger.info("%s 분석" % OBD)
        PID_int, PID_hex, Return_Bytes_Cnt, PID_name = OBD_info(csv_data, int(OBD_split_list[6], 16))
        Return_Bytes = OBD_split_list[7:7 + Return_Bytes_Cnt]
        forward_return_values = find_OBD_relevant_CANID(data_lines, Return_Bytes, Return_Bytes_Cnt, analysis_CAN_data_count, index, 'Forward')
        Reverse_Return_Bytes = Return_Bytes[::-1]
        reverse_return_values = find_OBD_relevant_CANID(data_lines, Reverse_Return_Bytes, Return_Bytes_Cnt, analysis_CAN_data_count, index, 'Reverse')
        all_return_values = forward_return_values + reverse_return_values
        for row in all_return_values:
            can_info = row[0].split('\t')
            data__field = [None, None, None, None, None, None, None, None]
            z = 0
            for i in range(8):
                if (int(row[2])-1) <= i <= (int(row[3])-1):
                    data__field[i] = row[1][z]
                    z = z+1
                else:
                    data__field[i] = '0'
            temp_row = [PID_int, PID_name, can_info[1]] + data__field + [row[4]]
            engine_check = 0
            for row in engine_info_list:
                if row[0] == can_info[1]:
                    engine_check = 1
                    temp_row += [str(row[1])]
                    break
            if engine_check == 0:
                temp_row += ['']
            unless_check = 0
            for row in unless_info_list:
                if row[0] == can_info[1]:
                    unless_check = 1
                    temp_row += [str(row[1])]
                    break
            if unless_check == 0:
                temp_row += ['']
            if temp_row not in temp_list:
                temp_list.append(temp_row)
    field_names = ['PID', 'Description', 'CAN ID'] + [("DATA[%s]" % i) for i in range(1, 9)] + ['Type'] + ['engine', 'unless']
    logger.info("\n"+makeTable(field_names, temp_list))
    print("FINISH")