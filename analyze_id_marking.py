import numpy as np
import matplotlib.pyplot as plt

def analyze_id_marking(marking_area, rows, cols):
    """마킹 영역을 rows x cols 격자로 분석하여 마킹된 위치를 찾는 함수
    
    Args:
        marking_area: 분석할 마킹 영역 이미지
        rows: 세로 격자 수
        cols: 가로 격자 수
    """
    
    height, width = marking_area.shape
    
    # 세로와 가로 각각 분할
    cell_height = height // rows
    cell_width = width // cols
    
    # 마킹 결과를 저장할 2차원 배열 (rows x cols)
    marking_result = np.zeros((rows, cols), dtype=int)
    
    # 각 셀별로 마킹 여부 확인
    for row in range(rows):
        for col in range(cols):
            # 현재 셀의 영역 추출
            cell = marking_area[row*cell_height:(row+1)*cell_height, 
                              col*cell_width:(col+1)*cell_width]
            
            # 마킹 영역 분석을 위한 ROI 설정
            roi_margin = 0.2
            roi_y_start = int(cell_height * roi_margin)
            roi_y_end = int(cell_height * (1 - roi_margin))
            roi_x_start = int(cell_width * roi_margin)
            roi_x_end = int(cell_width * (1 - roi_margin))
            
            roi = cell[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
            
            # ROI 영역 분석
            avg_value = np.mean(roi)
            dark_pixel_ratio = np.sum(roi < 200) / roi.size
            
            # 마킹 판단
            is_marked = (avg_value < 200) or (dark_pixel_ratio > 0.3)
            
            if is_marked:
                marking_result[row][col] = 1
    
    return marking_result

def visualize_marking_analysis(marking_area, rows, cols):
    """마킹 분석 과정을 시각화하는 함수"""
    height, width = marking_area.shape
    cell_height = height // rows
    cell_width = width // cols
    
    plt.figure(figsize=(15, 10))
    
    # 원본 이미지와 분석 영역 표시
    plt.subplot(1, 2, 1)
    plt.imshow(marking_area, cmap='gray')
    plt.title('Original with ROI Areas')
    
    # ROI 영역 표시
    for row in range(rows):
        for col in range(cols):
            roi_margin = 0.2
            y_start = row * cell_height + int(cell_height * roi_margin)
            y_end = (row + 1) * cell_height - int(cell_height * roi_margin)
            x_start = col * cell_width + int(cell_width * roi_margin)
            x_end = (col + 1) * cell_width - int(cell_width * roi_margin)
            
            plt.gca().add_patch(plt.Rectangle((x_start, y_start), 
                                            x_end - x_start, 
                                            y_end - y_start,
                                            fill=False, color='red', alpha=0.5))
    
    # 격자 표시
    for i in range(rows + 1):
        plt.axhline(y=i*cell_height, color='blue', linestyle='-', alpha=0.3)
    for i in range(cols + 1):
        plt.axvline(x=i*cell_width, color='blue', linestyle='-', alpha=0.3)
    
    # 분석 결과
    plt.subplot(1, 2, 2)
    marking_result = analyze_id_marking(marking_area, rows, cols)
    plt.imshow(marking_result, cmap='binary')
    plt.title('Marking Analysis Result')
    plt.grid(True)
    
    plt.tight_layout()
    plt.show() 