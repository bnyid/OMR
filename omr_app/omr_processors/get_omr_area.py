import cv2
import numpy as np
import matplotlib.pyplot as plt

def get_coordinates_from_large_contours(gray_image, min_area, show_result=False):
    """그레이스케일 이미지에서 지정된 최소 면적보다 큰 외곽선들을 찾아 반환합니다.
    외곽선은 왼쪽에서 오른쪽 순서로 정렬됩니다.

    Args:
        gray_image (numpy.ndarray): 그레이스케일로 변환된 입력 이미지
        min_area (float): 검출할 외곽선의 최소 면적 (픽셀 단위)
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

    # 외곽선을 x좌표 기준으로 정렬
    if filtered_contours:
        # 각 외곽선의 중심점 x좌표를 기준으로 정렬
        sorted_contours = sorted(filtered_contours, 
                               key=lambda c: cv2.moments(c)['m10']/cv2.moments(c)['m00'])
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
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 100, 255), 2)

        # 이미지 크기 조절
        height, width = display_image.shape[:2]
        resized_image = cv2.resize(display_image, (width//2, height//2))  # 50% 크기로 조절
        
        # 결과 표시
        cv2.imshow('Contours', resized_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return filtered_contours


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

def extract_marking_area(omr_area, 
                         skip_x=(True, 80, 300000),  # (스킵여부, 시작x좌표, 임계값)
                         skip_y=(True, 190, 60000),  # (스킵여부, 시작y좌표, 임계값)
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
    do_skip_x, skip_initial_x, vertical_threshold = skip_x
    
    # x축 스킵이 활성화된 경우에만 처리
    if do_skip_x:
        start_x = skip_initial_x
        while start_x < len(vertical_proj) - check_interval_x:
            if vertical_proj[start_x] > vertical_threshold:
                next_section = vertical_proj[start_x+1:start_x+1 + check_interval_x]
                if np.max(next_section) < vertical_threshold:
                    break
            start_x += 1
        print("최종 start_x: ", start_x)
        inner_area = inner_area[:, start_x:]
    
    # 수평 프로젝션 계산
    horizontal_proj = np.sum(255-inner_area, axis=1)
    check_interval = 20
    
    # skip_y 파라미터 분해
    do_skip_y, skip_initial_y, horizontal_threshold = skip_y
    
    # y축 스킵이 활성화된 경우에만 처리
    if do_skip_y:
        start_y = skip_initial_y
        while start_y < len(horizontal_proj) - check_interval:
            if horizontal_proj[start_y] > horizontal_threshold:
                next_section = horizontal_proj[start_y+1:start_y+1 + check_interval]
                if np.max(next_section) < horizontal_threshold:
                    break
            start_y += 1
        print("최종 start_y: ", start_y)
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
