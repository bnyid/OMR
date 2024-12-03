import fitz  # PyMuPDF
import numpy as np
import cv2
import pandas as pd


def convert_pdf_to_image(pdf_path):
    """PDF를 -> 처리가능한 BGR 이미지로 변환"""
    try:
        # PDF 파일 열기
        pdf_document = fitz.open(pdf_path)
        # 첫 페이지 가져오기
        page = pdf_document[0]
        # 페이지를 이미지로 변환 (300dpi로 설정)
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        # numpy 배열로 변환
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        # BGR 형식으로 변환 (만약 RGBA인 경우)
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
        pdf_document.close()
        return img_array
    except Exception as e:
        print(f"PDF 변환 중 오류 발생: {e}")
        return None


def convert_marking_to_number(marking_result, read_by_column=False):
    """
    마킹 결과를 숫자 문자열로 변환하는 함수
    
    Args:
        marking_result: 마킹 결과 2D 배열(행x열)
        read_by_column: True면 열 기준으로 읽기, False면 행 기준으로 읽기
    
    Returns:
        str: 변환된 숫자 문자열 (1부터 시작)
    """
    result = []
    
    # 열 기준으로 읽기
    if read_by_column:
        for col in range(marking_result.shape[1]):
            for row in range(marking_result.shape[0]):
                if marking_result[row][col] == 1:
                    result.append(str(row + 1))  # 1을 더해서 1부터 시작하도록 수정
                    break
            else:
                result.append('X')
                
    # 행 기준으로 읽기
    else:        
        for row in range(marking_result.shape[0]):
            for col in range(marking_result.shape[1]):
                if marking_result[row][col] == 1:
                    result.append(str(col + 1))  # 1을 더해서 1부터 시작하도록 수정
                    break
            else:
                result.append('X')  # 마킹이 없는 경우
    return ''.join(result)


def convert_marking_to_hangul(marking_result, read_by_column=True):
    """
    마킹 결과를 한글로 변환하는 함수
    
    Args:
        marking_result: 마킹 결과 2D 배열(행x열)
        read_by_column: True면 열 기준으로 읽기, False면 행 기준으로 읽기
    
    Returns:    
        str: 변환된 한글 문자열
    """
    # 초성 리스트
    CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 
               'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    
    # 중성 리스트
    JUNGSUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 
                'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    
    # 종성 리스트
    JONGSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 
                'ㄻ', 'ㄼ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅆ',
                'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    JONGSUNG_MAPPING = {
        'ㄱ': 1, 'ㄲ': 2, 'ㄴ': 4, 'ㄶ': 6, 'ㄷ': 7, 'ㄹ': 8, 
        'ㄺ': 9, 'ㄻ': 10, 'ㄼ': 11, 'ㅀ': 15, 'ㅁ': 16, 'ㅂ': 17, 
        'ㅅ': 19, 'ㅆ': 20, 'ㅇ': 21, 'ㅈ': 22, 'ㅊ': 23, 'ㅋ': 24, 
        'ㅌ': 25, 'ㅍ': 26, 'ㅎ': 27
    }

    def compose_hangul(cho, jung, jong):
        """초성, 중성, 종성을 조합하여 한글 문자를 생성"""
        try:
            cho_idx = CHOSUNG.index(cho)
            jung_idx = JUNGSUNG.index(jung)
            jong_idx = JONGSUNG_MAPPING[jong] if jong else 0
            
            # 유니코드 한글 시작 : 0xAC00 = "가"
            # 초성 19개, 중성 21개, 종성 28개
            unicode_value = 0xAC00 + cho_idx * 21 * 28 + jung_idx * 28 + jong_idx
            return chr(unicode_value)
        except (ValueError, KeyError):
            return ''

    result = []
    current_char = {'cho': None, 'jung': None, 'jong': None}
    char_position = 0  # 0: 초성, 1: 중성, 2: 종성
    
    if read_by_column:
        for col in range(marking_result.shape[1]):
            marked_position = None
            for row in range(marking_result.shape[0]):
                if marking_result[row][col] == 1:
                    marked_position = row
                    break
            
            if marked_position is not None:
                if char_position == 0:  # 초성
                    current_char['cho'] = CHOSUNG[marked_position]
                elif char_position == 1:  # 중성
                    current_char['jung'] = JUNGSUNG[marked_position]
                else:  # 종성
                    current_char['jong'] = JONGSUNG[marked_position]
            else:
                # 마킹이 없는 경우 해당 위치는 None으로 유지
                pass
            
            char_position += 1
            
            # 한 글자가 완성되면 (초성+중성+종성)
            if char_position == 3:
                # 한글 조합
                hangul = compose_hangul(
                    current_char['cho'],
                    current_char['jung'],
                    current_char['jong']
                )
                if hangul:  # 빈 문자열이 아닌 경우에만 추가
                    result.append(hangul)
                
                # 초기화
                current_char = {'cho': None, 'jung': None, 'jong': None}
                char_position = 0
    print(result)
    return ''.join(result)



def create_student_dataframe(student_id, student_name, answers):
    """
    학생의 답안을 DataFrame으로 변환하는 함수
    
    Args:
        student_id: 학번
        student_name: 이름
        answers: 답안 문자열
        
    Returns:
        pandas.DataFrame: 각 문제별로 행이 생성된 DataFrame
    """
    data = []
    
    # 각 답안을 개별 행으로 변환
    for i, answer in enumerate(answers, start=1):
        data.append({
            '학번': student_id,
            '이름': student_name,
            '문항': i,
            '답': answer
        })
    
    # DataFrame 생성
    df = pd.DataFrame(data)
    return df


def handle_image_file(image_file):
    """
    이미지 파일을 처리하여 OpenCV 이미지로 변환하는 함수
    
    Args:
        image_file: Django의 UploadedFile 객체
        
    Returns:
        numpy.ndarray: OpenCV 이미지 객체 또는 변환 실패시 None
    """
    try:
        if image_file.name.lower().endswith('.pdf'):
            return convert_pdf_to_image(image_file)
        else:
            image_array = np.frombuffer(image_file.read(), np.uint8)
            return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"이미지 처리 중 오류 발생: {e}")
        return None



