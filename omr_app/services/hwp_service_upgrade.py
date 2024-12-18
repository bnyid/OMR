# hwp_service.py
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

def go_to_index(hwp):
    hwp.SetMessageBoxMode(0x00020000) # 계속 찾으시겠습니까? No
    hwp.HAction.GetDefault("Goto", hwp.HParameterSet.HGotoE.HSet)
    hwp.HParameterSet.HGotoE.HSet.SetItem("DialogResult", 34)
    hwp.HParameterSet.HGotoE.SetSelectionIndex = 5
    if hwp.HAction.Execute("Goto", hwp.HParameterSet.HGotoE.HSet):
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기
        return True
    else:
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기
        return False
    
    
### 각종 extract 함수들

def extract_text_from_block_lines(hwp):  
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
    hwp.InitScan(range=0xff)  # 0xff <<선택된 범위 내에서 검색
    _, text_blokced = hwp.GetText()  # 텍스트만 추출
    hwp.ReleaseScan() # 스캔을 해제.
    print(f"text_blokced: {text_blokced}")
    return text_blokced # 이경우, 해당 target이 text에 포함되어있으면 True, 아니면 False를 반환.


def search_text_condition(hwp, text): 
    """조건식사용에 체크하고 텍스트 검색

	Args:
		text (_type_): _description_
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


def extract_number_from_text(text):
    """
    텍스트에서 숫자(정수 또는 소수)를 추출하는 함수
    
    Args:
        text (str): 숫자가 포함된 텍스트
        
    Returns:
        float: 추출된 숫자. 숫자가 없으면 None 반환
    """
    import re
    
    number_match = re.search(r'(\d+\.?\d*)', text)
    if number_match:
        return float(number_match.group(1))
    return None


# 텍스트 검색
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
    특정 숫자에 해당하는 모든 원문자를 검색하는 함수
    
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
    
    result = hwp.HAction.Execute("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    hwp.SetMessageBoxMode(0x000F0000)  # 기본값으로 돌리기
    
    return result
    
    
    
def go_to_table(hwp):
    hwp.HAction.GetDefault("Goto", hwp.HParameterSet.HGotoE.HSet);
    hwp.HParameterSet.HGotoE.HSet.SetItem("DialogResult", 55);
    hwp.HParameterSet.HGotoE.SetSelectionIndex = 5;
    return hwp.HAction.Execute("Goto", hwp.HParameterSet.HGotoE.HSet)


def go_to_faster_question(hwp,word):
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
    hwp.SetMessageBoxMode(0x20000) # 예/아니오 중에 아니오를 누름
    start_pos = hwp.GetPos()

    result1 = search_text(hwp,word1)
    hwp.Cancel()
    pos1 = hwp.GetPos() if result1 else None
        
    hwp.SetPos(*start_pos)
    
    result2 = search_text(hwp,word2)
    hwp.Cancel()
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


# 커서 행의 미주에 진입
def enter_note(hwp):
    hwp.Run("MoveParaBegin")
    hwp.SelectCtrlFront()
    hwp.Run("MoveRight")
    hwp.FindCtrl()
    return hwp.HAction.Run("NoteModify")


# 텍스트에서 입력된 원문자들을 인식해 일반 숫자 리스트로 변환
def convert_circled_number(text):
    """
    인자로 받은 텍스트의 원문자들을 인식해 일반 숫자 리스트로 변환
    
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
    # '#' 제거
    text = index_text.lstrip('#').strip()
    
    # 일련번호가 있는 경우 처리
    if text.startswith('['):
        text = text.split(']', 1)[1].strip()
    
    # '-' 를 기준으로 분리하여 앞부분(source) 추출
    source = text.split('-')[0].strip()
    
    return source


''' 정규식 용으로 남겨두었음
def extract_source_text(hwp, text):
    pattern = re.compile(r"(고\d+ \d+년 \d+월 \d+번)")
    match = pattern.search(text)
    if match:
        source_text = match.group(1)  # 첫 번째 그룹(괄호 안)에 해당하는 문자열
        return source_text
    return None
'''



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


####################################################

