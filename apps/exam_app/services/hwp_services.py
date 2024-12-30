# hwp_service_upgrade.py
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

####################################################

def extract_exam_sheet_data(hwp_file_path,visible=True):
    """
    한글(HWP) 문서를 분석하여 시험지 정보를 추출하는 함수.
    
    주어진 한글 파일(hwp_file_path)을 열어 텍스트, 표, 보기(객관식), 논술형 답안 등의 정보를
    구조화된 형태의 리스트로 반환한다. 이 함수는 다음과 같은 구조를 가진 JSON 유사 파이썬 객체를 반환한다.

    Returns:
        list of dict: passage_dict_list

    반환되는 전체 구조(passsage_dict_list)는 다음과 같다:
    ``` 
    [
        {
            "passage_number": int,           # 지문 번호(1부터 시작)
            "passage_serial": str or None,   # 지문 일련번호 예: "A1", "B20322" / 없을 경우 None
            "passage_source": str or None,   # 지문 출처 문자열, 없으면 None
            "is_double_question": bool,      # 더블(2문항)인지 싱글(1문항)인지 표시
            "is_registered": bool,       # 문제 등록 제외 여부
            "passage_text": str,             # 추출된 지문 본문 텍스트 (HTML, 표도 포함)
            
            "question_list": [
                {
                    # 공통 필드
                    "order_number": int,                 # 정렬 번호
                    "is_essay": bool,                    # True면 논술형 문제, False면 객관식 문제
                    "question_number": int,               # OMR 채점 시 사용되는 문제 식별용 번호
                    "question_type": str or None,        # 문제 유형 정보 (e.g. '주제', '어법')
                    "question_text": str,                # 문제 발문 텍스트 (non-HTML)
                    "question_text_extra": str or None,  # 발문 텍스트 이후 추가 텍스트,표 등 (HTML)
                    "score": float or int or None,       # 문제 배점(숫자), 없으면 None
                    "answer": list of int or str or None,  # 객관식의 경우 [2], [3], ..., 주관식인 경우 str
                    
                    # 객관식 전용 필드 (is_essay=False 인 경우)
                    "choice_list": [
                        {
                            "choice_number": int,     # 보기 번호(1~5)
                            "choice_text": str        # 보기 텍스트(HTML 형태)
                        },
                        ...
                    ],
                    "explanation": str or None,       # 해설 텍스트
                       
                    # 논술형 전용 필드 (is_essay=True)
                    "answer_format": str or None,     # 논술형 답안 형식 관련 텍스트(HTML)
                },
            ]
        },
    ]

    즉, 최상위 반환 값은 'passage_dict_list'이며, 이 리스트는 여러 개의 'passage_dict'를 담는다.
    이를 통해 프론트엔드나 다른 로직에서 지문, 문제, 보기, 정답, 해설 등의 정보에 손쉽게 접근 가능하다.
    """
    hwp = None
    
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
        passage_dict_list = []
        
        while search_text(hwp, "#"):
            passage_num += 1
            passage_dict = {}

            is_double_question = None
            
            # 인덱스 텍스트 추출 및 좌표 저장
            hwp.Run("MoveSelParaEnd")
            index_text = extract_text_from_block(hwp)
            hwp.Run("CloseEx")
            hwp.Run("MoveParaEnd")
            index_end_coordinate = hwp.GetPos() # 좌표
            
            # is_registered
            is_registered = not ("$" in index_text)

            # question_type_list 추출 (콤마(,)기준)
            type_texts = index_text.split(",")
            question_type_list = extract_detail_type(type_texts)

            # passage 일련번호가 있는 경우 추출
            index_text_split = index_text.split("]")
            passage_serial = index_text_split[0].split("[")[1] if len(index_text_split) > 1 else None
                
                
            # passage 출처 추출
            source = extract_source_from_index_text(index_text)

            
            # 더블/싱글 유형판단
            is_double_question = True if "##" in index_text else False
            
            passage_dict.update({
                'passage_number': passage_num,
                'passage_serial': passage_serial,
                'passage_source': source,
                'is_double_question': is_double_question,
                'is_registered': is_registered
            })
            
            question_dict_list = []
            # double passage인 경우 passage_text 좌표 추출
            if is_double_question:
                search_text(hwp, "]")
                hwp.Run("MoveParaEnd")
                search_text(hwp, "*")
                hwp.Run("MoveLeft")
                hwp.Run("MoveRight")
                passage_start_coor = hwp.GetPos()
                
                go_to_index(hwp)
                hwp.Run("MovePrevParaEnd")
                passage_end_coor = hwp.GetPos()
            # Single passage인 경우 passage_text 좌표 추출
            else:
                go_to_index(hwp)
                hwp.Run("MoveParaEnd")
                search_text(hwp, "*")
                hwp.Run("MoveLeft")
                hwp.Run("MoveRight")
                passage_start_coor = hwp.GetPos()
                
                if "논술" in index_text:
                    search_text(hwp, "[*답안]")
                    hwp.Run("MoveLeft")
                    hwp.Run("MoveRight")
                    passage_end_coor = hwp.GetPos()
                
                else:
                    search_circled_number(hwp, 1)
                    hwp.Run("MoveLeft")
                    hwp.Run("MoveRight")
                    hwp.Run("MovePrevParaEnd")
                    passage_end_coor = hwp.GetPos()
            
                
            # passage_text
            hwp.SetPos(*passage_start_coor)
            hwp.Select()
            hwp.SetPos(*passage_end_coor)
            passage_text = extract_html_text_from_block(hwp)                    
            passage_dict['passage_text'] = passage_text
            
            # 인덱스 텍스트 끝으로 이동
            hwp.Cancel()
            hwp.SetPos(*index_end_coordinate)
        
            # is_double_question이 True이면 2회 반복, False이면 1회 반복
            question_count = 2 if is_double_question else 1
            question_dict_list = []
            for i in range(question_count): 
                question_dict = {}
                order_num += 1
                
                # 샾(#)의 갯수와 comma(,)의 갯수 오류를 확인, question_type 추출
                try:
                    question_type = question_type_list[i] 
                except IndexError:
                    error_msg = "오류 : 파일의 #의 갯수 또는 comma(,)의 갯수가 맞는지 점검하세요."
                    print(error_msg)
                    question_type = None
                    raise ValueError(error_msg)

                # question_text
                go_to_index(hwp) # 발문으로 이동
                hwp.Run("MoveSelParaEnd")
                question_text = extract_text_from_block(hwp)
                
                # headstring & is_essay
                headstring = hwp.GetHeadingString()
                is_essay = True if "논술" in headstring else False

                # score
                search_text_condition(hwp, r"{\d점}|{\d\.\d점}")
                score_text = extract_text_from_block(hwp)
                score = extract_number_from_text(score_text)
                
                
                # 객관식/논술형 공통 필드 업데이트
                question_dict.update({
                    'order_number': order_num,
                    'question_type': question_type,
                    'is_essay': is_essay,
                    'score': score,
                    'question_text': question_text,
                })
                
                # 발문 끝점 좌표 저장
                hwp.Run("MoveParaEnd")
                question_text_end_coor = hwp.GetPos()
                                
                # 객관식 : answer, explanation, question_text_extra, choice_list
                if not is_essay:
                    multi_num +=1
                    question_dict.update({
                        'question_number': multi_num
                    })
                    
                    hwp.SetPos(*question_text_end_coor)
                    hwp.Run("MoveParaBegin")
                    hwp.Run("MoveSelParaEnd")
                    
                    # answer
                    enter_note(hwp)
                    search_text(hwp, "*")
                    hwp.Run("MoveSelParaEnd")
                    answer_text = extract_text_from_block(hwp)
                    answer_num = convert_circled_number(answer_text)
                    hwp.Run("MoveRight")
                    hwp.Run("MoveLeft")
                    
                                        
                    # explanation
                    hwp.Run("Select")
                    while True:
                        place_1 = hwp.GetPos()
                        para_num = place_1[1]
                        hwp.Run("MoveNextParaBegin")
                        place_2 = hwp.GetPos()
                        if para_num == place_2[1]:
                            break

                    explanation_text = extract_html_text_from_block(hwp)
                    
                    hwp.Run("CloseEx")
                    hwp.Run("MoveParaEnd")
                    
                    # 보기 또는 답안 시작점 좌표 저장
                    search_circled_number(hwp, 1)
                    hwp.Run("MoveLeft")
                    hwp.Run("MoveRight")
                    choice_start_coor = hwp.GetPos()

                    
                    # 발문과 보기 사이 범위 블럭
                    hwp.SetPos(*question_text_end_coor)
                    hwp.Select()
                    hwp.SetPos(*choice_start_coor)
                    
                    # question_text_extra
                    question_text_extra = ""
                    if has_content_in_block(hwp):
                        question_text_extra = extract_html_text_from_block(hwp)
                        
                    question_dict.update({
                        'question_text_extra': question_text_extra
                    })

                    # choice_list
                    hwp.Cancel()
                    hwp.SetPos(*choice_start_coor)
                    choice_list = []
                    for choice_number in range(1,6):
                        search_circled_number(hwp, choice_number)
                        hwp.Run("MoveRight")
                        choice_num_coor = hwp.GetPos()
                        
                        if choice_number < 5:
                            search_circled_number(hwp, choice_number+1)
                            search_text(hwp, "*",direction="Backward")
                            hwp.Run("MoveRight")
                            hwp.Run("MoveLeft")
                            

                        elif choice_number == 5:
                            if go_to_faster_question(hwp, "#"):
                                search_text(hwp, "*",direction="Backward")
                                hwp.Run("MoveRight")
                                hwp.Run("MoveLeft")
                                
                            else:
                                search_text(hwp, "확인사항")
                                hwp.Run("CloseEx")
                                hwp.Run("CloseEx")
                                hwp.Run("MoveLeft")
                                hwp.Run("MoveLeft")
                                search_text(hwp, "*",direction="Backward")
                                hwp.Run("MoveRight")
                                hwp.Run("MoveLeft")
                                
                        choice_num_plus_coor = hwp.GetPos()
                        
                        hwp.SetPos(*choice_num_coor)
                        hwp.Select()
                        hwp.SetPos(*choice_num_plus_coor)
                        choice_text = extract_html_text_from_block(hwp)
                        hwp.Cancel()
                        
                        
                        choice_dict = {
                            'choice_number': choice_number,
                            'choice_text': choice_text
                        }
                        
                        choice_list.append(choice_dict)
                        
                    question_dict.update({
                        'choice_list': choice_list
                    })
                    # question_text(발문으로) 이동
                    hwp.Cancel()

                    question_dict_list.append(question_dict)
                    
                # 논술형 : answer, answer_format, question_text_extra
                elif is_essay:
                    essay_num = extract_number_from_text(headstring)
                    question_dict.update({
                        'question_number': essay_num
                    })
                    
                    # 답안 작성 시작점 좌표 저장
                    if search_text(hwp, "*답안"):
                        hwp.Run("MoveLeft")
                        hwp.Run("MoveRight")
                    else:
                        raise Exception(f"주관식 {essay_num}번 이후로 [답안] 문자를 확인하세요.")
                    
                    answer_format_start_coor = hwp.GetPos()
                    
                    # question_table 있는지 확인
                    hwp.SetPos(*question_text_end_coor)
                    hwp.Select()
                    hwp.SetPos(*answer_format_start_coor)
                    
                    question_text_extra = ""
                    if has_content_in_block(hwp):
                        question_text_extra = extract_html_text_from_block(hwp)
                        
                    question_dict.update({
                        'question_text_extra': question_text_extra
                    })
                    
                    # 답안 format 끝점 추출
                    if go_to_faster_question(hwp, "#"):
                        search_text(hwp, "*",direction="Backward")
                        hwp.Run("MoveRight")
                        hwp.Run("MoveLeft")
                        answer_format_end_coor = hwp.GetPos()
                    elif search_text(hwp, "확인사항"):
                        hwp.Run("CloseEx")
                        hwp.Run("MoveLeft")
                        search_text(hwp, "*",direction="Backward")
                        hwp.Run("MoveRight")
                        hwp.Run("MoveLeft")
                        answer_format_end_coor = hwp.GetPos()
                    else:
                        raise Exception(f"주관식 {essay_num}번 이후로, 다음 문제 '#'이 없거나 문제 끝에 '확인사항' 문자를 찾지 못해 주관식 답안 작성란의 끝을 찾지 못했습니다.")
                    
                    
                    hwp.SetPos(*answer_format_start_coor)
                    hwp.Select()
                    hwp.SetPos(*answer_format_end_coor)

                    # answer_format
                    answer_format = extract_html_text_from_block(hwp)
                    hwp.Cancel()
                    
                    # 답안 추출
                    hwp.Run("MoveDocEnd")
                    search_text(hwp, headstring, direction="Backward")
                    hwp.Run("MoveNextParaBegin")
                    answer_start_coor = hwp.GetPos()
                    
                    go_to_faster_word(hwp, "[논술","<객관")
                    search_text(hwp, "*",direction="Backward")
                    hwp.Run("MoveRight")
                    hwp.Run("MoveLeft")
                    answer_end_coor = hwp.GetPos()
                    
                    hwp.SetPos(*answer_start_coor)
                    hwp.Select()
                    hwp.SetPos(*answer_end_coor)
                    
                    answer_text = extract_html_text_from_block(hwp)
                    hwp.Cancel()

                    question_dict.update({
                        'answer_format': answer_format,
                        'answer': answer_text,
                        'question_text_extra': question_text_extra
                    })
                    
                    question_dict_list.append(question_dict)
                    
                    hwp.SetPos(*question_text_end_coor)
                    

                hwp.Cancel()
            
            passage_dict.update({
                'question_list': question_dict_list
            })
                
            passage_dict_list.append(passage_dict)
            
        pprint(passage_dict_list)
    except Exception as e:
        traceback.print_exc()
        print(f"에러 발생: {e}")
        raise
    
    finally:
        HwpProcessManager.safe_hwp_quit(hwp)

    return passage_dict_list