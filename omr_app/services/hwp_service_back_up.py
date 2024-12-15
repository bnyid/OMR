import re
from pyhwpx import Hwp


# 스타일 찾기
def search_style(style_number):
    hwp.SetMessageBoxMode(0x00020000) # 계속 찾으시겠습니까? No
    hwp.HAction.GetDefault("Goto", hwp.HParameterSet.HGotoE.HSet)
    hwp.HParameterSet.HGotoE.HSet.SetItem("DialogResult", style_number)
    hwp.HParameterSet.HGotoE.SetSelectionIndex = 4
    if hwp.HAction.Execute("Goto", hwp.HParameterSet.HGotoE.HSet):
        hwp.Run("MoveParaEnd")
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기
        return True
    else:
        hwp.Run("MoveParaEnd")
        hwp.SetMessageBoxMode(0x000F0000) # 기본값으로 돌리기
        return False

# 블록 텍스트 추출
def extract_text_from_block():  # 이 함수명을 영어로 바꾸면 = extract_text_from_block
    hwp.InitScan(range=0xff)  # 0xff <<선택된 범위 내에서 검색
    _, text_blokced = hwp.GetText()  # 텍스트만 추출
    hwp.ReleaseScan() # 스캔을 해제.
    print(f"text_blokced: {text_blokced}")
    return text_blokced # 이경우, 해당 target이 text에 포함되어있으면 True, 아니면 False를 반환.

# 텍스트 검색
def search_text(text,direction="Forward"):
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

def is_text_in_block(text): 
    hwp.InitScan(range=0xff)  # 0xff <<선택된 범위 내에서 검색
    _, text_blokced = hwp.GetText()  # 텍스트만 추출
    hwp.ReleaseScan() # 스캔을 해제.
    return f"{text}" in text_blokced # 이경우, 해당 target이 text에 포함되어있으면 True, 아니면 False를 반환.

    
# 텍스트 검색(조건식 사용)
def search_text_condition(text): 
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


def go_to_faster_word(word1, word2): 
    hwp.SetMessageBoxMode(0x20000) # 예/아니오 중에 아니오를 누름
    start_pos = hwp.GetPos()

    result1 = search_text(word1)
    hwp.Cancel()
    pos1 = hwp.GetPos() if result1 else None
        
    hwp.SetPos(*start_pos)
    
    result2 = search_text(word2)
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


def extract_source_text(text):
    pattern = re.compile(r"(고\d+ \d+년 \d+월 \d+번)")
    match = pattern.search(text)
    if match:
        source_text = match.group(1)  # 첫 번째 그룹(괄호 안)에 해당하는 문자열
        return source_text
    return None





def type_text(text):
    hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
    hwp.HParameterSet.HInsertText.Text = text
    hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)



# 해당 행의 미주에 진입
def enter_note():
    hwp.Run("MoveParaBegin")
    hwp.SelectCtrlFront()
    hwp.Run("MoveRight")
    hwp.FindCtrl()
    hwp.HAction.Run("NoteModify")
    
    
def go_to_index():
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
    



###### 문항 채점 과정
# (1) 객관식 문단번호 스타일을 찾아가 원문 출처, 총 문항 수, 배점, 정답 번호를 구하고 문항 번호를 부여한다.
# (2) 주관식 문단번호 스타일을 찾아 발문, 배점을 구하고 발문 좌표 저장
# (3) 발문에서 GetHEadString()으로 논술형 번호 추출 -> 문서 끝으로 이동한 뒤 논술형 번호로 "위로 찾기"
# (4) 논술형 정답을 추출하고 다시 발문 좌표로 이동