def extract_basic_data(hwp):
    q_multiple_data_list = []
    q_essay_data_list = []

    ## 객관식 문항 추출 (세부 유형을 제외하고 추출)
    hwp.Run("MoveDocBegin")
    i=0
    print("디버깅 포인트1")
    while go_to_index(hwp):
        print("디버깅 포인트2")
        # 발문(question_stem) 추출 및 좌표 저장
        hwp.Run("MoveParaBegin")
        hwp.Run("MoveSelParaEnd")
        question_text = extract_text_from_block(hwp)

        question_text_coordinate = hwp.GetPos()
        
        
        search_text_condition(hwp, r"{\d점}|{\d\.\d점}")
        score_text = extract_text_from_block(hwp)
        score = extract_number_from_text(score_text)
        print(f"배점 추출 완료")
        
        
        head = hwp.GetHeadingString()
        #정답 추출_논술형인 경우
        if "논술" in head:
            hwp.Run("MoveDocEnd")
            search_text(hwp, f"{head}",direction="Backward")
            hwp.Run("MoveParaEnd")
            answer_start_coordinate = hwp.GetPos()
                
            go_to_faster_word(hwp, "논술형", "객관식")
            hwp.Run("MoveParaBegin")
            answer_end_coordinate = hwp.GetPos()
            
            hwp.SetPos(*answer_start_coordinate)
            hwp.Select()
            hwp.SetPos(*answer_end_coordinate)
            answer_text = extract_text_from_block(hwp)
            hwp.Cancel()
            print(f"{head} 정답 추출 완료")
            hwp.SetPos(*question_text_coordinate)
            
            q_dict_essay = {
                'number': f"{head}",
                'question_text': question_text,
                'answer': answer_text,
                'score': score
            }
            
            q_essay_data_list.append(q_dict_essay)
            
        #정답 추출_객관식인 경우
        else:
            i += 1
            # 미주 진입
            hwp.Run("MoveParaBegin")
            hwp.Run("MoveSelParaEnd")
            enter_note(hwp)
            
            # 정답 추출
            search_text(hwp, "*")
            hwp.Run("MoveSelParaEnd")
            answer_circled = extract_text_from_block(hwp)
            answer_num = convert_circled_number(answer_circled)

            # 해설 추출
            hwp.Run("MoveRight")
            hwp.Run("MoveLeft")
            
            hwp.Run("Select")
            while True:
                place_1 = hwp.GetPos()
                para_num = place_1[1]
                hwp.Run("MoveNextParaBegin")
                place_2 = hwp.GetPos()
                if para_num == place_2[1]:
                    break

            explanation_text = extract_text_from_block_lines(hwp)
            
            question_dict = {
                'number': i,
                'question_text': question_text,
                'answer': answer_num,
                'explanation': explanation_text,
                'score': score
            }
            q_multiple_data_list.append(question_dict)

            # 미주 종료
            hwp.Run("CloseEx")
            
        # 문단끝으로 이동(다음 검색 준비)
        hwp.Run("Cancel")
        hwp.Run("MoveParaEnd")
        
    return q_multiple_data_list, q_essay_data_list



def extract_type_and_source_data(hwp):
    
    detail_type_keywords = ['어법','어휘', '일치', '순서', '삽입', '제목', '주제', '요약', '빈칸', '함축', '영영풀이']            
    essay_type_keywords = ['논술형(어법)', '논술형(요약)', '논술형(영작)'] # 추후 수정 필요

    ################## 세부유형 추출 및 문제 출처 추출 ##################

    q_multiple_data_list = []
    q_essay_data_list = []

    hwp.Run("MoveDocBegin")
    while search_text(hwp,"#"):
        # 블록 설정 후 index_text 저장
        hwp.Run("MoveParaBegin")
        hwp.Run("MoveSelParaEnd")
        index_text = extract_text_from_block(hwp)

        # 일련번호 저장
        serial_number = index_text.split("]")
        if len(serial_number) > 1:
            serial_number = serial_number[0].lstrip("[")  # '[' 제거
        else:
            serial_number = None
        
        source_text = extract_source_from_index_text(index_text)
        type_texts = index_text.split(",") # type 두개를 리스트로 저장 -> 반복문 돌릴 예정
        print(type_texts)
        # type_text = type_texts
        
        # 각 type_text에 대해 반복
        for type_text in type_texts:
            # 문제가 논술형이라면
            if "논술" in type_text:
                detail_type = None
                for keyword in essay_type_keywords:
                    if keyword in type_text:
                        detail_type = keyword
                        q_type_dict_essay = {
                            'detail_type': detail_type,
                            'source': source_text
                        }
                        q_essay_data_list.append(q_type_dict_essay)
                        break

            # 문제가 객관식이라면
            else:
                detail_type = None
                for keyword in detail_type_keywords:
                    if keyword in type_text:
                        detail_type = keyword
                        q_type_dict = {
                            'source': source_text,
                            'detail_type': detail_type,
                        }
                        q_multiple_data_list.append(q_type_dict) 
                        break
        
        hwp.Run("MoveParaEnd")
        
    return {
        'multiple': q_multiple_data_list,
        'essay': q_essay_data_list
    }

