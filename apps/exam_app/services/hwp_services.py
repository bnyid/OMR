# apps/exam_app/services/hwp_services.py
from pprint import pprint
from pyhwpx import Hwp
import pythoncom, traceback, psutil, re
from bs4 import BeautifulSoup

############## 안전 실행 START #################

class HwpProcessManager:
    @staticmethod
    def kill_hwp_processes():
        try:
            for proc in psutil.process_iter():
                try:
                    if proc.name().lower() in ['hwp.exe', 'hword.exe']:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"HWP 프로세스 종료 중 오류: {e}")

    @staticmethod
    def safe_hwp_quit(hwp):
        try:
            if hwp:
                hwp.Clear(3)  # 모든 문서 닫기
                hwp.Quit()
                pythoncom.CoUninitialize()
        except Exception as e:
            print(f"HWP 종료 중 오류: {e}")
            HwpProcessManager.kill_hwp_processes()
            
############## 안전 실행 END #################

### 각종 extract 함수들

def extract_text_from_block_lines(hwp):  
    """_summary_
    여러 문단의 블록 텍스트 추출(non-HTML)

    Args:
        hwp (Hwp): 한글 객체

    Returns:
        str: 추출된 텍스트(non-HTML)
    """
    result_text = ""
    hwp.InitScan(range=0xff)  # 스캔 초기화
    
    while True:
        state, text = hwp.GetText()
        
        # 상태 체크
        if state <= 1:  # 텍스트가 없거나 끝난 경우
            break
            
        result_text += text  # 텍스트 누적
        
    hwp.ReleaseScan()  # 스캔 해제
    return result_text

def extract_text_from_block(hwp):  
    """_summary_
    블록 내 텍스트 추출 한 문단(non-HTML)

    Returns:
        str: 추출된 텍스트(non-HTML)
    """
    hwp.InitScan(range=0xff)  # 0xff <<선택된 범위 내에서 검색
    _, text_blokced = hwp.GetText()  # 텍스트만 추출
    hwp.ReleaseScan() # 스캔을 해제.
    return text_blokced # 이경우, 해당 target이 text에 포함되어있으면 True, 아니면 False를 반환.

def extract_number_from_text(text):
    """
    텍스트에서 숫자(정수 또는 소수)를 추출하는 함수
    
    Args:
        text (str): 텍스트
        
    Returns:
        int or float or None : 추출된 숫자. 정수:int, 소수:float, 없으면: None
    """
    import re
    
    number_match = re.search(r'(\d+\.?\d*)', text)
    if number_match:
        number = float(number_match.group(1))
        # 정수인 경우 int로 변환
        return int(number) if number.is_integer() else number
    return None

def extract_detail_type(type_texts):
    """
    인덱스 텍스트(#)에서 세부 유형 리스트를 최대 2개 추출
    
    Args:
        type_texts (list): 유형 텍스트 리스트
                    
                Returns:
        list: 추출된 세부 유형 리스트(최대 2개)
    """
                
    detail_type_keywords = ['어법','어휘', '일치', '순서', '삽입', '제목', '주제', '요약', '빈칸', '함축', '영영풀이']            
    essay_type_keywords = ['논술형(어법)', '논술형(요약)', '논술형(영작)'] # 추후 수정 필요
    
    question_type_list = []
    detail_type = None
    for type_text in type_texts:
        # 논술형 먼저 파악
        for keyword in essay_type_keywords:
            # keyword = essay_type_keywords[0]
            if keyword in type_text:
                detail_type = keyword
                break
        # 논술형에서 세부유형이 없으면 객관식 세부유형 파악
        if detail_type is None:
            for keyword in detail_type_keywords:
                # keyword = detail_type_keywords[1]
                if keyword in type_text:
                    detail_type = keyword
                    break
        question_type_list.append(detail_type)
    return question_type_list

