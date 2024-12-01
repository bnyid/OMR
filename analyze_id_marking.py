import numpy as np
import matplotlib.pyplot as plt
import cv2

def analyze_fixed_id_marking(marking_area, start_point=(1, 1), cell_size=(66.5, 40), first_row_height=45, first_row_gap=11, rows=10, cols=10, first_row_margin=0.3, other_rows_margin=0.35):
    """ROI 마진을 첫 번째 행과 나머지 행에 대해 다르게 설정할 수 있는 마킹 분석 함수"""
    start_y, start_x = map(int, start_point)
    cell_height, cell_width = cell_size
    
    marking_result = np.zeros((rows, cols), dtype=int)
    
    for col in range(cols):
        for row in range(rows):
            # 현재 셀의 y 좌표와 ROI 마진 설정
            if row == 0:
                y_start = start_y
                current_height = first_row_height
                roi_margin = first_row_margin
            else:
                y_start = int(start_y + first_row_height + first_row_gap + (row - 1) * cell_height)
                current_height = int(cell_height)
                roi_margin = other_rows_margin
                
            x_start = int(start_x + (col * cell_width))
            
            # ROI 영역 계산 시 정수형으로 변환
            roi_y_start = int(y_start + current_height * roi_margin)
            roi_y_end = int(y_start + current_height * (1 - roi_margin))
            roi_x_start = int(x_start + cell_width * roi_margin)
            roi_x_end = int(x_start + cell_width * (1 - roi_margin))
            
            roi = marking_area[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
            
            avg_value = np.mean(roi)
            dark_pixel_ratio = np.sum(roi < 180) / roi.size
            
            is_marked = (avg_value < 180) and (dark_pixel_ratio > 0.7) # 마킹된 비율 임계치 설정 
            
            if is_marked:
                marking_result[row][col] = 1
    
    return marking_result

def visualize_fixed_marking_analysis(marking_area, start_point=(1, 1), cell_size=(66.5, 40), first_row_height=45, first_row_gap=11, rows=10, cols=10, first_row_margin=0.3, other_rows_margin=0.35):
    """ROI 마진을 첫 번째 행과 나머지 행에 대해 다르게 설정할 수 있는 시각화 함수"""
    start_y, start_x = map(int, start_point)
    cell_height, cell_width = cell_size
    
    plt.figure(figsize=(15, 10))
    
    plt.subplot(1, 2, 1)
    plt.imshow(marking_area, cmap='gray')
    plt.title('Original with Fixed ROI Areas')
    
    # 격자 라인 표시
    plt.axhline(y=start_y, color='blue', linestyle='-', alpha=0.3)
    plt.axhline(y=start_y + first_row_height, color='blue', linestyle='-', alpha=0.3)
    
    for i in range(1, rows + 1):
        y = start_y + first_row_height + first_row_gap + (i - 1) * cell_height
        plt.axhline(y=y, color='blue', linestyle='-', alpha=0.3)
    
    for i in range(cols + 1):
        plt.axvline(x=start_x + i * cell_width, color='blue', linestyle='-', alpha=0.3)
    
    # ROI 영역 표시
    for col in range(cols):
        for row in range(rows):
            if row == 0:
                y_start = start_y
                current_height = first_row_height
                roi_margin = first_row_margin
            else:
                y_start = int(start_y + first_row_height + first_row_gap + (row - 1) * cell_height)
                current_height = int(cell_height)
                roi_margin = other_rows_margin
                
            x_start = int(start_x + col * cell_width)
            
            y_roi_start = int(y_start + current_height * roi_margin)
            y_roi_end = int(y_start + current_height * (1 - roi_margin))
            x_roi_start = int(x_start + cell_width * roi_margin)
            x_roi_end = int(x_start + cell_width * (1 - roi_margin))
            
            plt.gca().add_patch(plt.Rectangle((x_roi_start, y_roi_start),
                                            x_roi_end - x_roi_start,
                                            y_roi_end - y_roi_start,
                                            fill=False, color='red', alpha=0.5))
    
    plt.subplot(1, 2, 2)
    marking_result = analyze_fixed_id_marking(
        marking_area, start_point, cell_size, first_row_height, first_row_gap, 
        rows, cols, first_row_margin, other_rows_margin
    )
    plt.imshow(marking_result, cmap='binary')
    plt.title('Marking Analysis Result')
    plt.grid(True)
    
    plt.tight_layout()
    plt.show() 