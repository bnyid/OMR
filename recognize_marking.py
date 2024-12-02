import numpy as np
import matplotlib.pyplot as plt

def recognize_marking(marking_area_image,
                            start_point=(1, 1),
                            rows=10, cols=10,
                            cell_size=(66.5, 40),
                            first_row_height=45,
                            first_row_gap=11,
                            roi_size=(20, 25),
                            threshold=0.3,
                            show_result=False
                            ):
    """
    OMR 용지의 마킹 영역을 분석하는 함수
    
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
    """

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