def extract_question_data(hwp_file_path, visible=False):
    hwp = None
    try:
        pythoncom.CoInitialize()
        hwp = Hwp(visible=visible)
        hwp.Open(hwp_file_path)
                
        multiple_data, essay_data = extract_basic_data(hwp)
        
        # 세부 유형 및 출처 데이터 추출
        type_source_data = extract_type_and_source_data(hwp)
        
        # 최종 데이터 병합
        multiple_final = merge_multiple_choice_data(multiple_data, type_source_data['multiple'])
        essay_final = merge_essay_data(essay_data, type_source_data['essay'])
        
        return {
            'multiple_choice': multiple_final,
            'essay': essay_final
        }
        
    except Exception as e:
        print(f"에러 발생: {e}")
        raise
    
    finally:
        HwpProcessManager.safe_hwp_quit(hwp)

def extract_html_text_from_block(hwp):
    """
    블록으로 선택된 부분의 HTML 형태 서식 텍스트를 추출하는 함수.
    - 빈 문단은 건너뛰어 불필요한 <p></p> 제거
    - 문단 사이에 줄바꿈 추가
    - 결과 문자열 앞뒤의 공백 및 줄바꿈 제거
    
    Args:
        hwp: 한글 객체 (Hwp)

    Returns:
        str: 처리된 HTML 텍스트.
            각 문단은 <p>...</p> 형태로 감싸지고,
            문단 사이에 줄바꿈(\n) 추가.
            빈 문단은 제거되며,
            최종 결과 앞뒤 공백은 strip()으로 제거.
    """

    html_content = hwp.GetTextFile("HTML", "saveblock:true")
    if not html_content:
        return ""

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    body = soup.find('body')
    if not body:
        return ""

    paragraphs = body.find_all(['p', 'div'])

    result_soup = BeautifulSoup('<div></div>', 'html.parser')
    result_div = result_soup.div

    for p in paragraphs:
        # 빈 문단 건너뛰기
        if not p.get_text(strip=True):
            continue

        # span, p 태그에서 class 속성 제거
        for tag in p.find_all(['span', 'p']):
            if 'class' in tag.attrs:
                del tag['class']

        # 새로운 문단 생성
        new_p = result_soup.new_tag('p')
        new_p.append(BeautifulSoup(str(p), 'html.parser'))
        result_div.append(new_p)
        # 문단 사이 구분용 줄바꿈 추가
        result_div.append(result_soup.new_string('\n'))

    # div 제거
    result = str(result_div)[5:-6]

    # 앞뒤 공백 및 개행 제거
    result = result.strip()

    return result

