import os
import tkinter as tk
from tkinter.filedialog import askopenfilename
from pyhwpx import Hwp



def center_window(root, width=300, height=200):
    # 화면의 너비와 높이 얻기
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # 창의 위치 계산
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
 
    # 창의 크기와 위치 설정
    root.geometry(f'{width}x{height}+{x}+{y}') # 여기서 +{x} + {y}는 뭘 의미하는 거지?

def get_user_input():
    result = {'학교정보': None, '시험범위리스트': None}  # 결과를 저장할 딕셔너리

    def on_submit():
        try:
            학교정보 = entry_학교정보.get()
            시험범위리스트_str = entry_시험범위리스트.get()
            시험범위리스트 = list(map(int, 시험범위리스트_str.split(',')))
            result['학교정보'] = 학교정보
            result['시험범위리스트'] = 시험범위리스트
            root.quit()  # mainloop 종료
            root.destroy()  # 창 닫기
        except ValueError:
            tk.messagebox.showerror("오류", "시험범위 입력 형식이 잘못되었습니다.\n숫자와 쉼표만 입력해주세요.")
            return
    
    # Create the main application window
    
    root = tk.Tk()
    
    center_window(root, 600, 80)
    # root.geometry("600x250") 창크기조절
    
    
    tk.Label(root, text="학교 정보 (ex : 송양2):").grid(row=0, column=0)
    entry_학교정보 = tk.Entry(root) ## 입력창 하나를 만들어서 entry_학교정보 변수에 할당
    entry_학교정보.grid(row=0, column=1)

    tk.Label(root, text="시험범위 (ex : 20,21,22 (장문은 41,43으로)").grid(row=2, column=0)
    entry_시험범위리스트 = tk.Entry(root)
    entry_시험범위리스트.grid(row=2, column=1)

    # Create and place the submit button
    submit_button = tk.Button(root, text="Submit", command=on_submit)
    submit_button.grid(row=3, column=2, columnspan=2)

    root.mainloop() # 여기서 .mainloop() 메서드는 뭘하는거지?

    return result['학교정보'], result['시험범위리스트']


