import cv2
import numpy as np
import pandas as pd
from find_contours import find_large_contours
from warp_image import get_warped_image
from skew_correction import correct_skew



# 이미지 로드
image = cv2.imread('OMR.png')
# 기울임 보정 추가
corrected_image = correct_skew(image)  # 기존 함수 사용

gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 이미지를 그레이 스케일로 변환(회색)



min_area = 100000
contours = find_large_contours(corrected_image, min_area)  # 보정된 이미지로 외곽선 추출



# 외곽선을 영역별로 매칭
id_contour = contours[0]      # 학번 영역
name_contour = contours[1]    # 이름 영역
answer_contours = contours[2:]  # 답안표시영역1, 2, 3

# 학번 영역 처리
id_warp = get_warped_image(id_contour, gray_image) # get_warped_image 함수는 외곽선 좌표와 그레이 이미지를 인자로 받아 해당 외곽선에 해당하는 영역만 이미지로 변환하는 함수이다.


### 여기까지 완료 ############################################################ 24.11.16(토) 11:30pm

if id_warp is not None:
    # 학번 영역의 마킹 인식
    # 예를 들어, 학번은 8자리이고, 각 자리마다 10개의 숫자(0~9)가 있음
    num_digits = 8
    num_options = 10
    id_result = ''
    cell_width = id_warp.shape[1] / num_digits
    cell_height = id_warp.shape[0] / num_options

    for i in range(num_digits):
        max_fill = 0
        selected_digit = None
        for j in range(num_options):
            x = int(i * cell_width)
            y = int(j * cell_height)
            w = int(cell_width)
            h = int(cell_height)
            cell = id_warp[y:y+h, x:x+w]
            # 마킹 여부 판단 (검은 픽셀의 비율 사용)
            total_pixels = w * h
            black_pixels = cv2.countNonZero(255 - cell)
            fill_ratio = black_pixels / total_pixels
            if fill_ratio > max_fill and fill_ratio > 0.5:
                max_fill = fill_ratio
                selected_digit = str(j)
        if selected_digit is not None:
            id_result += selected_digit
        else:
            id_result += '*'
else:
    id_result = '인식 실패'

# 이름 영역 처리
name_warp = get_warped_image(name_contour, gray_image)
if name_warp is not None:
    # 이름 영역의 마킹 인식
    # 예를 들어, 이름은 5글자이고, 각 글자마다 20개의 선택지가 있음 (가~하)
    num_chars = 5
    num_options = 20  # 가나다 순으로 20개의 글자라고 가정
    name_result = ''
    cell_width = name_warp.shape[1] / num_chars
    cell_height = name_warp.shape[0] / num_options

    hangul_chars = ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차',
                    '카', '타', '파', '하', '거', '너', '더', '러', '머', '버']

    for i in range(num_chars):
        max_fill = 0
        selected_char = None
        for j in range(num_options):
            x = int(i * cell_width)
            y = int(j * cell_height)
            w = int(cell_width)
            h = int(cell_height)
            cell = name_warp[y:y+h, x:x+w]
            # 마킹 여부 판단
            total_pixels = w * h
            black_pixels = cv2.countNonZero(255 - cell)
            fill_ratio = black_pixels / total_pixels
            if fill_ratio > max_fill and fill_ratio > 0.5:
                max_fill = fill_ratio
                selected_char = hangul_chars[j]
        if selected_char is not None:
            name_result += selected_char
        else:
            name_result += '*'
else:
    name_result = '인식 실패'

# 답안 영역 처리
answers = []
question_num = 1
for answer_contour in answer_contours:
    answer_warp = get_warped_image(answer_contour, gray_image)
    if answer_warp is not None:
        # 각 답안 영역에서 답안 인식
        num_questions = 10  # 예시로 각 영역에 10문항이 있다고 가정
        num_choices = 5     # 선택지 5개 (A~E)
        cell_width = answer_warp.shape[1] / num_choices
        cell_height = answer_warp.shape[0] / num_questions

        for i in range(num_questions):
            selected_choice = None
            max_fill = 0
            for j in range(num_choices):
                x = int(j * cell_width)
                y = int(i * cell_height)
                w = int(cell_width)
                h = int(cell_height)
                cell = answer_warp[y:y+h, x:x+w]
                # 마킹 여부 판단
                total_pixels = w * h
                black_pixels = cv2.countNonZero(255 - cell)
                fill_ratio = black_pixels / total_pixels
                if fill_ratio > max_fill and fill_ratio > 0.5:
                    max_fill = fill_ratio
                    selected_choice = chr(ord('A') + j)
            if selected_choice is not None:
                answers.append({'문항번호': question_num, '답안': selected_choice})
            else:
                answers.append({'문항번호': question_num, '답안': '*'})
            question_num +=1
    else:
        print("답안 영역을 감지하지 못했습니다.")

# 결과 출력 및 저장
print(f"학번: {id_result}")
print(f"이름: {name_result}")
df_answers = pd.DataFrame(answers)
print(df_answers)

# CSV 파일로 저장
df_answers.to_csv('omr_answers.csv', index=False)




#################################이전


# 가장 큰 외곽선 추출 (OMR 카드로 가정)
contours = sorted(contours, key=cv2.contourArea, reverse=True)
omr_contour = contours[0]

# OMR 카드의 4개 모서리 점 찾기
epsilon = 0.02 * cv2.arcLength(omr_contour, True)
approx = cv2.approxPolyDP(omr_contour, epsilon, True)

# 투시 변환을 위한 좌표 정렬 함수
def order_points(pts):
    rect = np.zeros((4, 2), dtype = "float32")
    s = pts.sum(axis = 1)
    rect[0] = pts[np.argmin(s)]  # 좌상단
    rect[2] = pts[np.argmax(s)]  # 우하단

    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]  # 우상단
    rect[3] = pts[np.argmax(diff)]  # 좌하단

    return rect

# 투시 변환 적용
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

    # 마킹 영역 분할 및 인식 (예시로 10문항, 선택지 5개 가정)
    results = []
    num_questions = 10
    num_choices = 5
    cell_width = maxWidth / num_choices
    cell_height = maxHeight / num_questions

    for i in range(num_questions):
        row = []
        for j in range(num_choices):
            x = int(j * cell_width)
            y = int(i * cell_height)
            w = int(cell_width)
            h = int(cell_height)
            cell = warp[y:y+h, x:x+w]
            # 마킹 여부 판단 (평균 픽셀 값 사용)
            mean_val = cv2.mean(cell)[0]
            if mean_val > 127:
                row.append(0)
            else:
                row.append(1)
        results.append(row)

    # pandas DataFrame 생성
    df = pd.DataFrame(results, columns=['A', 'B', 'C', 'D', 'E'])
    print(df)

    # CSV 파일로 저장
    df.to_csv('omr_results.csv', index=False)

else:
    print("OMR 카드를 감지하지 못했습니다.")