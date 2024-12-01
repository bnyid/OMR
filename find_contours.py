import cv2
import numpy as np
import pandas as pd
from skew_correction import correct_skew  # correct_skew 함수가 있는 파일에서 import


def find_large_contours(image, min_area):
    # 이미지가 컬러인 경우 그레이스케일로 변환
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 이진화
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 외곽선 찾기
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 최소 면적보다 큰 외곽선만 필터링
    large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    return large_contours


if __name__ == "__main__":
    
    ############################################################ Parameters
    
    image = cv2.imread('OMR.png') 
    corrected_image = correct_skew(image)
    gray_image = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)
    min_area = 100000

    corrected_image_copy = corrected_image.copy() # 그려서 보여주는 용 복사본

    ############################################################    

    contours = find_large_contours(gray_image, min_area)
    
    color = (0,0,255) # 외곽선을 그려서 보여줄 때, 외곽선의 색깔은 빨간색으로 설정한다.

    # 모든 외곽선을 그리고 인덱스를 붙여서 각 외곽선을 확인하기
    for i, contour in enumerate(contours):
        # 외곽선 그리기
        cv2.drawContours(corrected_image_copy, [contour], -1, color, 2) # 원본 이미지의 복사본에 외곽선을 그린다.
        
        # 외곽선의 중심 좌표 계산
        M = cv2.moments(contour)
        if M['m00'] != 0:
            cX = int(M['m10'] / M['m00'])
            cY = int(M['m01'] / M['m00'])
            # 인덱스 표시
            cv2.putText(corrected_image_copy, str(i), (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 100, 255), 5) # 복사본에 인덱스를 표시한다.

    # 이미지 표시
    cv2.imshow('Contours', corrected_image_copy)
    cv2.waitKey(0)
    cv2.destroyAllWindows()