def get_clean_table_html(passage_table_raw_html):
    """
    HWP에서 추출한 테이블 HTML을 입력받아,
    원문에는 없던 불필요한 줄바꿈을 모두 제거한 깔끔한 HTML을 반환한다.
    
    - 빈 <p> 태그 제거
    - 불필요한 개행, 공백 제거
    - 스타일, 폰트 등은 그대로 유지
    """
    soup = BeautifulSoup(passage_table_raw_html, 'html.parser')

    # 빈 p 태그 제거
    for p in soup.find_all('p'):
        if not p.get_text(strip=True):
            p.decompose()

    # 문자열로 변환
    passage_table_html = str(soup)

    # 불필요한 개행 및 공백 제거
    # 모든 개행 문자(\n) 및 그 주변 공백을 제거
    passage_table_html = re.sub(r'\s*\n\s*', '', passage_table_html)
    passage_table_html = passage_table_html.strip()

    return passage_table_html


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
            "passage_text": str,             # 추출된 지문 본문 텍스트 (HTML 형식)
            "passage_table": str or None,    # 지문 내 표를 HTML 형태로 추출한 문자열, 없으면 None
            
            "question_list": [
                {
                    # 공통 필드
                    "question_number": int,      # 문항 번호 (1부터 순차적으로 증가)
                    "question_type": str or None,# 문제 유형 정보 (e.g. '주제', '어법')
                    "is_essay": bool,            # True면 논술형 문제, False면 객관식 문제
                    "score": float or None,      # 문제 배점(숫자), 없으면 None
                    "question_text": str,        # 문제 발문 텍스트 (일반 텍스트)
                    "grading_number": str or int, # OMR 채점 시 사용되는 문제 식별용 번호
                    
                    # 객관식 전용 필드 (is_essay=False 인 경우)
                    "grading_number": int,        # 객관식 문제 식별용 번호(문항 순서)
                    "answer": list of int or None,# 정답(원문자 숫자), 예: [2]
                    "explanation": str or None,   # 해설 텍스트
                    "choice_list": [
                        {
                            "choice_number": int,   # 보기 번호(1~5)
                            "choice_text": str      # 보기 텍스트(HTML 형태)
                        },
                        ...
                    ],
                    "question_table": [
                        # 문제 내에 존재하는 표가 있을 경우
                        # 각 표를 HTML 문자열로 저장
                        "<table>...</table>",
                        ...
                    ] or []
                    
                    # 논술형 전용 필드 (is_essay=True 인 경우)
                    "answer_format": str or None, # 논술형 답안 형식 관련 텍스트(HTML)
                    # 위에서와 같이 question_table 필드에 표가 있을 수 있음
                    # "answer" 필드: 논술형 답안(텍스트)
                    
                },
                ...
            ]
        },
        ...
    ]
    ```

    즉, 최상위 반환 값은 'passage_dict_list'이며, 이 리스트는 여러 개의 'passage_dict'를 담는다.
    각 'passage_dict'는 한 개의 지문(passage)과 해당 지문에 연결된 문제(question_list)를 포함한다.
    
    각 passage_dict 내 필드 설명:
    - passage_number (int): 지문의 순번(1부터)
    - passage_serial (str or None): 지문 일련번호 
    - passage_source (str or None): 지문 출처에 대한 문자열
    - is_double_question (bool): 해당 지문에 연결된 문제가 2문항인지(True) 1문항인지(False)
    - passage_text (str): 지문 전체를 HTML 형태로 파싱한 텍스트
    - passage_table (str or None): 지문 내에 포함된 표를 HTML로 추출한 문자열. 없거나 표가 없으면 None
    - question_list (list): 이 지문에 연결된 문제들의 리스트. 보통 1개 또는 2개 문제.
    
    question_list 내 각 question_dict 설명:
    - question_number (int): 문제번호(전체 문서에서 누적)
    - question_type (str or None): 문제 유형(주제, 어휘, 어법 등)
    - is_essay (bool): 논술형 문제 여부
    - score (float or None): 문제 배점
    - question_text (str): 문제 발문 텍스트 (HTML 제거한 순수 텍스트)
    - grading_number (int or str): OMR 채점 시 사용되는 문제 식별용 번호
    
    - 만약 is_essay=False(객관식):
      - answer (list of int): 정답 번호. 예: [2]이면 2번이 정답
      - explanation (str or None): 해설 텍스트(줄바꿈 포함)
      - choice_list (list): 보기 목록
         각 보기(dict):
           - choice_number (int): 보기 번호(1~5)
           - choice_text (str): 보기 텍스트 (HTML 포함)
      - question_table (list): 문제 내에 포함된 표(들). 각 표는 HTML 문자열.
      
    - 만약 is_essay=True(논술형):
      - grading_number (str or int): 논술형 문제 식별용 정보
      - answer_format (str or None): 논술형 문제의 답안 형식 관련 텍스트(HTML)
      - answer (str): 논술형 문제의 답안 내용(HTML)
      - question_table (list): 마찬가지로 문제 내 표들(HTML로 추출)

    최종적으로 이 함수는 문서를 모두 분석한 뒤, 'passage_dict_list'를 반환한다.
    이를 통해 프론트엔드나 다른 로직에서 지문, 문제, 보기, 정답, 해설 등의 정보에 손쉽게 접근 가능하다.
    """
    hwp = None
    
    try:
        pythoncom.CoInitialize()
        print("===== DEBUG: Before creating hwp instance =====")

        print("Type of hwp:", type(Hwp))
        hwp = Hwp(visible=visible)
        
        print("===== DEBUG: After creating hwp instance =====")
        hwp.Open(hwp_file_path)
        hwp.Run("MoveDocBegin")
        
        passage_num = 0
        question_num = 0
        multi_num = 0
        passage_dict_list = []
        
        while search_text(hwp, "#"):
            passage_num += 1
            
            is_double_question = None
            passage_dict = {}
            
            # 인덱스 텍스트 추출 및 좌표 저장
            hwp.Run("MoveSelParaEnd")
            index_text = extract_text_from_block(hwp)
            hwp.Run("CloseEx")
            hwp.Run("MoveParaEnd")
            index_end_coordinate = hwp.GetPos() # 좌표

            
            # 세부 유형 미리 추출
            detail_type_keywords = ['어법','어휘', '일치', '순서', '삽입', '제목', '주제', '요약', '빈칸', '함축', '영영풀이']            
            essay_type_keywords = ['논술형(어법)', '논술형(요약)', '논술형(영작)'] # 추후 수정 필요

            type_texts = index_text.split(",")        
            question_type_list = []
            for type_text in type_texts:
                # type_text = type_texts[0]
                detail_type = None
                # 논술형 먼저 파악
                for keyword in essay_type_keywords:
                    if keyword in type_text:
                        detail_type = keyword
                        break
                if detail_type is None:
                    for keyword in detail_type_keywords:
                        if keyword in type_text:
                            detail_type = keyword
                            break
                question_type_list.append(detail_type)


            # 일련번호 추출
            index_text_split = index_text.split("]")
            passage_serial = index_text_split[0].split("[")[1] if len(index_text_split) > 1 else None
                
            # 출처 추출
            source = extract_source_from_index_text(index_text)

            
            # 더블/싱글 유형판단
            is_double_question = True if "##" in index_text else False
            
            passage_dict.update({
                'passage_number': passage_num,
                'passage_serial': passage_serial,
                'passage_source': source,
                'is_double_question': is_double_question,
            })
            
            question_dict_list = []
            # double passage인 경우 passage_text와 passage_table 추출
            if is_double_question:
                search_text(hwp, "]")
                hwp.Run("MoveParaEnd")
                search_text(hwp, "*")
                hwp.Run("MoveLeft")
                hwp.Run("MoveRight")
                passage_start_coor = hwp.GetPos()
                
                go_to_index(hwp)
                hwp.Run("MoveParaBegin")
                question_text_start_coor = hwp.GetPos()
                
                
                hwp.SetPos(*passage_start_coor)
                hwp.Select()
                hwp.SetPos(*question_text_start_coor)
                
                
                # passage_table이 있다면 추출
                if hwp.GetTextFile(format="HWPML2X", option="saveblock:true").count("<TABLE"):
                    go_to_table(hwp)
                    passage_end_coor = hwp.GetPos()
                    
                    # table찾아서 html 저장
                    go_to_table(hwp)
                    hwp.SelectCtrlFront()      # 표 선택
                    passage_table_raw_html = hwp.GetTextFile("HTML", "saveblock:true")
                    passage_table_clean_html = get_clean_table_html(passage_table_raw_html)
                    
                    passage_dict['passage_table'] = passage_table_clean_html
                    
                else:
                    hwp.SetPos(*question_text_start_coor)
                    search_text(hwp, "*",direction="Backward")
                    hwp.Run("MoveRight")
                    hwp.Run("MoveLeft")
                    passage_end_coor = hwp.GetPos()
                
                hwp.Cancel()
                hwp.SetPos(*passage_start_coor)
                hwp.Select()
                hwp.SetPos(*passage_end_coor)    
                passage_text = extract_html_text_from_block(hwp)
                hwp.Cancel()
                
                passage_dict['passage_text'] = passage_text
            
            # Single passage인 경우 passage_text 및 passage_table 추출
            else:
                go_to_index(hwp)
                hwp.Run("MoveParaEnd")
                search_text(hwp, "*")
                hwp.Run("MoveLeft")
                hwp.Run("MoveRight")
                passage_start_coor = hwp.GetPos()
                
                if "논술" in index_text:
                    search_text(hwp, "[답안]")
                    hwp.Run("MoveLeft")
                    hwp.Run("MoveRight")
                    end_coor = hwp.GetPos()
                
                else:
                    search_circled_number(hwp, 1)
                    hwp.Run("MoveLeft")
                    hwp.Run("MoveRight")
                    end_coor = hwp.GetPos()
                
                hwp.SetPos(*passage_start_coor)
                hwp.Select()
                hwp.SetPos(*end_coor)
                
                passage_end_coor = None
                # passage_table이 있다면 추출
                for table_index in range(hwp.GetTextFile(format="HWPML2X", option="saveblock:true").count("<TABLE")):
                    go_to_table(hwp)
                    passage_end_coor = hwp.GetPos()
                    
                    
                    # 표 html 저장
                    hwp.SelectCtrlFront()
                    passage_table_raw_html = hwp.GetTextFile("HTML", "saveblock:true")
                    passage_table_clean_html = get_clean_table_html(passage_table_raw_html)
                    passage_dict['passage_table'] = passage_table_clean_html
                    
                    hwp.Cancel()
                    hwp.Run("MoveLineEnd")

                
                if passage_end_coor is None:
                    hwp.Cancel()
                    hwp.SetPos(*end_coor)
                    search_text(hwp, "*", direction="Backward")
                    hwp.Run("MoveRight")
                    hwp.Run("MoveLeft")
                    
                    passage_end_coor = hwp.GetPos()
                        
                hwp.SetPos(*passage_start_coor)
                hwp.Select()
                hwp.SetPos(*passage_end_coor)
                    
                passage_text = extract_html_text_from_block(hwp)
                
                passage_dict['passage_text'] = passage_text
                hwp.Cancel()
            
            hwp.SetPos(*index_end_coordinate)

            # is_double_question이 True이면 2회 반복, False이면 1회 반복
            question_count = 2 if is_double_question else 1

            # question_number, question_text, score, is_essay, question_type, answer, explanation, choice_list, choice_table_list 추출
            question_dict_list = []
            for i in range(question_count):
                question_dict = {}
                question_num += 1

                go_to_index(hwp)
                hwp.Run("MoveParaBegin")
                hwp.Run("MoveSelParaEnd")

                # 발문
                question_text = extract_text_from_block(hwp)
                
                # 논술형 판단
                headstring = hwp.GetHeadingString()
                is_essay = True if "논술" in headstring else False

                # 배점
                search_text_condition(hwp, r"{\d점}|{\d\.\d점}")
                score_text = extract_text_from_block(hwp)
                score = extract_number_from_text(score_text)

                try:
                    question_type = question_type_list[i] 
                except IndexError:
                    error_msg = "오류 : 파일의 #의 갯수 또는 comma(,)의 갯수가 맞는지 점검하세요."
                    print(error_msg)
                    question_type = None
                    raise ValueError(error_msg)
                
                question_dict.update({
                    'question_number': question_num,
                    'question_type': question_type,
                    'is_essay': is_essay,
                    'score': score,
                    'question_text': question_text,
                })
                
                
                # 발문 끝점 좌표 저장
                hwp.Run("MoveParaEnd")
                question_text_end_coor = hwp.GetPos()
                                
                # 객관식인 경우 정답,해설, question_table, 보기 추출
                if not is_essay:
                    multi_num +=1
                    question_dict.update({
                        'grading_number': multi_num
                    })
                    
                    hwp.SetPos(*question_text_end_coor)
                    hwp.Run("MoveParaBegin")
                    hwp.Run("MoveSelParaEnd")
                    
                    # 정답 추출
                    enter_note(hwp)
                    search_text(hwp, "*")
                    hwp.Run("MoveSelParaEnd")
                    answer_text = extract_text_from_block(hwp)
                    answer_num = convert_circled_number(answer_text)
                    
                    # 해설 추출
                    hwp.Run("MoveRight")
                    hwp.Run("MoveLeft")
                    
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
                    if not is_essay:
                        search_circled_number(hwp, 1)
                        hwp.Run("MoveLeft")
                        hwp.Run("MoveRight")
                        choice_start_coor = hwp.GetPos()

                    
                    # 보기 추출 전 테이블이 존재할 수 있는 범위 블럭
                    hwp.SetPos(*question_text_end_coor)
                    hwp.Select()
                    hwp.SetPos(*choice_start_coor)
                    
                    # question_table이 있다면 추출
                    question_table_list = []
                    for table_index in range(hwp.GetTextFile(format="HWPML2X", option="saveblock:true").count("<TABLE")):
                        go_to_table(hwp)
                        hwp.SelectCtrlFront()
                        question_table_raw_html = hwp.GetTextFile("HTML", "saveblock:true")
                        question_table_clean_html = get_clean_table_html(question_table_raw_html)
                        question_table_list.append(question_table_clean_html)
                        hwp.Cancel()
                        hwp.Run("MoveLineEnd")
                    
                
                    # 보기 추출
                    hwp.Cancel()
                    hwp.SetPos(*choice_start_coor)
                    choice_list = []
                    for choice_number in range(1,6):
                        search_circled_number(hwp, choice_number)
                        hwp.Run("MoveLeft")
                        hwp.Run("MoveRight")
                        hwp.Run("MoveRight")
                        choice_num_coor = hwp.GetPos()
                        
                        if choice_number < 5:
                            print("choice_index",choice_number)
                            search_circled_number(hwp, choice_number+1)
                            hwp.Run("MoveLeft")
                            hwp.Run("MoveRight")
                            search_text(hwp, "*",direction="Backward")
                            hwp.Run("MoveRight")
                            hwp.Run("MoveLeft")
                            

                        else:
                            print("choice_index",choice_number)
                            if go_to_faster_question(hwp, "#"):
                                search_text(hwp, "*",direction="Backward")
                                hwp.Run("MoveRight")
                                hwp.Run("MoveLeft")
                                
                            else:
                                print("choice_number 5 진입")
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
                    hwp.SetPos(*question_text_end_coor)
                    hwp.Run("MoveParaBegin")
                    hwp.Run("MoveSelParaEnd")
                    
                    # 정답 및 해설 추출
                    if enter_note(hwp):
                        # 정답 추출
                        search_text(hwp, "*")
                        hwp.Run("MoveSelParaEnd")
                        answer_circled = extract_text_from_block(hwp)
                        answer_num = convert_circled_number(answer_circled)
                        hwp.Run("MoveRight")
                        hwp.Run("MoveLeft")
                        
                        # 해설 추출
                        hwp.Run("Select")
                        while True:
                            place_1 = hwp.GetPos()
                            para_num = place_1[1]
                            hwp.Run("MoveNextParaBegin")
                            place_2 = hwp.GetPos()
                            if para_num == place_2[1]:
                                break
                        explanation_text = extract_html_text_from_block(hwp)
                        
                        question_dict.update({
                            'answer': answer_num,
                            'explanation': explanation_text
                        })
                        hwp.Run("CloseEx")
                    hwp.Run("MoveParaEnd")

                    question_dict_list.append(question_dict)
                # 논술형의 경우 question_table, 답안format, 답안 추출
                else:
                    essay_num = headstring.replace('[','').replace(']','')
                    question_dict.update({
                        'grading_number': essay_num
                    })
                    
                    # 답안 작성 시작점 좌표 저장
                    if search_text(hwp, "*답안"):
                        hwp.Run("MoveLeft")
                        hwp.Run("MoveRight")
                    answer_format_start_coor = hwp.GetPos()
                    
                    # question_table 있는지 확인
                    hwp.SetPos(*question_text_end_coor)
                    hwp.Select()
                    hwp.SetPos(*answer_format_start_coor)
                    
                    # question_table이 있다면 추출
                    question_table_list = []
                    for table_index in range(hwp.GetTextFile(format="HWPML2X", option="saveblock:true").count("<TABLE")):
                        go_to_table(hwp)
                        hwp.SelectCtrlFront()
                        question_table_raw_html = hwp.GetTextFile("HTML", "saveblock:true")
                        question_table_clean_html = get_clean_table_html(question_table_raw_html)
                        question_table_list.append(question_table_clean_html)
                        
                        hwp.Cancel()
                        hwp.Run("CloseEx")
                        hwp.Run("MoveLineEnd")
                    
                    # 답안 format 끝점 추출
                    if go_to_faster_question(hwp, "#"):
                        search_text(hwp, "*",direction="Backward")
                        hwp.Run("MoveRight")
                        hwp.Run("MoveLeft")
                        answer_format_end_coor = hwp.GetPos()
                    
                    # 답안 format 블럭
                    if hwp.SetPos(*answer_format_start_coor):
                        hwp.Select()
                        hwp.SetPos(*answer_format_end_coor)

                    # 답안 format 추출
                    answer_format = extract_html_text_from_block(hwp)
                    hwp.Cancel()
                    
                    # 답안 추출
                    hwp.Run("MoveDocEnd")
                    search_text(hwp, headstring, direction="Backward")
                    hwp.Run("MoveNextParaBegin")
                    answer_start_coor = hwp.GetPos()
                    
                    go_to_faster_word(hwp, "[논술","<객관")
                    hwp.Run("MoveParaBegin")
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
                        'question_table': question_table_list
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
        
        