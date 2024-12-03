import cv2
import numpy as np

def correct_skew(image):
    """
    이미지의 기울기를 보정하는 함수
    
    Args:
        image: 입력 이미지 (컬러 또는 그레이스케일)
    Returns:
        보정된 이미지
    """
    # 그레이스케일 변환 (이미 그레이스케일이면 그대로 사용)
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # 엣지 검출 부분 개선
    edges = cv2.Canny(gray, 30, 200, apertureSize=3)  # 임계값 조정
    
    # 허프 변환 매개변수 조정
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 30,  # threshold 값 낮춤
                           minLineLength=40,  # 더 짧은 선도 감지
                           maxLineGap=10)  # gap 허용치 증가
    
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 수평 판단 기준 완화
            if abs(x2 - x1) > abs(y2 - y1) * 0.5:  # 수평 조건 완화
                angle = np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi
                # 극단적인 각도 제외
                if abs(angle) < 30:  # 45도에서 30도로 변경
                    angles.append(angle)
    
    if angles:
        # 이상치 제거 후 평균 계산
        angles = np.array(angles)
        mean_angle = np.mean(angles)
        std_angle = np.std(angles)
        filtered_angles = angles[abs(angles - mean_angle) < 2 * std_angle]
        
        if len(filtered_angles) > 0:
            median_angle = np.median(filtered_angles)
            print(f"skew_correction_debug: 감지된 모든 각도들의 개수: {len(angles)}")  # 디버깅용 출력 추가
            print(f"skew_correction_debug: 필터링된 각도들의 개수: {len(filtered_angles)}")  # 디버깅용 출력 추가
            # print(f"skew_correction_debug: 필터링된 각도들: {filtered_angles}")  # 디버깅용 출력 추가
            print(f"skew_correction_debug: 감지된 기울기: {median_angle:.2f}도")
            print(f"skew_correction_debug: 보정할 각도: {-median_angle:.2f}도")
            
            # 원본 이미지 회전
            center = (image.shape[1] // 2, image.shape[0] // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]),
                                    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
    
    
    return image

if __name__ == "__main__":
    # 테스트 코드
    image = cv2.imread("OMR.png")
    if image is None:
        print("이미지를 불러올 수 없습니다.")
        exit()
        
    corrected = correct_skew(image)  # 그레이스케일 변환 없이 직접 전달
    
    # 결과 확인
    cv2.imshow('Original', image)
    cv2.imshow('Corrected', corrected)
    cv2.waitKey(0)
    cv2.destroyAllWindows() 