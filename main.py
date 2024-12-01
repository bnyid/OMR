import cv2
import numpy as np
import pandas as pd
from find_contours import find_large_contours
from get_omr_area_image import get_omr_area_image, extract_marking_area
from skew_correction import correct_skew


image = cv2.imread('OMR.png') # 이미지 로드
corrected_image = correct_skew(image)  # 기울임 보정
gray_image = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)  # 이미지를 그레이 스케일로(회색으로) 변환
contours = find_large_contours(gray_image, 100000)  # 보정된 회색 이미지와 설정된 최소 면적(100000)을 기준으로 주요 외곽선 추출


# 외곽선을 영역별로 매칭
id_contour = contours[0]      # 학번 영역
name_contour = contours[1]    # 이름 영역
answer_contours = contours[2:]  # 답안표시영역1, 2, 3

#학번 영역 처리
id_area = get_omr_area_image(id_contour, gray_image, show_result=False) # OMR 카드에서 해당 외곽선에 해당하는 영역만 이미지로 추출하는 함수
id_marking_area = extract_marking_area(id_area,show_result=True) # 순수 마킹 영역만 추출하는 함수