if __name__ == "__main__":
    hwp = Hwp()

    q_multiple_data_list_1 = []
    q_essay_data_list_1 = []


    ## 객관식 문항 추출 (세부 유형을 제외하고 추출)
    # hwp = Hwp()
    hwp.Run("MoveDocBegin")
    i=0
    while go_to_index():
        # 발문(question_stem) 추출 및 좌표 저장
        hwp.Run("MoveParaBegin")
        hwp.Run("MoveSelParaEnd")
        question_text = extract_text_from_block()
        question_text_coordinate = hwp.GetPos()
        
        
        search_text_condition(r"{\d점}|{\d\.\d점}")
        score_text = extract_text_from_block()
        score = extract_number_from_text(score_text)
        print(f"배점 추출 완료")
        
        
        head = hwp.GetHeadingString()
        #정답 추출_논술형인 경우
        if "논술" in head:
            hwp.Run("MoveDocEnd")
            search_text(f"{head}",direction="Backward")
            hwp.Run("MoveParaEnd")
            answer_start_coordinate = hwp.GetPos()
            
            go_to_faster_word("논술형", "객관식")
            hwp.Run("MoveParaBegin")
            answer_end_coordinate = hwp.GetPos()
            
            hwp.SetPos(*answer_start_coordinate)
            hwp.Select()
            hwp.SetPos(*answer_end_coordinate)
            answer_text = extract_text_from_block()
            hwp.Cancel()
            print(f"{head} 정답 추출 완료")
            hwp.SetPos(*question_text_coordinate)
            
            q_dict_essay = {
                'number': f"{head}",
                'question_text': question_text,
                'answer': answer_text,
                'score': score
            }
            
            q_essay_data_list_1.append(q_dict_essay)
            
        #정답 추출_객관식인 경우
        else:
            i += 1
            # 미주 진입
            hwp.Run("MoveParaBegin")
            hwp.Run("MoveSelParaEnd")
            enter_note()
            
            # 정답 추출
            search_text("*")
            hwp.Run("MoveSelParaEnd")
            answer_circled = extract_text_from_block()
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

            explanation_text = extract_text_from_block()
            
            question_dict = {
                'number': i,
                'question_text': question_text,
                'answer': answer_num,
                'explanation': explanation_text,
                'score': score
            }
            q_multiple_data_list_1.append(question_dict)

            # 미주 종료
            hwp.Run("CloseEx")
            
        # 문단끝으로 이동(다음 검색 준비)
        hwp.Run("Cancel")
        hwp.Run("MoveParaEnd")
        
    print(len(q_multiple_data_list_1))
    print(len(q_essay_data_list_1))

    detail_type_keywords = ['어법','어휘', '일치', '순서', '삽입', '제목', '주제', '요약', '빈칸', '함축', '영영풀이']            
    essay_type_keywords = ['논술형(어법)', '논술형(요약)', '논술형(영작)'] # 추후 수정 필요

    ################## 세부유형 추출 및 문제 출처 추출 ##################

    q_multiple_data_list_2 = []
    q_essay_data_list_2 = []

    hwp.Run("MoveDocBegin")
    while search_text("#"):
        # 블록 설정 후 index_text 저장
        hwp.Run("MoveParaBegin")
        hwp.Run("MoveSelParaEnd")
        index_text = extract_text_from_block()
        source_text = extract_source_text(index_text)
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
                        q_essay_data_list_2.append(q_type_dict_essay)
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
                        q_multiple_data_list_2.append(q_type_dict) 
                        break

        
        
        hwp.Run("MoveParaEnd")
        
    if len(q_multiple_data_list_2) != len(q_multiple_data_list_1):
        raise ValueError("객관식 세부유형이 모두 추출되지 않았습니다.")
        
    if len(q_essay_data_list_2) != len(q_essay_data_list_1):
        raise ValueError("논술형 세부유형이 모두 추출되지 않았습니다.")


    # 객관식 최종 리스트 생성
    q_multiple_final_list = []
    for (dict_1, dict_2) in zip(q_multiple_data_list_1, q_multiple_data_list_2):
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


    # 주관식 최종 리스트 생성
    q_essay_final_list = []
    for (dict_1, dict_2) in zip(q_essay_data_list_1, q_essay_data_list_2):
        q_essay_final_dict = {
            'number': dict_1.get('number'),
            'question_text': dict_1.get('question_text'),
            'answer': dict_1.get('answer'),
            'score': dict_1.get('score'),
            'source': dict_2.get('source'),
            'detail_type': dict_2.get('detail_type')
        }
        q_essay_final_list.append(q_essay_final_dict)


    ###################### 결과 확인 ######################
    print("q_multiple_final_list:")
    for item in q_multiple_final_list:
        for key, value in item.items():
            print(f"{key}: {value}")
        print("###")  # 각 item 사이에 빈 줄

    print("q_essay_final_list:")
    for item in q_essay_final_list:
        for key, value in item.items():
            print(f"{key}: {value}")
        print("###")  # 각 item 사이에 빈 줄