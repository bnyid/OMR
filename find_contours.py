import cv2
import numpy as np
import pandas as pd
from skew_correction import correct_skew  # correct_skew 함수가 있는 파일에서 import


def find_large_contours(gray_image, min_area, show_result=False):
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
                          cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 100, 255), 5)

        # 결과 표시
        cv2.imshow('Contours', display_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return filtered_contours