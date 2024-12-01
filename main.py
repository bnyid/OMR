import cv2
import numpy as np
import pandas as pd
from find_contours import find_large_contours
from get_omr_area_image import get_omr_area_image, extract_marking_area
from skew_correction import correct_skew
from analyze_id_marking import analyze_fixed_id_marking, visualize_fixed_marking_analysis


image = cv2.imread('OMR.png') # 이미지 로드
corrected_image = correct_skew(image)  # 기울임 보정
gray_image = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)  # 이미지를 그레이 스케일로(회색으로) 변환
contours = find_large_contours(gray_image, 100000)  # 보정된 회색 이미지와 설정된 최소 면적(100000)을 기준으로 주요 외곽선 추출


# 외곽선을 영역별로 매칭
id_contour = contours[0]      # 학번 영역
name_contour = contours[1]    # 이름 영역
answer_contours = contours[2:]  # 답안표시영역1, 2, 5

#학번 영역 처리
id_area = get_omr_area_image(id_contour, gray_image, show_result=False) # OMR 카드에서 해당 외곽선에 해당하는 영역만 이미지로 추출하는 함수
id_marking_area = extract_marking_area(id_area, show_result=False) # 순수 ��킹 영역만 추출하는 함수

# 학번 마킹 분석
start_point = (1, 1)  # 시작 좌표 (y, x)
cell_size = (66.5, 40)  # 기본 셀의 크기 (height, width)
first_row_height = 45  # 첫 번째 행의 높이
first_row_gap = 13     # 첫 번째 행과 두 번째 행 사이의 여백
first_row_margin = 0.35  # 첫 번째 행의 ROI 마진
other_rows_margin = 0.35  # 나머지 행의 ROI 마진 (더 큰 값 = 더 작은 검사 영역)

visualize_fixed_marking_analysis(
    id_marking_area, 
    start_point=start_point,
    cell_size=cell_size,
    first_row_height=first_row_height,
    first_row_gap=first_row_gap,
    rows=10, 
    cols=10,
    first_row_margin=first_row_margin,
    other_rows_margin=other_rows_margin
)

id_marking_result = analyze_fixed_id_marking(
    id_marking_area,
    start_point=start_point,
    cell_size=cell_size,
    first_row_height=first_row_height,
    first_row_gap=first_row_gap,
    rows=10,
    cols=10
)