# 검색
def search_text(hwp, text,direction="Forward"):
    """
    특정 텍스트를 찾아서 블록 처리
    Args:
        text (str): 찾을 텍스트
        direction (optional): 찾기 방향(Forward, Backward, AllDoc)
    """
    hwp.SetMessageBoxMode(0x00020000) # 계속 찾으시겠습니까? No
    hwp.HAction.GetDefault("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    hwp.HParameterSet.HFindReplace.FindString = f"{text}"
    hwp.HParameterSet.HFindReplace.Direction = hwp.FindDir(f"{direction}")
    hwp.HParameterSet.HFindReplace.FindType = 1  
    hwp.HParameterSet.HFindReplace.UseWildCards = 1
    hwp.HParameterSet.HFindReplace.IgnoreMessage = 2  # 계속 찾을까요? 1=YES, 2=NO
    if hwp.HAction.Execute("RepeatFind", hwp.HParameterSet.HFindReplace.HSet):
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기기
        return True
    else:
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기기
        return False

def search_circled_number(hwp, number):
    """
    특정 숫자에 해당하는 모든 원문자의 앞으로 이동
    
    Args:
        hwp: 한글 객체
        number (int): 검색할 숫자 (1~5)
        
    Returns:
        bool: 검색 성공 여부
    """
    # 숫자별 원문자 매핑
    circled_numbers = {
        1: ['①', '❶', '➀'],
        2: ['②', '❷', '➁'],
        3: ['③', '❸', '➂'],
        4: ['④', '❹', '➃'],
        5: ['⑤', '❺', '➄']
    }
    
    if number not in circled_numbers:
        return False
        
    # 해당 숫자의 모든 원문자를 | 로 연결하여 검색어 생성
    search_string = '|'.join(circled_numbers[number])
    
    # 검색 실행
    hwp.SetMessageBoxMode(0x00020000)  # 계속 찾으시겠습니까? No
    hwp.HAction.GetDefault("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    hwp.HParameterSet.HFindReplace.FindString = f"{search_string}"
    hwp.HParameterSet.HFindReplace.Direction = hwp.FindDir("Forward")
    hwp.HParameterSet.HFindReplace.FindType = 1
    hwp.HParameterSet.HFindReplace.FindRegExp = 1  # 정규식 사용
    hwp.HParameterSet.HFindReplace.IgnoreMessage = 2
    
    if hwp.HAction.Execute("RepeatFind", hwp.HParameterSet.HFindReplace.HSet):
        result = True
        hwp.Run("MoveLeft")
        hwp.Run("MoveRight")
    else:
        result = False
    hwp.SetMessageBoxMode(0x000F0000)  # 기본값으로 돌리기
    
    return result
    
def go_to_faster_question(hwp,word):
    """_summary_
    다음 둘 중 빠른 위치로 이동함
    (1) 문단번호가 있는 문단 앞
    (2) 사용자가 입력한 단어 앞

    Args:
        hwp : 한글 객체
        word : 찾을 단어

    Returns:
        bool: 단어 앞으로 이동 성공 여부, 두 단어 모두 못찾은 경우 False
    """
    hwp.SetMessageBoxMode(0x20000) # 예/아니오 중에 아니오를 누름
    start_pos = hwp.GetPos()

    result1 = search_text(hwp,word)
    hwp.Run("MoveParaBegin")
    pos1 = hwp.GetPos() if result1 else None
        
    hwp.SetPos(*start_pos)
    
    result2 = go_to_index(hwp)
    hwp.Run("MoveParaBegin")
    
    pos2 = hwp.GetPos() if result2 else None
    
    hwp.SetPos(*start_pos)
    
    hwp.SetMessageBoxMode(0xF0000) # 경고창이 기본모드로 바뀜
    
    if not result1 and not result2:
        return False
    else:
        if not result1:  # word1을 못 찾은 경우
            hwp.SetPos(*pos2)
            return True
        elif not result2:  # word2를 못 찾은 경우
            hwp.SetPos(*pos1)
            return True
        else:  # 둘 다 찾은 경우
            if pos1[1] < pos2[1]:
                hwp.SetPos(*pos1)
            else:
                hwp.SetPos(*pos2)
            return True

def go_to_faster_word(hwp, word1, word2): 
    """_summary_
    두 단어 중 먼저 나오는 단어를 찾아 단어 앞으로 이동

    Args:
        hwp : 한글 객체
        word1 : 찾을 단어
        word2 : 찾을 단어

    Returns:
        bool: 단어 앞으로 이동 성공 여부, 두 단어 모두 못찾은 경우 False
    """
    hwp.SetMessageBoxMode(0x20000) # 예/아니오 중에 아니오를 누름
    start_pos = hwp.GetPos()

    result1 = search_text(hwp,word1)
    hwp.Run("MoveLeft")
    hwp.Run("MoveRight")
    pos1 = hwp.GetPos() if result1 else None
        
    hwp.SetPos(*start_pos)
    
    result2 = search_text(hwp,word2)
    hwp.Run("MoveLeft")
    hwp.Run("MoveRight")
    pos2 = hwp.GetPos() if result2 else None
    
    hwp.SetPos(*start_pos)
    
    hwp.SetMessageBoxMode(0xF0000) # 경고창이 기본모드로 바뀜
    
    if not result1 and not result2:
        return False
    else:
        if not result1:  # word1을 못 찾은 경우
            hwp.SetPos(*pos2)
            return True
        elif not result2:  # word2를 못 찾은 경우
            hwp.SetPos(*pos1)
            return True
        else:  # 둘 다 찾은 경우
            if pos1[1] < pos2[1]:
                hwp.SetPos(*pos1)
            else:
                hwp.SetPos(*pos2)
            return True

def go_to_index(hwp):
    """_summary_
    문단번호가 있는 문단 앞으로 이동

    Args:
        hwp : 한글 객체

    Returns:
        bool: 이동 성공 여부
    """
    hwp.SetMessageBoxMode(0x00020000) # 계속 찾으시겠습니까? No
    hwp.HAction.GetDefault("Goto", hwp.HParameterSet.HGotoE.HSet)
    hwp.HParameterSet.HGotoE.HSet.SetItem("DialogResult", 34)
    hwp.HParameterSet.HGotoE.SetSelectionIndex = 5
    if hwp.HAction.Execute("Goto", hwp.HParameterSet.HGotoE.HSet):
        hwp.Run("MoveParaBegin")
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기
        return True
    else:
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기
        return False
    
def search_text_condition(hwp, text): 
    """조건식사용에 체크하고 텍스트 검색

	Args:
		text (str): 찾을 텍스트(hwp 조건식 사용가능)
	"""
    hwp.SetMessageBoxMode(0x00020000) # 계속 찾으시겠습니까? 아니오
    hwp.HAction.GetDefault("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    hwp.HParameterSet.HFindReplace.FindString = f"{text}"
    hwp.HParameterSet.HFindReplace.Direction = hwp.FindDir("Forward")
    hwp.HParameterSet.HFindReplace.FindType = 1
    hwp.HParameterSet.HFindReplace.FindRegExp = 1 
    hwp.HParameterSet.HFindReplace.IgnoreMessage = 2
    if hwp.HAction.Execute("RepeatFind", hwp.HParameterSet.HFindReplace.HSet):
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기기
        return True
    else:
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기기
        return False

# 커서 행의 미주에 진입
def enter_note(hwp):
    """
    커서 행의 미주에 진입
    
    Args:
        hwp : 한글 객체
        
    Returns:
        bool: 미주 진입 성공 여부
    """
    hwp.Run("MoveParaBegin")
    hwp.SelectCtrlFront()
    hwp.Run("MoveRight")
    hwp.FindCtrl()
    return hwp.HAction.Run("NoteModify")

# 텍스트에서 입력된 원문자들을 인식해 일반 숫자 리스트로 변환
def convert_circled_number(text):
    """
    인자로 받은 텍스트 내 원문자들을 인식해 일반 숫자 리스트로 변환
    
    Args:
        text (str): 원문자가 포함된 텍스트
        
    Returns:
        list: 변환된 숫자들의 리스트. 원문자가 없으면 빈 리스트 반환
    """
    # 다양한 원문자 매핑
    circled_num_map = {
        '①': 1, '❶': 1, '➀': 1,  # 1에 해당하는 다양한 원문자
        '②': 2, '❷': 2, '➁': 2,  # 2에 해당하는 다양한 원문자
        '③': 3, '❸': 3, '➂': 3,  # 3에 해당하는 다양한 원문자
        '④': 4, '❹': 4, '➃': 4,  # 4에 해당하는 다양한 원문자
        '⑤': 5, '❺': 5, '➄': 5,  # 5에 해당하는 다양한 원문자
        # 필요한 만큼 추가
    }
    
    result = []
    
    # 텍스트를 순회하면서 원문자를 찾아 변환
    for char in text:
        if char in circled_num_map:
            result.append(circled_num_map[char])
            
    return result

def extract_source_from_index_text(index_text):
    """_summary_
    1) 인덱스 텍스트에서 '#' 제거, 
    2) 일련번호가 있는 경우 제거
    3) "-"을 기준으로 앞부분 출처 추출

    Args:
        index_text (str): 

    Returns:
        str: 추출된 출처 문자열
    """
    # '#' 제거
    text = index_text.lstrip('#').strip()
    
    # 일련번호가 있는 경우 처리
    if text.startswith('['):
        text = text.split(']', 1)[1].strip()
    
    # '-' 를 기준으로 분리하여 앞부분(source) 추출
    source = text.split('-')[0].strip()
    
    return source



 # 객관식 최종 리스트 생성

def merge_multiple_choice_data(data_list, type_source_list):
    q_multiple_final_list = []
    for (dict_1, dict_2) in zip(data_list, type_source_list):
        q_multiple_final_dict = {
            'number': dict_1.get('number'),
            'question_text': dict_1.get('question_text'),
            'answer': dict_1.get('answer'),
            'explanation': dict_1.get('explanation'),
            'score': dict_1.get('score'),
            'source': dict_2.get('source'),
            'detail_type': dict_2.get('detail_type')
        }
        q_multiple_final_list.append(q_multiple_final_dict)
    return q_multiple_final_list

def merge_essay_data(data_list, type_source_list):
    q_essay_final_list = []
    for (dict_1, dict_2) in zip(data_list, type_source_list):
        q_essay_final_dict = {
            'number': dict_1.get('number'),
            'question_text': dict_1.get('question_text'),
            'answer': dict_1.get('answer'),
            'score': dict_1.get('score'),
            'source': dict_2.get('source'),
            'detail_type': dict_2.get('detail_type')
        }
        q_essay_final_list.append(q_essay_final_dict)
    return q_essay_final_list

def has_content_in_block(hwp):
    """
    현재 선택된 블록 내에 텍스트나 표가 존재하는지 확인하는 함수
    
    Args:
        hwp: 한글 객체
        
    Returns:
        bool: 텍스트나 표가 존재하면 True, 없으면 False
    """
    # 텍스트 확인
    hwp.InitScan(range=0xff)
    _, text = hwp.GetText()
    hwp.ReleaseScan()
    has_text = bool(text.strip())
    
    # 표 확인
    has_table = hwp.GetTextFile(format="HWPML2X", option="saveblock:true").count("<TABLE") > 0
    
    return has_text or has_table

def extract_html_text_from_block(hwp):
    """
    블록으로 선택된 부분의 HTML 형태 서식 텍스트를 추출하는 함수.
    - 빈 문단은 건너뛰어 불필요한 <p></p> 제거
    - 문단 사이에 줄바꿈 추가
    - 표 구조 유지 (중복 없이)
    - 결과 문자열 앞뒤의 공백 및 줄바꿈 제거
    
    Args:
        hwp: 한글 객체 (Hwp)

    Returns:
        str: 처리된 HTML 텍스트
    """

    html_content = hwp.GetTextFile("HTML", "saveblock:true")
    if not html_content:
        return ""

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    body = soup.find('body')
    if not body:
        return ""

    # 문단과 표를 모두 찾음
    elements = body.find_all(['p', 'div', 'table'], recursive=False)

    result_soup = BeautifulSoup('<div></div>', 'html.parser')
    result_div = result_soup.div

    for element in elements:
        # 빈 요소 건너뛰기
        if not element.get_text(strip=True):
            continue

        if element.name == 'table':
            # 표인 경우 그대로 복사 (중복 방지)
            new_table = result_soup.new_tag('table')
            new_table.attrs = element.attrs  # 스타일 등 속성 복사
            
            # 표 내용을 직접 복사 (중첩된 BeautifulSoup 객체 생성 방지)
            new_table.extend(element.contents)
            result_div.append(new_table)
        else:
            # 문단인 경우 기존 로직 유지
            # span, p 태그에서 class 속성 제거
            for tag in element.find_all(['span', 'p']):
                if 'class' in tag.attrs:
                    del tag['class']

            new_p = result_soup.new_tag('p')
            new_p.append(BeautifulSoup(str(element), 'html.parser'))
            result_div.append(new_p)

        # 요소 사이 구분용 줄바꿈 추가
        result_div.append(result_soup.new_string('\n'))

    # div 제거
    result = str(result_div)[5:-6]

    # 앞뒤 공백 및 개행 제거
    result = result.strip()

    return result


##################################################################################################################################

def extract_exam_sheet_info(hwp_file_path,visible=False):
    """
    한글(HWP) 문서를 분석하여 시험지 정보를 추출하는 함수.
    
    주어진 한글 파일(hwp_file_path)을 열어, 문서 내 각 문항의 정보와 답안을 추출하여 
    문항별 정보를 담은 사전(dict)들의 리스트를 반환한다.
    
    Parameters:
        hwp_file_path (str):
            분석할 한글 파일의 전체 경로.
        visible (bool, optional):
            한글 문서의 창을 실제로 띄울지 여부. True인 경우 창이 표시되며, 기본값은 True.
    
    Returns:
        list of dict:
            추출된 문항 정보가 담긴 사전들의 리스트. 각 사전은 하나의 문항에 대한 정보를 포함하며,
            반환되는 사전은 다음과 같은 키를 가진다.
            
            +------------------+----------------------+---------------------------------------------------------------+
            | Key              | Type                 | Description                                                   |
            +------------------+----------------------+---------------------------------------------------------------+
            | order_number     | int                  | 전체 문항 중 해당 문항의 순번 (문항이 처리된 순서대로 증가하는 번호)   |
            | multi_or_essay   | str                  | 문항의 유형: "객관식" 또는 "논술형"                              |
            | number           | int                  | 해당 유형 내 문항 번호 (예: 객관식 문제면 multi_num, 논술형 문제면 essay_num)|
            | detail_type      | str                  | 문항의 세부 유형. 인덱스 텍스트에서 추출된 값으로, 예: "어법", "논술형(어법)" 등 |
            | question_text    | str                  | 문항의 본문 텍스트                                             |
            | answer           | str                  | 문항의 정답 텍스트                                             |
            | score            | int or float         | 문항에 부여된 점수. 추출된 점수 텍스트를 숫자형으로 변환한 값              |
            +------------------+----------------------+---------------------------------------------------------------+
    
    Raises:
        Exception:
            한글 파일을 열거나 문서 내 정보를 추출하는 과정 중 문제가 발생할 경우 예외를 발생시킨다.
    
    Notes:
        - 이 함수는 한컴오피스 한글의 COM 인터페이스를 활용하여 문서를 조작 및 분석한다.
        - 문서 내 특정 마커(예: "#", "##", "*", "{\d점}", "{\d\.\d점}")를 기준으로 각 영역을
          추출하여 문항 정보에 포함시킨다.
        - 추출된 문항 정보는 문서 내 출현 순서에 따라 order_number가 증가하며, 각 문항별로
          객관식과 논술형의 번호를 별도로 관리한다.
        - 함수 내부에서 사용된 보조 함수들(extract_text_from_block, search_text, go_to_index 등)은
          문서 내 특정 영역의 텍스트 추출 및 위치 이동을 담당한다.
    
    Example:
        >>> exam_info = extract_exam_sheet_info("C:/path/to/exam_sheet.hwpx", visible=False)
        >>> for question in exam_info:
        ...     print(question['order_number'], question['multi_or_essay'], question['number'])
    """
    hwp = None
    
    # hwp = Hwp()
    try:
        pythoncom.CoInitialize() # 한글 프로세스 초기화
        # hwp_file_path = "G:\공유 드라이브\Workspace\omr_exam 테스트용.hwpx" 
        # visible = True
        # hwp = Hwp()
        hwp = Hwp(visible=visible)
        hwp.Open(hwp_file_path)
        hwp.Run("MoveDocBegin")
        
        passage_num = 0
        order_num = 0
        multi_num = 0
        essay_num = 0
        question_dict_list = []
        
        while search_text(hwp, "#"):
            question_dict = {}
            passage_num += 1
            
            # 인덱스 텍스트 추출 및 좌표 저장
            hwp.Run("MoveSelParaEnd")
            index_text = extract_text_from_block(hwp)
            hwp.Run("CloseEx")
            hwp.Run("MoveParaEnd")
            index_end_coordinate = hwp.GetPos() # 좌표
            
            # question_type_list 추출 (콤마(,)기준)
            type_texts = index_text.split(",")
            question_type_list = extract_detail_type(type_texts)
                
            # passage 출처 추출
            source = extract_source_from_index_text(index_text)
            
            # 더블/싱글 문제 처리
            question_count = 2 if "##" in index_text else 1
            for i in range(question_count):
                # 문단번호로 이동
                go_to_index(hwp)
                start_coor = hwp.GetPos()
                
                # HEADSTRING 추출 후 논술/객관식 판단
                headstring = hwp.GetHeadingString()
                if "논술" in headstring:
                    multi_or_essay = "논술형"
                    essay_num += 1
                    number = essay_num
                else:
                    multi_or_essay = "객관식"
                    multi_num += 1
                    number = multi_num

                hwp.Run("MoveSelParaEnd")
                question_text = extract_text_from_block(hwp)
                
                # score
                search_text_condition(hwp, r"{\d점}|{\d\.\d점}")
                score_text = extract_text_from_block(hwp)
                score = extract_number_from_text(score_text)
                
                
                # answer
                if multi_or_essay == "객관식":
                    # answer(객관식)
                    hwp.Run("MoveParaBegin")
                    hwp.Run("MoveSelParaEnd")
                    enter_note(hwp)
                    search_text(hwp, "*")
                    hwp.Run("MoveSelParaEnd")
                    answer_text = extract_text_from_block(hwp)
                    answer_num = convert_circled_number(answer_text)
                    hwp.Run("CloseEx")
                    hwp.Run("MoveParaEnd")
                    
                elif multi_or_essay == "논술형":
                    # answer(논술형)
                    hwp.Run("MoveDocEnd")
                    search_text(hwp, f"{headstring}_정답", direction="Backward")
                    hwp.Run("TableCellBlock")
                    hwp.Run("TableLowerCell")
                    answer_text = extract_text_from_block(hwp)
                    hwp.Run("Cancel")
                                
                order_num += 1
                question_dict.update({
                    'order_number': order_num,
                    'multi_or_essay': multi_or_essay,
                    'number': number,
                    'detail_type': question_type_list[i],
                    'question_text': question_text,
                    'answer': answer_text,
                    'score': score,
                })
                question_dict_list.append(question_dict)
                
                hwp.SetPos(*start_coor)
                hwp.Run("MoveParaEnd")        
            hwp.SetPos(*index_end_coordinate)
        pprint(question_dict_list,sort_dicts=False)
        
    except Exception as e:
        traceback.print_exc()
        print(f"에러 발생: {e}")
        raise
    
    finally:
        HwpProcessManager.safe_hwp_quit(hwp)

    return question_dict_list