def 찾기(text):
    hwp.HAction.GetDefault("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    hwp.HParameterSet.HFindReplace.FindString = f"{text}"
    hwp.HParameterSet.HFindReplace.Direction = hwp.FindDir("Forward")
    hwp.HParameterSet.HFindReplace.IgnoreMessage = 2  # 메시지 뜨면 자동으로 (1=Yes, 2=No)
    hwp.HParameterSet.HFindReplace.FindType = 1  # 일반 텍스트 찾기
    return hwp.HAction.Execute("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)

def 위로_찾기_아무거나():
    hwp.HAction.GetDefault("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)
    hwp.HParameterSet.HFindReplace.FindString = "*"  # 정규식에서 '.'은 공백을 제외한 모든 문자와 매칭
    hwp.HParameterSet.HFindReplace.Direction = hwp.FindDir("Backward")
    hwp.HParameterSet.HFindReplace.FindType = 2  # 일반 텍스트 찾기
    hwp.HParameterSet.HFindReplace.UseWildCards = 1  # 정규식 사용 설정
    hwp.HParameterSet.HFindReplace.IgnoreMessage = 2  # 메시지 무시 설정
    return hwp.HAction.Execute("RepeatFind", hwp.HParameterSet.HFindReplace.HSet)



def 현재문단블록처리():
    hwp.HAction.Run("MoveParaBegin")
    hwp.HAction.Run("MoveSelParaEnd")

def 블록내_텍스트_포함_여부(text):
    try: 
        hwp.InitScan(Range=0xff)  # 0xff <<선택된 범위 내에서 검색
    except:
        hwp.InitScan(range=0xff)
    _, range_text = hwp.GetText()  # 텍스트만 추출
    hwp.ReleaseScan() # releaseScan이란 함수는 스캔을 해제.
    hwp.HAction.Run("MoveParaEnd")
    return f"{text}" in range_text # 이경우, 해당 target이 text에 포함되어있으면 True, 아니면 False를 반환.

def 블록내_리스트_포함_여부(str_list):
    try: 
        hwp.InitScan(Range=0xff)  
    except:
        hwp.InitScan(range=0xff)
    _, range_text = hwp.GetText()  
    hwp.ReleaseScan()
    hwp.HAction.Run("MoveParaEnd")
    
    # 지울번호리스트의 각 숫자를 문자열로 변환하여 확인
    return any(str(번호) in range_text for 번호 in str_list)

def 둘중_빠른것_찾기(word1, word2):
    hwp.SetMessageBoxMode(0x20000) # 예/아니오 중에 아니오를 누름
    start_pos = hwp.GetPos()

    result1 = 찾기(word1)
    pos1 = hwp.GetPos() if result1 else None
        
    hwp.SetPos(*start_pos)
    
    result2 = 찾기(word2)
    pos2 = hwp.GetPos() if result2 else None
    
    hwp.SetPos(*start_pos)
    
    hwp.SetMessageBoxMode(0xF0000) # 경고창이 기본모드로 바뀜
    
    if not result1 and not result2:
        return False
    else:
        if not result1:  # word1을 못 찾은 경우
            hwp.SetPos(*pos2)
            return True
        elif not result2:  # word2를 못 찾은 경우
            hwp.SetPos(*pos1)
            return True
        else:  # 둘 다 찾은 경우
            if pos1[1] < pos2[1]:
                hwp.SetPos(*pos1)
            else:
                hwp.SetPos(*pos2)
            return True
        
        
def hwp선택():
    """
    사용자에게 선택창을 띄우고
    사용자가 선택한 한글파일의 경로를 반환합니다
    
    Returns:
        str: 선택된 한글 파일의 전체 경로
        
    Raises:
        Exception: 파일이 선택되지 않았을 경우 발생
    """
    
    # Tkinter 루트 윈도우 생성
    root = tk.Tk()
    root.withdraw()  # 메인 윈도우 숨기기
    
    # 파일 선택 다이얼로그 열기
    hwp경로 = askopenfilename(
        title="문제를 추릴 hwp 파일을 선택하세요",
        filetypes=[
            ("한글 파일", "*.hwp;*.hwpx"),  # hwp와 hwpx 모두 인식
            ("모든 파일", "*.*")
        ]
    )
    
    # 파일이 선택되지 않았다면
    if not hwp경로:
        raise Exception("파일이 선택되지 않았습니다.")
        
    return hwp경로


if __name__ == '__main__':
    
    
    hwp경로 = hwp선택()
    hwp가속한폴더 = os.path.dirname(hwp경로)
    hwp파일이름 = os.path.splitext(os.path.basename(hwp경로))[0]  # 확장자 제외
    
    학교정보, 시험범위리스트 = None, None        # global 변수 선언을 하려면 일단 변수가 선언되어야함
    학교정보, 시험범위리스트 = get_user_input()  #get_user_input 함수의 리턴값을 각 변수에 할당
    
    전체리스트 = [x for x in range(18, 44) if x != 42]
    지울번호리스트 = [f"_{x}" for x in 전체리스트 if x not in 시험범위리스트]
    # 지울번호리스트 = ["_20", "_21", "_22", "_23", "_30", "_31", "_32", "_33", "_41"]
    print(f"{학교정보} hwp에서 지울 번호 : {지울번호리스트}")
    
    hwp = Hwp(visible=True)
    hwp.Open(hwp경로)
    # hwp = Hwp()
    
    print("hwp파일을 열었습니다.")
    
    ######### 어법 문제 이외 문제들 삭제
    
    hwp.Run("MoveDocBegin")
    hwp.SetMessageBoxMode(0x20000) # 예/아니오 중에 아니오를 누름
    
    print("시험 범위 이외의 문제들을 삭제합니다.")
    while 찾기("[20"):
        hwp.Run("MoveParaBegin")
        hwp.Run("MovePrevParaBegin")
        현재문단블록처리()
        if not 블록내_텍스트_포함_여부("어법"):
            hwp.Run("MoveParaBegin")
            startpos = hwp.GetPos()
            hwp.Run("MoveNextParaBegin")
            hwp.Run("MoveParaEnd")
            둘중_빠른것_찾기("[20", "빠른 정답")
            현재문단블록처리()
            if 블록내_리스트_포함_여부("[20"):
                hwp.Run("MovePrevParaBegin")
                hwp.Run("MovePrevParaBegin")
            else:
                hwp.Run("MovePageBegin")
                hwp.Run("MoveLeft")

            endpos = hwp.GetPos()
            
            hwp.SetPos(*startpos)
            hwp.Run("Select")
            hwp.SetPos(*endpos)
            hwp.HAction.Run("Delete")
        else:
            hwp.Run("MoveNextParaBegin")
            hwp.Run("MoveParaEnd")
            
    hwp.SetMessageBoxMode(0xF0000) # 경고창이 기본모드로 바뀜
    
    
    ########### 시험 범위 이외 문제들 삭제
    while 찾기("[20"):
        현재문단블록처리()
        if 블록내_리스트_포함_여부(지울번호리스트):
            hwp.Run("MoveParaBegin")
            hwp.Run("MovePrevParaBegin")
            startpos = hwp.GetPos()
            hwp.Run("MoveNextParaBegin")
            hwp.Run("MoveParaEnd")

            둘중_빠른것_찾기("[20", "빠른 정답")
            현재문단블록처리()
            if 블록내_리스트_포함_여부("[20"):
                hwp.Run("MovePrevParaBegin")
                hwp.Run("MovePrevParaBegin")
            else:
                hwp.Run("MovePageBegin")
                hwp.Run("MoveLeft")

            endpos = hwp.GetPos()
            
            hwp.SetPos(*startpos)
            hwp.Run("Select")
            hwp.SetPos(*endpos)
            hwp.HAction.Run("Delete")
            
        else:
            hwp.Run("MoveParaEnd")
            
    hwp.SetMessageBoxMode(0xF0000) # 경고창이 기본모드로 바뀜 
    저장경로 = os.path.join(hwp가속한폴더, f"{hwp파일이름}_{학교정보}_어법만.hwpx")
    
    hwp.SaveAs(저장경로)
    hwp.Close()
    hwp.Quit()
    print(f"파일을 저장하였습니다. : {저장경로}")       
            
################################################## 아래는 페이지 정리(미구현)
'''
    위로_찾기_아무거나()
      
      
      
                
            hwp.Run("MoveParaBegin")
            startpos = hwp.GetPos()
            hwp.Run("MoveParaEnd")
            둘중_빠른것_찾기("#", "<<<")
            현재문단블록처리()
            if 블록내_텍스트_포함_여부("<<<"):
                hwp.Run("MovePageBegin")
                hwp.Run("MoveLeft")
            else:
                hwp.Run("MoveParaBegin")
            endpos = hwp.GetPos()
            
            hwp.SetPos(*startpos)
            hwp.Run("Select")
            hwp.SetPos(*endpos)
            hwp.HAction.Run("Delete")
    
    hwp.Run("MoveDocBegin")
    
    #### 페이지를 넘어가는 문제가 없도록 정리
    
    print("페이지를 넘어가는 문제가 없도록 정리합니다.")
    
    while 찾기("#"):
        hwp.Run("MoveLineBegin")
        start_page = hwp.KeyIndicator()[3]
        start_pos = hwp.GetPos()
        hwp.Run("MoveParaEnd")
        둘중_빠른것_찾기("#", "<<<")
        현재문단블록처리()
        if 블록내_텍스트_포함_여부("<<<"):
            hwp.Run("MovePageBegin")
            hwp.Run("MoveLeft")
        else:
            hwp.Run("MoveParaBegin")
        위로_찾기_아무거나()
        hwp.Run("MoveParaEnd")
        end_page = hwp.KeyIndicator()[3]
        endpos = hwp.GetPos()
        if end_page != start_page:
            hwp.SetPos(*start_pos)
            hwp.Run("BreakPage")
            hwp.Run("MoveParaEnd")
    
    hwp.SetMessageBoxMode(0xF0000) # 경고창이 기본모드로 바뀜
    
'''