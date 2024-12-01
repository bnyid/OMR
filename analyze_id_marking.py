import numpy as np
import matplotlib.pyplot as plt
import cv2

def find_grid_lines(marking_area, rows=10, cols=10):
    """수평/수직 프로젝션을 통해 실제 격자 라인의 위치를 찾는 함수"""
    height, width = marking_area.shape
    
    # 이미지 이진화 (격자 라인이 더 잘 보이도록)
    _, binary = cv2.threshold(marking_area, 200, 255, cv2.THRESH_BINARY)
    
    # 수직 방향 프로젝션 (가로 라인 찾기)
    horizontal_proj = np.sum(binary, axis=1)
    
    # 가로 라인 위치 찾기
    row_positions = [0]  # 시작점
    section_height = height // rows
    
    for i in range(1, rows):
        # 각 구간의 중앙 부근에서 격자 라인 찾기
        center = i * section_height
        search_start = max(center - section_height//4, 0)
        search_end = min(center + section_height//4, height)
        
        # 해당 구간에서 가장 밝은 부분(격자 라인) 찾기
        section = horizontal_proj[search_start:search_end]
        max_val_idx = np.argmax(section) + search_start
        
        # 너무 급격한 변화 방지
        if i > 1:
            expected_pos = row_positions[-1] + section_height
            max_deviation = section_height // 4
            if abs(max_val_idx - expected_pos) > max_deviation:
                max_val_idx = expected_pos
        
        row_positions.append(max_val_idx)
    
    row_positions.append(height)  # 끝점
    
    # 수평 방향 프로젝션 (세로 라인 찾기)
    vertical_proj = np.sum(binary, axis=0)
    
    # 세로 라인 위치 찾기
    col_positions = [0]  # 시작점
    section_width = width // cols
    
    for i in range(1, cols):
        # 각 구간의 중앙 부근에서 격자 라인 찾기
        center = i * section_width
        search_start = max(center - section_width//4, 0)
        search_end = min(center + section_width//4, width)
        
        # 해당 구간에서 가장 밝은 부분(격자 라인) 찾기
        section = vertical_proj[search_start:search_end]
        max_val_idx = np.argmax(section) + search_start
        
        # 너무 급격한 변화 방지
        if i > 1:
            expected_pos = col_positions[-1] + section_width
            max_deviation = section_width // 4
            if abs(max_val_idx - expected_pos) > max_deviation:
                max_val_idx = expected_pos
        
        col_positions.append(max_val_idx)
    
    col_positions.append(width)  # 끝점
    
    # 간격 균일화 보정
    row_positions = np.array(row_positions)
    col_positions = np.array(col_positions)
    
    # 극단적인 간격 차이 보정
    row_diffs = np.diff(row_positions)
    col_diffs = np.diff(col_positions)
    
    median_row_diff = np.median(row_diffs)
    median_col_diff = np.median(col_diffs)
    
    for i in range(1, len(row_positions)-1):
        if abs(row_diffs[i-1] - median_row_diff) > median_row_diff * 0.3:
            row_positions[i] = row_positions[i-1] + median_row_diff
            
    for i in range(1, len(col_positions)-1):
        if abs(col_diffs[i-1] - median_col_diff) > median_col_diff * 0.3:
            col_positions[i] = col_positions[i-1] + median_col_diff
    
    return row_positions.astype(int), col_positions.astype(int)

def analyze_id_marking(marking_area, rows, cols):
    """개선된 마킹 영역 분석 함수"""
    # 격자 라인 위치 찾기
    row_positions, col_positions = find_grid_lines(marking_area, rows, cols)
    
    # 마킹 결과를 저장할 2차원 배열
    marking_result = np.zeros((rows, cols), dtype=int)
    
    # 각 셀별로 마킹 여부 확인
    for row in range(rows):
        for col in range(cols):
            # 현재 셀의 영역 추출
            cell = marking_area[row_positions[row]:row_positions[row+1],
                              col_positions[col]:col_positions[col+1]]
            
            # ROI 설정
            cell_height = cell.shape[0]
            cell_width = cell.shape[1]
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
    """개선된 시각화 함수"""
    # 격자 라인 위치 찾기
    row_positions, col_positions = find_grid_lines(marking_area, rows, cols)
    
    plt.figure(figsize=(15, 10))
    
    # 원본 이미지와 분석 영역 표시
    plt.subplot(1, 2, 1)
    plt.imshow(marking_area, cmap='gray')
    plt.title('Original with ROI Areas')
    
    # 실제 격자 라인 표시
    for pos in row_positions:
        plt.axhline(y=pos, color='blue', linestyle='-', alpha=0.3)
    for pos in col_positions:
        plt.axvline(x=pos, color='blue', linestyle='-', alpha=0.3)
    
    # ROI 영역 표시
    for row in range(len(row_positions)-1):
        for col in range(len(col_positions)-1):
            cell_height = row_positions[row+1] - row_positions[row]
            cell_width = col_positions[col+1] - col_positions[col]
            roi_margin = 0.2
            
            y_start = row_positions[row] + int(cell_height * roi_margin)
            y_end = row_positions[row] + int(cell_height * (1 - roi_margin))
            x_start = col_positions[col] + int(cell_width * roi_margin)
            x_end = col_positions[col] + int(cell_width * (1 - roi_margin))
            
            plt.gca().add_patch(plt.Rectangle((x_start, y_start),
                                            x_end - x_start,
                                            y_end - y_start,
                                            fill=False, color='red', alpha=0.5))
    
    # 분석 결과
    plt.subplot(1, 2, 2)
    marking_result = analyze_id_marking(marking_area, rows, cols)
    plt.imshow(marking_result, cmap='binary')
    plt.title('Marking Analysis Result')
    plt.grid(True)
    
    plt.tight_layout()
    plt.show() 