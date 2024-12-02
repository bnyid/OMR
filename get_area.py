import cv2
import numpy as np
from find_contours import find_large_contours
from skew_correction import correct_skew
import matplotlib.pyplot as plt

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
