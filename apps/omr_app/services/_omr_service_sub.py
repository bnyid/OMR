# apps/omr_app/services/_omr_service_sub.py
import cv2
import numpy as np
import matplotlib.pyplot as plt
import fitz
from pdf2image import convert_from_bytes
import math

##################### STEP 1: 이미지 전처리 및 이미지 기울기 보정 #####################

def convert_to_bgr_image(image_file):
    """
    PDF 또는 이미지 파일을 OpenCV BGR 이미지로 변환하는 함수
    
    Args:
        image_file: Django의 UploadedFile 객체
        
    Returns:
        numpy.ndarray: OpenCV BGR 이미지 객체
        
    Raises:
        ValueError: 이미지 변환 실패시 발생
    """
    if image_file.name.lower().endswith('.pdf'):
        # PDF 파일 처리
        pdf_document = fitz.open(image_file)
        page = pdf_document[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        # BGR 형식으로 변환
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
        pdf_document.close()
        return img_array
    else:
        # 일반 이미지 파일 처리
        image_array = np.frombuffer(image_file.read(), np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)

def correct_skew(image, show_result=False):
    """
    이미지의 기울기를 보정하는 함수
    
    Args:
        image: 입력 이미지 (컬러 또는 그레이스케일)
        show_result: 결과를 시각화할지 여부 (기본값: False)
    Returns:
        보정된 이미지
    """
    # 그레이스케일 변환 (이미 그레이스케일이면 그대로 사용)
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # 엣지 검출 부분 개선
    edges = cv2.Canny(gray, 30, 200, apertureSize=3)
    
    # 허프 변환 매개변수 조정
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 30,
                           minLineLength=40,
                           maxLineGap=10)
    
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(x2 - x1) > abs(y2 - y1) * 0.5:
                angle = np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi
                if abs(angle) < 30:
                    angles.append(angle)
    
    result_image = image.copy()
    
    if angles:
        angles = np.array(angles)
        mean_angle = np.mean(angles)
        std_angle = np.std(angles)
        filtered_angles = angles[abs(angles - mean_angle) < 2 * std_angle]
        
        if len(filtered_angles) > 0:
            median_angle = np.median(filtered_angles)
            print(f"skew_correction_debug: 감지된 모든 각도들의 개수: {len(angles)}")
            print(f"skew_correction_debug: 필터링된 각도들의 개수: {len(filtered_angles)}")
            print(f"skew_correction_debug: 감지된 기울기: {median_angle:.2f}도")
            print(f"skew_correction_debug: 보정할 각도: {-median_angle:.2f}도")
            
            # 원본 이미지 회전
            center = (image.shape[1] // 2, image.shape[0] // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            result_image = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]),
                                    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # 결과 시각화
    if show_result:
        # 결과 이미지 표시를 위한 창 생성
        cv2.imshow('Original Image', image)
        cv2.imshow('Edge Detection', edges)
        if lines is not None:
            line_image = image.copy()
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.imshow('Detected Lines', line_image)
        cv2.imshow('Corrected Image', result_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return result_image

##################### STEP 2: 이미지에서 큰 외곽선과 그 좌표 추출 #####################

def get_coordinates_from_large_contours(gray_image, min_area, axis='x', show_result=False):
    """그레이스케일 이미지에서 지정된 최소 면적보다 큰 외곽선들을 찾아 반환합니다.
    axis 파라미터에 따라 x축, 또는 y축 기준으로 순서를 정렬합니다.

    Args:
        gray_image (numpy.ndarray): 그레이스케일로 변환된 입력 이미지
        min_area (float): 검출할 외곽선의 최소 면적 (픽셀 단위)
        axis (str): 정렬 기준 ('x' 또는 'y', 기본값: 'x')
        show_result (bool): 결과를 시각화할지 여부 (기본값: False)

    Returns:
        list 또는 None: 다음 세 가지 경우 중 하나를 반환합니다:

            1. 최소 면적 조건을 충족하는 외곽선이 검출된 경우:
                - 예시 : [array([[x1, y1], [x2, y2], ...]), array([[x3, y3], ...])]
                - 각 외곽선은 각 1개의 외곽선 도형을 나타낸다. 
                - 이는 numpy.ndarray 형태의 (N, 1, 2) 모양을 가진 좌표점들의 배열이다.
                - N은 외곽선을 구성하는 점의 개수

            2. 최소 면적 조건을 만족하는 외곽선이 없는 경우:
                - 빈 리스트 [] 반환

            3. 사용자가 컬러 이미지를 인자로 넣은 경우:
                - None 반환 

    Note:
        입력 이미지는 반드시 그레이스케일(회색변환)이어야 합니다.
        Otsu 이진화 방법(=이미지를 흰색(255)과 검은색(0)으로만 바꿈)을 사용하여 이미지를 이진화한 후 외곽선을 검출합니다.
    """

    # 이미지가 컬러인 경우 에러 메시지 출력 후 종료
    if len(gray_image.shape) == 3:
        print("find_large_contours 함수는 그레이스케일로 변환된 이미지를 인자로 넣어야 합니다")
        return None
    
    _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU) # thresh란 이진화 처리된 이미지를 말함
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) # 모든 외곽선 찾기
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area] # 최소 면적보다 큰 외곽선만 필터링

    # 정렬: axis='x'면 x좌표 기준, axis='y'면 y좌표 기준 (두 번째 기준은 반대축)
    if filtered_contours:
        if axis == 'x':
            # x먼저, x가 같으면 y
            sorted_contours = sorted(
                filtered_contours,
                key=lambda c: (
                    cv2.boundingRect(c)[0],  # x
                    cv2.boundingRect(c)[1]   # y
                )
            )
        else:  # axis == 'y'
            # y먼저, y가 같으면 x
            sorted_contours = sorted(
                filtered_contours,
                key=lambda c: (
                    cv2.boundingRect(c)[1],  # y
                    cv2.boundingRect(c)[0]   # x
                )
            )
        filtered_contours = sorted_contours

    if show_result and filtered_contours:
        # 원본 컬러 이미지 가져오기 (그레이스케일을 3채널로 변환)
        display_image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
        color = (0, 0, 255)  # 빨간색

        # 외곽선 그리기 및 인덱스 표시
        for i, contour in enumerate(filtered_contours):
            cv2.drawContours(display_image, [contour], -1, color, 2)
            
            # 외곽선의 중심 좌표 계산
            M = cv2.moments(contour)
            if M['m00'] != 0:
                cX = int(M['m10'] / M['m00'])
                cY = int(M['m01'] / M['m00'])
                cv2.putText(display_image, str(i), (cX, cY), 
                          cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 0, 0), 4)     # 3=폰트크기, 4=폰트두께

        # 이미지 크기 조절
        height, width = display_image.shape[:2]
        resized_image = cv2.resize(display_image, (width//2, height//2))  # 50% 크기로 조절
        
        # 결과 표시
        cv2.imshow('Contours', resized_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # contours 개수 검증
    if len(filtered_contours) < 5:  # 필요한 최소 contour 개수를 5개로 수정
        raise ValueError(f"필요한 영역을 찾을 수 없습니다. (발견된 영역: {len(filtered_contours)}개, 필요한 영역: 5개)")
    
    return filtered_contours

##################### STEP 3: 외곽선 좌표대로 영역 추출 #####################

def get_omr_area_image(contour, gray_image, show_result=False):
    """contour 좌표에 해당하는 영역만 잘라서 반환합니다.
    
    Parameters
    ----------
    contour : numpy.ndarray
        추출하고자 하는 영역의 테두리 좌표
    gray_image : numpy.ndarray
        처리할 그레이스케일 이미지
    show_result : bool, optional
        잘라낸 이미지를 화면에 표시할지 여부 (기본값: False)

    Returns
    -------
    numpy.ndarray
        contour 영역만큼 잘라낸 이미지
    """
    # contour의 경계 사각형 좌표 구하기
    x, y, w, h = cv2.boundingRect(contour) # contour 좌표를 완전히 감싸는 최소 크기의 직사각형(바운딩 박스)을 찾아 좌상단의 x좌표,y좌표, 너비, 높이를 반환함
    cropped_image = gray_image[y:y+h, x:x+w] # 그레이스케일 이미지에서 좌상단 좌표(x,y)와 너비, 높이(w,h)를 기준으로 영역을 잘라냄
    
    if show_result:
        cv2.imshow('Cropped Image', cropped_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return cropped_image

##################### STEP 4: 외곽선에서 마킹 영역만 추출 #####################

def extract_marking_area(omr_area, 
                         skip_x=(True, 80, 300000, 40000), # (스킵여부, 시작x좌표, 1차임계값(상), 2차임계값(하))
                         skip_y=(True, 190, 40000, 15000),  # (스킵여부, 시작y좌표, 1차임계값(상), 2차임계값(하))
                         show_result=False,
                         ):
    """주어진 OMR 이미지에서 순수 마킹 영역만 추출
    
    Parameters
    ----------
    omr_area : numpy.ndarray
        처리할 OMR 이미지
    skip_x : tuple, optional
        (스킵여부(bool), 시작x좌표(int), 임계값(int))로 구성된 튜플
        (기본값: (True, 80, 300000))
    skip_y : tuple, optional
        (스킵여부(bool), 시작y좌표(int), 임계값(int))로 구성된 튜플
        (기본값: (True, 190, 60000))
    show_result : bool, optional
        결과 시각화 여부 (기본값: False)
    """
    # 테두리 제외
    vertical_margin = 10
    horizontal_margin = 3
    inner_area = omr_area[vertical_margin:-vertical_margin, horizontal_margin:-horizontal_margin]
    
    # 수직 프로젝션 계산 및 start_x 찾기
    vertical_proj = np.sum(255-inner_area, axis=0)
    check_interval_x = 20     # 다음 피크를 체크할 간격
    
    # skip_x 파라미터 분해
    do_skip_x, skip_initial_x, vertical_threshold, secondary_threshold_x = skip_x
    
    # x축 스킵이 활성화된 경우에만 처리
    if do_skip_x:
        start_x = skip_initial_x
        while start_x < len(vertical_proj) - check_interval_x:
            val = vertical_proj[start_x]
            if val > vertical_threshold:
                # 다음 interval 구간에 더 큰 피크가 없으면 1차 임계값 충족
                next_section = vertical_proj[start_x+1:start_x+1 + check_interval_x]
                if np.max(next_section) < vertical_threshold:
                    # 1차 임계값 충족한 뒤, 2차 임계값 이하로 내려갈 떄까지 start_x 증가
                    while start_x < len(vertical_proj) and vertical_proj[start_x] > secondary_threshold_x:
                        start_x += 1
                    break
            start_x += 1
        inner_area = inner_area[:, start_x:]
    
    # 수평 프로젝션 계산
    horizontal_proj = np.sum(255-inner_area, axis=1)
    check_interval = 20
    
    # skip_y 파라미터 분해
    do_skip_y, skip_initial_y, horizontal_threshold, secondary_threshold_y = skip_y
    
    # y축 스킵이 활성화된 경우에만 처리
    if do_skip_y:
        start_y = skip_initial_y
        while start_y < len(horizontal_proj) - check_interval:
            val = horizontal_proj[start_y]
            if val > horizontal_threshold:
                next_section = horizontal_proj[start_y+1:start_y+1 + check_interval]
                if np.max(next_section) < horizontal_threshold:
                    # 1차 임계값 충족한 뒤, 2차 임계값 이하로 내려갈 떄까지 start_y 증가
                    while start_y < len(horizontal_proj) and horizontal_proj[start_y] > secondary_threshold_y:
                        start_y += 1
                    break
            start_y += 1
        marking_area = inner_area[start_y:, :]
    else:
        marking_area = inner_area
    
    # 시각화 추가
    if show_result:
        plt.figure(figsize=(10.5, 8.4))
        
        # 원본 이미지 표시
        plt.subplot(2, 2, 1)
        plt.imshow(omr_area, cmap='gray')
        plt.title('Original OMR Area')
        
        # inner_area 표시 (x축 잘린 부분 표시)
        plt.subplot(2, 2, 2)
        plt.imshow(inner_area, cmap='gray')
        plt.title('Inner Area')
        
        if do_skip_y:
            plt.subplot(2, 2, 3)
            plt.plot(horizontal_proj)
            plt.axhline(y=horizontal_threshold, color='r', linestyle='--', label='Threshold')
            plt.axvline(x=start_y, color='g', linestyle='--', label='Start Point')
            plt.title('Horizontal Projection')
            plt.legend()
        
        if do_skip_x:
            plt.subplot(2, 3, 5)
            plt.plot(vertical_proj)
            plt.axhline(y=vertical_threshold, color='r', linestyle='--', label='Threshold')
            plt.axvline(x=start_x, color='g', linestyle='--', label='Start Point')
            plt.title('Vertical Projection')
            plt.legend()
        
        # 최종 마킹 영역
        plt.subplot(2, 2, 4)
        plt.imshow(marking_area, cmap='gray')
        plt.title('Extracted Marking Area')
        
        plt.tight_layout()
        plt.show()
    
    return marking_area

##################### STEP 5: grid 설정으로 마킹 값을 인식 #####################

def analyze_omr_grid(marking_area_image,
                            start_point=(1, 1),
                            rows=10, cols=10,
                            cell_size=(66.5, 40),
                            first_row_height=None,
                            first_row_gap=0,
                            roi_size=(20, 25),
                            threshold=0.3,
                            show_result=False
                            ):
    """ OMR 용지의 마킹 영역을 분석하는 함수
    
    Parameters:
    - marking_area_image: Input image (예: 스캔된 OMR 이미지)
    - start_point: 셀 영역의 시작점 좌표 (y, x) - 기본값 (1, 1)
    - rows, cols: 행과 열의 수 - 기본값 각각 10
    - cell_size: 각 셀의 크기 (높이, 너비) - 기본값 (66.5, 40) 픽셀
    
    - first_row_height: 첫 번째 행의 높이 - 기본값 45 픽셀
    - first_row_gap: 첫 번째 행과 두 번째 행 사이의 간격 - 기본값 11 픽셀
    
    - roi_size: ROI 영역의 고정 크기 (높이, 너비) - 기본값 (20, 25) 픽셀
    - threshold: 마킹으로 인식할 검은 픽셀 비율의 임계값 - 기본값 0.35
    - show_result: 분석 결과를 시각화할지 여부 (기본값: False)
    
    Returns:
    --------
    numpy.ndarray
        마킹 결과를 나타내는 2차원 배열 (rows x cols)
        - 마킹된 셀: 1
        - 마킹되지 않은 셀: 0
        
    예시:
    -----
    >>> image = cv2.imread('omr_sample.jpg', cv2.IMREAD_GRAYSCALE)
    >>> result = recognize_marking(image, rows=5, cols=4)
    >>> print(result)
    array([[1, 0, 0, 0],
           [0, 1, 0, 0],
           [0, 0, 1, 0],
           [0, 0, 0, 1],
           [1, 0, 0, 0]])
    
    Notes:
    ------
    - 반환되는 배열의 shape는 (rows, cols)입니다.
    - show_result=True로 설정하면 마킹 영역 분석 결과를 시각화하여 보여줍니다.
    - threshold 값을 조절하여 마킹 인식의 민감도를 조정할 수 있습니다.
    """
    
    if first_row_height is None:
        first_row_height = cell_size[0]

    # 시작점 좌표를 정수로 변환
    # map(함수, 반복가능객체) : 반복가능객체의 각 요소에 함수를 적용하여, 새로운 반복가능객체를 map객체로 반환
    start_y, start_x = map(int, start_point) 
    cell_height, cell_width = cell_size
    
    # 마킹 결과를 저장할 2차원 배열 초기화 (zeros메서드는 모든 요소가 0인 배열을 반환함)
    # 즉, 아래 코드는 모든 요소가 int(0)인 {rows}x{cols}의 2차원 배열을 반환함
    marking_result = np.zeros((rows, cols), dtype=int)
    
    for row in range(rows):
        for col in range(cols):
            # 첫 번째 행은 특별한 처리가 필요함
            if row == 0:
                y_start = start_y  # 첫 번째 행의 시작 y좌표
                current_height = first_row_height  # 첫 번째 행의 높이
            else:
                # 두 번째 행부터의 y좌표 계산
                # 예: 첫 행(45px) + 간격(11px) + (현재행-1) * 일반높이(66.5px)
                y_start = int(start_y + first_row_height + first_row_gap + (row - 1) * cell_height)
                current_height = int(cell_height)
            
            # x 좌표 계산 (각 열마다 cell_width만큼 이동)
            x_start = int(start_x + (col * cell_width))
            
            # ROI 영역을 셀의 중앙에 위치시키기
            roi_height, roi_width = roi_size
            roi_y_start = int(y_start + (current_height - roi_height) / 2)
            roi_y_end = roi_y_start + roi_height
            roi_x_start = int(x_start + (cell_width - roi_width) / 2)
            roi_x_end = roi_x_start + roi_width
            
            # ROI 영역의 이미지 추출
            # 이미지에다가 [y_start:y_end, x_start:x_end] 슬라이싱을 하면, 
            # 좌측상단이 (y_start, x_start)이고, 우측하단이 (y_end, x_end)인 직사각형 영역이 추출됨
            roi = marking_area_image[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
            
            
            # np.sum(roi == 0) : roi 배열에서 값이 0인 요소의 개수를 반환함
            # roi.size : roi 배열의 전체 요소 개수를 반환함 
            # 따라서, black_pixel_ratio는 roi 그림에서 검은색 픽셀(값=0)인 픽셀의 비율을 계산함.
            black_pixel_ratio = np.sum(roi == 0) / roi.size
            
            # threshold 파라미터 사용
            is_marked = black_pixel_ratio > threshold
            
            # 마킹된 경우 결과 배열에 1로 표시
            if is_marked:
                marking_result[row][col] = 1
    
    # 시각화 해서 이미지를 보고싶을 경우.
    if show_result:
        plt.figure(figsize=(13, 8)) #시각화 이미지 크기 설정 (y,x)
        
        # 원본 이미지와 ROI 표시
        plt.subplot(1, 2, 1)
        plt.imshow(marking_area_image, cmap='gray')
        plt.title('Original with Fixed ROI Areas')
        
        # 격자 라인과 ROI 영역 표시
        for row in range(rows):
            for col in range(cols):
                # ROI 영역 좌표 계산 (기존 코드와 동일한 방식)
                if row == 0:
                    y_start = start_y
                    current_height = first_row_height
                else:
                    y_start = int(start_y + first_row_height + first_row_gap + (row - 1) * cell_height)
                    current_height = int(cell_height)
                
                x_start = int(start_x + (col * cell_width))
                
                # ROI 영역을 셀의 중앙에 위치시키기
                roi_height, roi_width = roi_size
                roi_y_start = int(y_start + (current_height - roi_height) / 2)
                roi_y_end = roi_y_start + roi_height
                roi_x_start = int(x_start + (cell_width - roi_width) / 2)
                roi_x_end = roi_x_start + roi_width
                
                # ROI 영역을 빨간색 사각형으로 표시
                plt.plot([roi_x_start, roi_x_end, roi_x_end, roi_x_start, roi_x_start],
                        [roi_y_start, roi_y_start, roi_y_end, roi_y_end, roi_y_start],
                        'r-', linewidth=1)
                
                # 전체 셀 영역을 파란색 사각형으로 표시
                plt.plot([x_start, x_start + cell_width, x_start + cell_width, x_start, x_start],
                        [y_start, y_start, y_start + current_height, y_start + current_height, y_start],
                        'b-', linewidth=0.5)
        
        # 분석 결과 표시
        plt.subplot(1, 2, 2)
        plt.imshow(marking_result, cmap='binary')
        plt.title('Marking Analysis Result')
        plt.grid(True)
        
        plt.tight_layout()
        plt.show()
    
    return marking_result

##################### STEP 6: 마킹결과 array를 숫자, 한글로 변환 #####################

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
                    result.append(str(row))  # 열 기준의 경우 0부터 시작하므로 그대로 추가
                    break
            else:
                result.append('X')
                
    # 행 기준으로 읽기
    else:        
        for row in range(marking_result.shape[0]):
            for col in range(marking_result.shape[1]):
                if marking_result[row][col] == 1:
                    result.append(str(col + 1))  # 행 기준의 경우 1부터 시작하므로 1을 더하여 추가
                    break
            else:
                result.append('X')  # 마킹이 없는 경우
    print(f"\n최종 변환 결과: {result}")
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
    JONGSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 
                'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    JONGSUNG_MAPPING = {
        'ㄱ': 1, 'ㄲ': 2, 'ㄴ': 4, 'ㄷ': 7, 'ㄸ': 0, 'ㄹ': 8, 'ㅁ': 16, 'ㅂ': 17, 'ㅃ': 0, 'ㅅ': 19,
        'ㅆ': 20, 'ㅇ': 21, 'ㅈ': 22, 'ㅉ': 0, 'ㅊ': 23, 'ㅋ': 24, 'ㅌ': 25, 'ㅍ': 26, 'ㅎ': 27}

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






####### 새롭게 추진중 #########

import cv2
import numpy as np

def order_points(pts):
    """
    4개의 점을 [좌상, 우상, 좌하, 우하] 순서로 정렬
    """
    pts = np.array(pts, dtype="float32")
    x_sorted = pts[np.argsort(pts[:, 0]), :]
    left_two = x_sorted[:2]
    right_two = x_sorted[2:]

    # 왼쪽 두 점 중 y가 작은게 top, 큰게 bottom
    left_top = left_two[np.argsort(left_two[:,1])[0]]
    left_bottom = left_two[np.argsort(left_two[:,1])[1]]

    # 오른쪽 두 점 중 y가 작은게 top, 큰게 bottom
    right_top = right_two[np.argsort(right_two[:,1])[0]]
    right_bottom = right_two[np.argsort(right_two[:,1])[1]]

    # 순서: 좌상, 우상, 좌하, 우하
    ordered = np.array([left_top, right_top, left_bottom, right_bottom], dtype="float32")
    return ordered


def extract_line_markers(contours, offset_y=0, show_result=False, draw_image=None, color=(0,255,0)):
    """
    공통 마커 추출 함수 예시:
    - 사각형 형태를 가지며 일정 면적 이상인 컨투어만 마커로 간주
    - 마커 중심점 추출
    - show_result=True일 경우, draw_image 위에 검출된 마커 표시
    """
    markers = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 50:  # 최소 면적 조건 (필요시 조정)
            continue

        x,y,w,h = cv2.boundingRect(cnt)
        aspect_ratio = w/h if h!=0 else 9999
        # 사각형 마커 조건: aspect ratio가 대략 0.5~2 사이
        if 0.4 < aspect_ratio < 0.8:
            cx = x + w/2
            cy = y + h/2
            markers.append((cx, cy + offset_y))
            if show_result and draw_image is not None:
                # 마커 위치 표시
                cv2.rectangle(draw_image, (x, y+offset_y), (x+w, y+h+offset_y), color, 2)
                cv2.circle(draw_image, (int(cx), int(cy+offset_y)), 5, (0,0,255), -1)
    return markers


def find_reference_markers_in_region(binary_image, region_box, offset_y=0, show_result=False, draw_image=None, color=(0,255,0)):
    """
    지정한 영역(region_box=(y_start, y_end, x_start, x_end))에서
    마커를 찾아내는 함수 예시.
    """
    y_start, y_end, x_start, x_end = region_box
    region = binary_image[y_start:y_end, x_start:x_end]
    contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    markers = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 50:
            continue
        x,y,w,h = cv2.boundingRect(cnt)
        aspect_ratio = w/h if h!=0 else 9999
        if 0.5 < aspect_ratio < 2:
            cx = x + w/2 + x_start
            cy = y + h/2 + y_start + offset_y
            markers.append((cx,cy))
            if show_result and draw_image is not None:
                cv2.rectangle(draw_image, (x_start+x, y_start+y+offset_y), (x_start+x+w, y_start+y+h+offset_y), color, 2)
                cv2.circle(draw_image, (int(cx), int(cy)), 5, (255,0,255), -1)
    return markers



def find_markers_for_omr(gray_image, min_area=800, show_result=False):
    """
    OMR 용지를 기준으로 상단/하단에 있는 검은 마커를 찾는 예시 함수.
    상단/하단 5% 영역만 잘라 사용.
    """
    height, width = gray_image.shape

    # 이진화
    _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    if show_result:
        cv2.namedWindow("binarized_image", cv2.WINDOW_NORMAL) 
        cv2.resizeWindow("binarized_image", 800, 600)
        cv2.imshow("binarized_image", thresh)
        cv2.waitKey(0)

    # 상단, 하단 영역 슬라이싱 (5%)
    top_cut = 0.10
    bottom_cut = 0.90
    top_region = thresh[0:int(height*top_cut), :]
    bottom_region = thresh[int(height*bottom_cut):, :]

    if show_result:
        cv2.namedWindow(f"top_region_{top_cut*100}%", cv2.WINDOW_NORMAL)
        cv2.resizeWindow(f"top_region_{top_cut*100}%", 800, 200)
        cv2.imshow(f"top_region_{top_cut*100}%", top_region)

        cv2.namedWindow(f"bottom_region_{(1-bottom_cut)*100}%", cv2.WINDOW_NORMAL)
        cv2.resizeWindow(f"bottom_region_{(1-bottom_cut)*100}%", 800, 200)
        cv2.imshow(f"bottom_region_{(1-bottom_cut)*100}%", bottom_region)
        cv2.waitKey(0)

    # 상단/하단 컨투어 추출
    top_contours, _ = cv2.findContours(top_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bottom_contours, _ = cv2.findContours(bottom_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = min_area  # (예) 최소 면적 픽셀값. 적절히 조정
    top_contours = [cnt for cnt in top_contours if cv2.contourArea(cnt) >= min_area]
    bottom_contours = [cnt for cnt in bottom_contours if cv2.contourArea(cnt) >= min_area]
    
    
    # 시각화용 이미지 복사
    draw_image = None
    if show_result:
        draw_image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
         # (추가) min_area 기준 사각형 그려주기
        #   - 면적 = min_area → 대략 정사각형으로 가정해서 변의 길이를 sqrt(min_area)로 계산.
        side = int(math.sqrt(min_area))
        # 화면 왼쪽 상단(10,10) 위치에, side x side 크기의 사각형을 겹쳐 그려줌
        cv2.rectangle(
            draw_image, 
            (10, 10), 
            (10 + side, 10 + side), 
            color=(0, 255, 0), 
            thickness=2
        )
    # 상단/하단 마커 포인트
    top_points = extract_line_markers(top_contours, offset_y=0, show_result=show_result, draw_image=draw_image)
    bottom_points = extract_line_markers(bottom_contours, offset_y=int(height*bottom_cut), show_result=show_result, draw_image=draw_image, color=(255,0,0))

    # 우측 하단 3개의 사각형 활용:
    # 우측 하단 20%*5% 영역에서 마커를 찾아 최대 x좌표를 기준점으로 활용
    right_region_box = (int(height*0.8), height, int(width*0.95), width)  # 하단 20%, 우측 5%
    right_markers = find_reference_markers_in_region(
        thresh, right_region_box,
        offset_y=0, show_result=show_result, draw_image=draw_image, color=(0,255,255)
    )

    # right_markers 중 최대 x좌표를 찾는다.
    if right_markers:
        max_right_x = max(m[0] for m in right_markers)
    else:
        max_right_x = width  # 만약 찾지 못하면 제한하지 않음

    # 마커 충분성 검증
    if len(top_points) < 2 or len(bottom_points) < 2:
        if show_result and draw_image is not None:
            cv2.destroyAllWindows()
            cv2.namedWindow("Markers Detected", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Markers Detected", 800, 600)
            cv2.imshow("Markers Detected", draw_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        raise ValueError("충분한 마커를 찾지 못했습니다. 상단/하단 마커 부족.")

    # 가장 왼쪽 / 오른쪽 마커 선택
    top_left = min(top_points, key=lambda p: p[0])
    top_right = max(top_points, key=lambda p: p[0])
    bottom_left = min(bottom_points, key=lambda p: p[0])
    bottom_right = max(bottom_points, key=lambda p: p[0])

    # 우측 제한을 적용하여 top_right, bottom_right 보정
    # top_right와 bottom_right의 x좌표가 max_right_x보다 크면 max_right_x로 제한
    def adjust_point_x(pt, max_x):
        if pt[0] > max_x:
            return (max_x, pt[1])
        return pt

    top_right = adjust_point_x(top_right, max_right_x)
    bottom_right = adjust_point_x(bottom_right, max_right_x)

    src_points = np.array([top_left, top_right, bottom_left, bottom_right], dtype="float32")
    src_points = order_points(src_points)

    if show_result and draw_image is not None:
        # 기준점 표시
        for i, pt in enumerate(src_points):
            cv2.circle(draw_image, (int(pt[0]), int(pt[1])), 15, (255,0,0), -1) # 20 = 반지름
            cv2.putText(draw_image, f"P{i+1}", (int(pt[0])+5,int(pt[1])+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 5) # 3 = 폰트 크기, 2 = 폰트 두께
        
        cv2.destroyAllWindows()
        cv2.namedWindow("Markers Detected", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Markers Detected", 800, 600)
        cv2.imshow("Markers Detected", draw_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return src_points


def warp_to_standard_view(image, src_points, target_size=(2800, 2000), show_result=False):
    """
    Perspective Transform 적용 - 가로 2800, 세로2000으로 픽셀 고정
    
    Args:
        image: 입력 이미지
        src_points: 변환할 4개의 좌표점
        target_size: 목표 크기 (너비, 높이) - 기본값: (2800, 2000)
        show_result: 결과 시각화 여부
    
    Returns:
        warped: 변환된 이미지
    """
    target_width, target_height = target_size
    
    # 목표 좌표 설정
    dst_points = np.array([
        [0, 0],
        [target_width-1, 0],
        [0, target_height-1],
        [target_width-1, target_height-1]
    ], dtype="float32")

    # 변환 행렬 계산 및 적용
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    warped = cv2.warpPerspective(image, M, (target_width, target_height))

    if show_result:
        cv2.namedWindow("Warped OMR", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Warped OMR", 800, 600)
        cv2.imshow("Warped OMR", warped)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return warped








############# 뒷면


def split_backside_into_equal_regions(
    image,
    top_margin=0,
    bottom_margin=0,
    left_margin=0,
    right_margin=0,
    num_segments=5,
    show_result=False
):
    """
    뒤쪽(OMR 뒷면) 이미지를 세로방향으로 num_segments등분해서 잘라내는 함수.
    - 상·하·좌·우 margin 픽셀만큼 잘라내고 남은 영역을 동일한 세로비율로 분할
    - 컬러/그레이 모두 처리 가능

    Parameters
    ----------
    image : numpy.ndarray
        원본 이미지(컬러 or 그레이)
    top_margin : int
        위쪽을 잘라낼 픽셀 수
    bottom_margin : int
        아래쪽을 잘라낼 픽셀 수
    left_margin : int
        왼쪽을 잘라낼 픽셀 수
    right_margin : int
        오른쪽을 잘라낼 픽셀 수
    num_segments : int
        세로를 몇 등분할지 (기본 5)
    show_result : bool
        True면 시각화하여 확인 (디버깅용)

    Returns
    -------
    list of numpy.ndarray
        세로로 나눈 영역들이 순서대로 저장된 리스트
    """

    # 1) 이미지 크기
    h, w = image.shape[:2]  # 그레이든 컬러든 [:2]는 height, width
    # 2) margin 만큼 잘라내기 (클리핑)
    #    주의: bottom_margin이 있으면 아래쪽 h - bottom_margin
    #         right_margin이 있으면 w - right_margin
    #    잘라낸 결과를 new_img에 저장
    new_img = image[
        top_margin : h - bottom_margin,
        left_margin : w - right_margin
    ].copy()

    # 3) 세로 높이, 가로 폭
    clipped_h, clipped_w = new_img.shape[:2]

    # 4) 세로 방향으로 num_segments 등분
    segment_height = clipped_h / num_segments  # float
    #    정수로 변환할지 여부는 선택
    #    만약 애매한 소수가 나올 수 있으면, int로 변환해서 마지막 부분은 약간 짤릴 수도 있음
    #    우선 float로 두고 범위 슬라이싱 시 int() 캐스팅
    regions = []
    for i in range(num_segments):
        y_start = int(i * segment_height)
        y_end   = int((i + 1) * segment_height)

        cropped = new_img[y_start : y_end, 0 : clipped_w].copy()
        regions.append(cropped)

    # 5) show_result 시각화
    if show_result:
        display_img = new_img.copy()
        # 직선(가로줄)로 분할 위치 표시
        for i in range(1, num_segments):
            y_line = int(i * segment_height)
            cv2.line(display_img, (0, y_line), (clipped_w, y_line), (0,0,255), 3)

        # 창 크기 조절을 위한 설정 추가
        cv2.namedWindow("Backside-Split", cv2.WINDOW_NORMAL)
        h, w = display_img.shape[:2]
        cv2.resizeWindow("Backside-Split", w//2, h//2)  # 너비와 높이를 절반으로

        # 창에 표시
        cv2.imshow("Backside-Split", display_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return regions