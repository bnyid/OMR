import cv2
import numpy as np
from find_contours import find_large_contours
from skew_correction import correct_skew

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # 좌상단
    rect[2] = pts[np.argmax(s)]  # 우하단

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # 우상단
    rect[3] = pts[np.argmax(diff)]  # 좌하단

    return rect

def get_warped_image(contour, gray_image, show_result=False): # 이미지를 보고 싶으면 show_result=True로 설정
    epsilon = 0.01 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
                                                    
    if len(approx) == 4:
        pts = approx.reshape(4, 2)
        rect = order_points(pts)
        (tl, tr, br, bl) = rect

        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warp = cv2.warpPerspective(gray_image, M, (maxWidth, maxHeight))
        
        if show_result:
            cv2.imshow('Warped Image', warp)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        return warp
    else:
        return None 

if __name__ == "__main__":
    ############################################################ Parameters
    image = cv2.imread("OMR.png")
    i = 0 # 확인하고자 하는 영역의 인덱스
    ############################################################    

    if image is None:
        print("이미지를 불러올 수 없습니다.")
        exit()
        
    # 그레이스케일 변환 

    
    # 기울기 보정
    corrected_image = correct_skew(image)
    gray_image = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)
    
    # 보정된 이미지로 윤곽선 검출
    contours = find_large_contours(gray_image, 100000)
    
    if contours and len(contours) > 0:
        warped = get_warped_image(contours[i], gray_image)
        if warped is not None:
            print("이미지 와핑 완료")
        else:
            print("적절한 사각형을 찾을 수 없습니다.")
    else:
        print("윤곽선을 찾을 수 없습니다.") 