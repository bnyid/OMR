import math, os, csv, ast
import pandas as pd
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog
from pyhwpx import Hwp
from datetime import datetime

def center_window(root, width=300, height=200):
        # 화면의 너비와 높이 얻기
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # 창의 위치 계산
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2 - 120

        # 창의 크기와 위치 설정
        root.geometry(f'{width}x{height}+{x}+{y}')
def get_user_titles():
    user_input = {'cover_title' : '' , 'main_title': '','folder_name' : ''}
    def on_submit():
        user_input['cover_title'] = entry_cover_title.get()
        user_input['sub_title'] = entry_sub_title.get()    
        user_input['main_title'] = entry_main_title.get()
        
        if not user_input['cover_title'] or not user_input['main_title'] or not user_input['sub_title']:
            messagebox.showwarning("입력 오류", "모든 타이틀을 입력하세요")
        else:
            root.quit()
    
   
    root = tk.Tk()
    root.title("단어장 상단 타이틀 입력하기")
    center_window(root, width=1100, height=550)

    # 그림 설명
    image1 = tk.PhotoImage(file=r"C:\Users\samsung-user\Documents\code_project\hwp_local\images\표지타이틀_설명.png")
    image1_label = tk.Label(root, image=image1)
    image1_label.grid(column=0,row=0, columnspan=2)
    
    image2 = tk.PhotoImage(file=r"C:\Users\samsung-user\Documents\code_project\hwp_local\images\메인+서브타이틀_설명.png")
    image2_label = tk.Label(root, image=image2)
    image2_label.grid(column=2,row=0,columnspan=2)


    ttk.Label(root, text = "표지 타이틀(주로 학교+학년) : ").grid(column=0,row=2, sticky=tk.E)
    entry_cover_title = tk.Entry(root)
    entry_cover_title.grid(column=1,row=2, sticky=tk.W)
    
    ttk.Label(root, text = "서브 타이틀 : ").grid(column=2, row=2, sticky=tk.E)
    entry_sub_title = tk.Entry(root)
    entry_sub_title.grid(column=3, row=2, sticky=tk.W)
    
    ttk.Label(root, text = "메인 타이틀(주로 학교+학년) : ").grid(column=2,row=3, sticky=tk.E)
    entry_main_title = tk.Entry(root)
    entry_main_title.grid(column=3,row=3, sticky=tk.W)

    button_submit = tk.Button(root,width=18, text="제출", command=on_submit)
    button_submit.grid(column=2, row=4, columnspan=2, sticky=tk.W)  # 버튼을 1열, 2행에 배치

    root.mainloop()
    root.destroy()
    
    return user_input['cover_title'], user_input['main_title'], user_input['sub_title']
def select_items(df):
    
    # 선택된 항목을 저장할 리스트와 딕셔너리
    selected_items_list = []
    selected_items = {'구분1' : None, '구분2' : None, '구분3' : None ,'구분4': None, '구분5': None, '구분6' : None, '구분7' : '', '단어_수' : None}

    # 마지막으로 선택한 '구분n'의 항목들을 관리하기 위한 딕셔너리
    last_selected_index = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7:None}

    #카테고리 박스를 관리하기 위한 딕셔너리 생성
    def clear_category_listbox(i):
        category_listboxes[i].delete(0,tk.END)          
    def highlight_selection(listbox, selected_index, category_num):
        # 이전에 선택된 항목이 유효한지 확인 (항목 수를 초과하지 않는지)
        if last_selected_index[category_num] is not None:
            if last_selected_index[category_num] < listbox.size():
                # 유효한 경우 이전 선택 항목의 색상을 초기화
                listbox.itemconfig(last_selected_index[category_num], bg='white', selectbackground="blue")
        # 선택된 항목의 배경을 변경
        listbox.itemconfig(selected_index, bg='lightblue', selectbackground="blue")
        # 마지막으로 선택된 인덱스를 업데이트
        last_selected_index[category_num] = selected_index
    def on_category1_select(event):
        selected = category1_listbox.curselection()
        if selected:
            selected_category1 = category1_listbox.get(selected[0])
            selected_items['구분1'] = selected_category1
            highlight_selection(category1_listbox, selected[0], 1)
            update_category2_listbox()
    def update_category2_listbox():          
        for i in range(2,7):
            clear_category_listbox(i)
        filtered_df = df[df['구분1']== selected_items['구분1']]
        category2s = filtered_df['구분2'].unique()
        
        for i in category2s:
            category2_listbox.insert(tk.END, i)         
    def on_category2_select(event):
        selected = category2_listbox.curselection()
        if selected:
            selected_category2 = category2_listbox.get(selected[0])
            selected_items['구분2'] = selected_category2
            highlight_selection(category2_listbox, selected[0], 2)
            update_category3_listbox()
    def update_category3_listbox():
        for i in range(3,7):
            clear_category_listbox(i)
        
        filtered_df = df[(df['구분1'] == selected_items['구분1']) 
                         & (df['구분2'] == selected_items['구분2'])]

        category3s = filtered_df['구분3'].unique()
        for category3 in category3s:
            category3_listbox.insert(tk.END,category3)
    def on_category3_select(event):
        selected = category3_listbox.curselection()
        if selected:
            selected_category3 = category3_listbox.get(selected[0])
            selected_items['구분3'] = selected_category3
            highlight_selection(category3_listbox, selected[0],3)
            update_category4_listbox()
    def update_category4_listbox():
        for i in range(4,7):
            clear_category_listbox(i)
        
        filtered_df = df[(df['구분1']== selected_items['구분1']) 
                         & (df['구분2']== selected_items['구분2']) 
                         & (df['구분3'] == selected_items['구분3'])]
        
        category4s = filtered_df['구분4'].unique()
        for category4 in category4s:
            category4_listbox.insert(tk.END, category4)
    def on_category4_select(event):
        selected = category4_listbox.curselection()
        if selected:
            selected_category4 = category4_listbox.get(selected[0])
            selected_items['구분4'] = selected_category4
            highlight_selection(category4_listbox, selected[0],4)
            update_category5_listbox()
    def update_category5_listbox():
        # 선택된 "구분4"에 해당하는 "구분5" 항목들을 Listbox에 표시
        for i in range(5,7):
            clear_category_listbox(i)  # 기존 항목 모두 삭제
        filtered_df = df[(df['구분1'] == selected_items['구분1']) 
                        & (df['구분2']== selected_items['구분2']) 
                        & (df['구분3'] == selected_items['구분3'])
                        & (df['구분4'] == selected_items['구분4'])]
        
                            # 구분4열을 선택하고 그게 사용자가 선택한 값과 일치하는지 판단하고 
                            # True/False값을 가지는 pandas.Series를 만듬
                            # 0 True
                            # 1 False
                            # 2 False 이런 시리즈를 반환
                            # df[시리즈]를 넣으니까, True인 행만 모아서 filtered_df에 할당함

        category5s_list = filtered_df['구분5'].unique()  # "구분5" 열에서 중복된 항목 제거하여 목록 만듬
        for category5 in category5s_list:
            category5_listbox.insert(tk.END, category5)
    def on_category5_select(event):
        selected = category5_listbox.curselection()
        if selected :
            selected_category5 = category5_listbox.get(selected[0])
            selected_items['구분5'] = selected_category5
            highlight_selection(category5_listbox, selected[0],5)
            update_category6_listbox()           
    def update_category6_listbox():
        clear_category_listbox(6)
        filtered_df = df[(df['구분1'] == selected_items['구분1']) 
                        & (df['구분2']== selected_items['구분2']) 
                        & (df['구분3'] == selected_items['구분3'])
                        & (df['구분4'] == selected_items['구분4'])
                        & (df['구분5'] == selected_items['구분5'])]
        category6s_list = filtered_df['구분6'].unique()
        for category6 in category6s_list:
            category6_listbox.insert(tk.END, category6)
    def on_category6_select(event):
        selected = category6_listbox.curselection()
        if selected:
            selected_items['구분6'] = [category6_listbox.get(i) for i in selected] # 튜플을 반복하면서 리스트로 반환함
            highlight_selection(category6_listbox, selected[0],6)
            if detail_selection_var.get():
                update_category7_listbox()
    def update_category7_listbox():
        clear_category_listbox(7)
        filtered_df = df[(df['구분1'] == selected_items['구분1']) 
                        & (df['구분2'] == selected_items['구분2']) 
                        & (df['구분3'] == selected_items['구분3'])
                        & (df['구분4'] == selected_items['구분4'])
                        & (df['구분5'] == selected_items['구분5'])
                        & (df['구분6'].isin(selected_items['구분6']))]
        category7s_list = filtered_df['구분7'].unique()
        for category7 in category7s_list:
            category7_listbox.insert(tk.END, category7)                
    def update_selected_count_label():
        selected_count = len(category7_listbox.curselection())
        selected_count_var.set(f"선택된 항목: {selected_count}개")
    def on_category7_select(event):
        selected = category7_listbox.curselection()
        if selected:
            selected_category7 = category7_listbox.get(selected[0])
            selected_items['구분7'] = selected_category7
            highlight_selection(category7_listbox, selected[0], 7)
        update_selected_count_label()  # 선택된 항목의 개수를 업데이트
    def on_detail_selection_change():
        if detail_selection_var.get():
            category6_listbox.config(selectmode=tk.SINGLE)
        else:
            category6_listbox.config(selectmode=tk.EXTENDED)
            clear_category_listbox(7)
        selected_items['구분7'] = None
        category6_listbox.selection_clear(0, tk.END)
    def on_select():
        # 구분6에 값이 존재할 때만 실행
        if selected_items['구분6']:
            
            # 선택모드에 따라 '구분7'에 값(리스트 or None) 할당
            if detail_selection_var.get():
                selected_indices = category7_listbox.curselection() # .curselection() 메써드는 튜플 반환함        
                if selected_indices :
                    selected_items['구분7'] = [category7_listbox.get(i) for i in selected_indices]
                else : 
                    messagebox.showwarning("오류", "세부선택 모드의 경우 구분7을 선택해야 합니다.")
                    return
            else:
                selected_indices = None
                selected_items['구분7'] = None        
            
            filtered_df = df[(df['구분1'] == selected_items['구분1']) 
                                & (df['구분2']== selected_items['구분2']) 
                                & (df['구분3'] == selected_items['구분3'])
                                & (df['구분4'] == selected_items['구분4'])
                                & (df['구분5'] == selected_items['구분5']) # isin()에 리스트 전달
                                & (df['구분6'].isin(selected_items['구분6']))
                            ]
            
            
            if selected_items['구분7']:
                filtered_df = filtered_df[filtered_df['구분7'].isin(selected_items['구분7'])]
                
            selected_items['단어_수'] = len(filtered_df)
            selected_items_list.append(selected_items.copy())
            
            if "모의고사" in selected_items['구분2']:
                if selected_items['구분7']:
                    summary_item = f"{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}_{selected_items['구분6']}___ {selected_items['구분7']} ___ 단어 수: {selected_items['단어_수']})"
                else:
                    summary_item = f"{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___ {selected_items['구분6']} ___ 단어 수: {selected_items['단어_수']})"
                
                
            elif "교과서" in selected_items['구분2']:
                if selected_items['구분7']:
                    summary_item = f"{selected_items['구분1']}_{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}_{selected_items['구분6']}___ {selected_items['구분7']} ___ 단어 수: {selected_items['단어_수']})"
                else:
                    summary_item = f"{selected_items['구분1']}_{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___ {selected_items['구분6']} ___ 단어 수: {selected_items['단어_수']})"
            else :
                summary_item = f"{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___{selected_items['구분6']} | 단어 수: {selected_items['단어_수']})"
                
            summary_listbox.insert(tk.END, summary_item)
            
            
            cumulative_word_count = sum(item['단어_수'] for item in selected_items_list)
            cumulative_word_count_var.set(str(cumulative_word_count))
            if detail_selection_var.get():
                category7_listbox.selection_clear(0, tk.END)
            else : 
                category6_listbox.selection_clear(0, tk.END)
        else:
            messagebox.showwarning("오류", "항목을 선택해주세요.")
    def save_selection_to_csv(file_path):
        # 현재 날짜와 요일을 가져오기 (MM-DD 형식의 날짜와 Mon, Tue 형식의 요일)
        current_date = datetime.now().strftime('%m-%d')  # 날짜 형식: MM-DD
        current_day = datetime.now().strftime('%a')  # 요일 형식: Mon, Tue, etc.

        # DataFrame 생성
        data = []
        for item in selected_items_list:
            data.append({
                'cover_title': cover_title,
                'date': current_date,
                'day': current_day,
                '구분1': item['구분1'],
                '구분2': item['구분2'],
                '구분3': item['구분3'],
                '구분4': item['구분4'],
                '구분5': item['구분5'],
                '구분6': item['구분6'],
                '구분7': item['구분7'],
                '단어_수': item['단어_수']
            })

        df = pd.DataFrame(data)
        file_exists = os.path.exists(file_path)
        df.to_csv(file_path, mode='a', index=False, header=not file_exists, encoding='utf-8')

    def on_final_select():
        if selected_items_list:
            save_selection_to_csv(r'C:\Users\samsung-user\Documents\code_project\hwp_local\word_book\selections.csv')
        root.quit()  # GUI 종료       
    def on_delete():
        selected_indices = summary_listbox.curselection()
        if selected_indices:
            for index in sorted(selected_indices, reverse=True): # reverse : 삭제할 때 인덱스가 변하는 문제를 방지함
                # Listbox에서 항목 삭제
                summary_listbox.delete(index)
                # selected_items_list에서 해당 항목 삭제
                del selected_items_list[index]
            # 누적 단어 수 업데이트
            cumulative_word_count = sum(item['단어_수'] for item in selected_items_list)
            cumulative_word_count_var.set(str(cumulative_word_count))
    def move_up():
        selected_index = summary_listbox.curselection()
        if selected_index and selected_index[0] > 0:
            index = selected_index[0]
            # 항목을 위로 이동
            item = selected_items_list.pop(index)
            selected_items_list.insert(index - 1, item)
            summary_item = summary_listbox.get(index)
            summary_listbox.delete(index)
            summary_listbox.insert(index - 1, summary_item)
            summary_listbox.select_set(index - 1)
    def move_down():
        selected_index = summary_listbox.curselection()
        if selected_index and selected_index[0] < len(selected_items_list) - 1:
            index = selected_index[0]
            # 항목을 아래로 이동
            item = selected_items_list.pop(index)
            selected_items_list.insert(index + 1, item)
            summary_item = summary_listbox.get(index)
            summary_listbox.delete(index)
            summary_listbox.insert(index + 1, summary_item)
            summary_listbox.select_set(index + 1)
    def load_previous_selections(file_path):
        # CSV 파일을 pandas DataFrame으로 읽어오기
        try:
            prev_selections_df = pd.read_csv(file_path, encoding='utf-8')

            # DataFrame에서 각 행을 format하여 listbox에 추가
            for _, row in prev_selections_df.iterrows():
                summary = (f"{row['cover_title']} | {row['date']}({row['day']}) | "
                        f"{row['구분1']}_{row['구분2']}_{row['구분3']}_{row['구분4']}_{row['구분5']}___"
                        f"{row['구분6']}___{row['구분7']}___단어 수: {row['단어_수']}")
                prev_summary_listbox.insert(tk.END, summary)
                
            return prev_selections_df

        except FileNotFoundError:
            print(f"File '{file_path}' not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
    def from_prev_to_present_summary():
        selected_indices = prev_summary_listbox.curselection() # 선택된 항목의 인덱스를 튜플로 반환

        for index in selected_indices:
            row = prev_selections_df.iloc[index]
            구분6 = ast.literal_eval(row.get('구분6', '[]')) if isinstance(row.get('구분6'), str) else row.get('구분6')
            구분7 = ast.literal_eval(row['구분7']) if isinstance(row['구분7'], str) else None if pd.isna(row['구분7']) else row['구분7']
            
            selected_items = {
                '구분1': row.get('구분1'),  
                '구분2': row.get('구분2'),
                '구분3': row.get('구분3'),
                '구분4': row.get('구분4'),
                '구분5': row.get('구분5'),
                '구분6': 구분6,
                '구분7': 구분7,
                '단어_수': int(row.get('단어_수')),  # '단어_수'가 없으면 0으로 기본값 설정
            }
            selected_items_list.append(selected_items)

            if "모의고사" in selected_items['구분2']:
                if selected_items['구분7']:
                    summary_item = f"{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___{selected_items['구분6']}___ {selected_items['구분7']} | 단어 수: {selected_items['단어_수']})"
                else:
                    summary_item = f"{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___ {selected_items['구분6']} | 단어 수: {selected_items['단어_수']})"
            elif "교과서" in selected_items['구분2']:
                if selected_items['구분7']:
                    summary_item = f"{selected_items['구분1']}_{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___{selected_items['구분6']}___ {selected_items['구분7']} | 단어 수: {selected_items['단어_수']})"
                else:
                    summary_item = f"{selected_items['구분1']}_{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___{selected_items['구분6']} | 단어 수: {selected_items['단어_수']})"
            else :
                summary_item = f"{selected_items['구분3']}_{selected_items['구분4']}_{selected_items['구분5']}___{selected_items['구분6']} | 단어 수: {selected_items['단어_수']})"
            summary_listbox.insert(tk.END, summary_item)
            
        cumulative_word_count = sum(selected_items['단어_수'] for selected_items in selected_items_list)
        cumulative_word_count_var.set(str(cumulative_word_count))
    def prev_on_delete(file_path):
        selected_indices = prev_summary_listbox.curselection()
        if selected_indices:
            for index in sorted(selected_indices, reverse=True): # reverse : 삭제할 때 인덱스가 변하는 문제를 방지함
                # Listbox에서 항목 삭제
                prev_summary_listbox.delete(index)
                # selected_items_list에서 해당 항목 삭제
                prev_selections_df.drop(prev_selections_df.index[index], inplace=True)
            prev_selections_df.reset_index(drop=True, inplace=True)
            prev_selections_df.to_csv(file_path, index=False, encoding='utf-8')
            
    # 윈도우 생성 및 각종 그리드 배치      
    root = tk.Tk()
    root.title("B&Y 단어장 자동제작")
    center_window(root,width=1100,height=670)
    # 프레임 생성 (위젯들을 그룹화하고 패딩을 주기 위함)
    frame = ttk.Frame(root, padding="10")  # ttk는 tk랑 똑같은건데 좀더 세련됐다고 하네 
                                            # frame은 그냥 html의 컨테이너랑 비슷한거라고 보면됨
    frame.grid(row=0, column=0)
    
    
    # '구분1'
    ttk.Label(frame, text= "구분1 :").grid(column=0, row=0)
    category1_listbox = tk.Listbox(frame, width=20, height=12)
    category1_listbox.grid(column= 0, row = 1)
    category1_listbox.bind('<<ListboxSelect>>', on_category1_select)

    # '구분2'
    ttk.Label(frame, text = "구분2: ").grid(column=1, row=0)
    category2_listbox = tk.Listbox(frame, width = 20, height=12)
    category2_listbox.grid(column= 1, row=1)
    category2_listbox.bind('<<ListboxSelect>>', on_category2_select)


    # '구분3'
    ttk.Label(frame, text="구분3:").grid(column=2, row=0,)
    category3_listbox = tk.Listbox(frame, width=20, height=12)
    category3_listbox.grid(column=2, row=1)
    category3_listbox.bind('<<ListboxSelect>>', on_category3_select)
            # widget.bind(event, handler) 구문 : 특정 이벤트가 발생하면 특정 함수를 실행한다.
            # 여기서 <<ListboxSelect>>는 Listbox에서 항목이 선택된 걸 말한다.

    # "구분4" Label
    ttk.Label(frame, text="구분4:").grid(column=3, row=0)  # sticky = 그리드 셀 내에 어느 쪽에 "붙어" 있을지 결정 (E동, W서, S남, N북, 안쓰면 중앙) 
    category4_listbox = tk.Listbox(frame, width=20, height=12)
    category4_listbox.grid(column=3, row=1)
    category4_listbox.bind('<<ListboxSelect>>', on_category4_select)
                
    # "구분5" Label
    ttk.Label(frame, text="구분5:").grid(column=4, row=0, sticky=tk.W)
    category5_listbox = tk.Listbox(frame, width=20, height=12)
    category5_listbox.grid(column=4, row=1)
    category5_listbox.bind('<<ListboxSelect>>', on_category5_select)

    # '구분6' Label
    ttk.Label(frame, text="구분6:").grid(column=5, row=0, sticky=tk.W)
    category6_listbox = tk.Listbox(frame, width=20, height=12, selectmode=tk.EXTENDED)
    category6_listbox.grid(column=5, row=1, sticky=(tk.W, tk.E))
    category6_listbox.bind('<<ListboxSelect>>', on_category6_select)

    # 체크박스 상태를 관리할 변수
    detail_selection_var = tk.BooleanVar()
    detail_selection_checkbox = ttk.Checkbutton(frame, text="세부선택", variable=detail_selection_var, command=on_detail_selection_change)
    detail_selection_checkbox.grid(column=5, row=0, sticky=tk.E)

    ttk.Label(frame, text="구분7:").grid(column=6, row=0)
    category7_listbox = tk.Listbox(frame, width=20, height=12, selectmode=tk.EXTENDED)
    category7_listbox.grid(column=6, row=1, sticky=(tk.W, tk.E))
    category7_listbox.bind('<<ListboxSelect>>', on_category7_select)

    # 라벨에 표시할 텍스트를 관리할 StringVar 생성
    selected_count_var = tk.StringVar(value="선택된 세부단어: 0개\n(Shift와 Ctrl로 다중선택 가능)")                                 
    # 구분7의 선택된 항목 수를 표시할 라벨 생성
    selected_count_label = ttk.Label(frame, textvariable=selected_count_var)
    selected_count_label.grid(column=6, row=2, sticky=((tk.E,tk.N)))
    
    
    # 카테고리 리스트박스들을 관리하기위한 딕셔너리 생성
    category_listboxes = {
        1: category1_listbox,
        2: category2_listbox,
        3: category3_listbox,
        4: category4_listbox,
        5: category5_listbox,
        6: category6_listbox,
        7: category7_listbox,
    }

    # '구분1' Listbox 초기 데이터 로드
    unique_category1s = df['구분1'].unique()
    for i in unique_category1s:
        category1_listbox.insert(tk.END, i)

    # "선택" 버튼 생성
    select_button = ttk.Button(frame, text="선택", command=on_select)
    select_button.grid(column=5, row=2, padx=30, pady=10)

    ttk.Label(frame,text="장바구니 : (여기에 제작할 단어장의 목록을 만드세요)").grid(column=0,row=3,padx = 10,columnspan=4, sticky=tk.W)

    # 선택된 항목 요약을 표시할 Listbox
    summary_listbox = tk.Listbox(frame, width=80, height=8,selectmode=tk.EXTENDED)
    summary_listbox.grid(column=0, row=4, columnspan=4)

    # "삭제" 버튼 생성
    delete_button = ttk.Button(frame, text="삭제", command=on_delete)
    delete_button.grid(column=0, row=5, pady=10, sticky=tk.W)

    # "위로" 버튼 생성
    up_button = ttk.Button(frame, text="위로", width=5 , command=move_up)
    up_button.grid(column=2, row=5, padx=45 , pady=10, sticky=tk.E)

    # "아래로" 버튼 생성
    down_button = ttk.Button(frame, text="아래로",width=5, command=move_down)
    down_button.grid(column=2, row=5, pady=10, sticky=tk.E)


    # "최종선택" 버튼 생성
    final_select_button = ttk.Button(frame, text="최종 선택",  command=on_final_select)
    final_select_button.grid(column=3, row=5, pady=10, sticky=tk.E)

    # 누적 단어 수의 표시
    ttk.Label(frame,text="누적단어수").grid(column=4,row=3, sticky=tk.W)
    cumulative_word_count_var = tk.StringVar(value="0")
    cumulative_word_count_label = ttk.Label(frame, textvariable=cumulative_word_count_var)
    cumulative_word_count_label.grid(column=4, row=4, padx=2, sticky=(tk.W, tk.N))
    
        
    # 과거에 선택되었던 조합들을 표시할 Listbox
    ttk.Label(frame,text="과거 제작기록 : 안쓰는 기록은 삭제하여 관리합시다. 저장된 과거 기록은 필요 시 '불러오기' 사용").grid(column=0,row=7,columnspan=4,padx = 10, sticky=tk.W)
    prev_summary_listbox = tk.Listbox(frame, width=80, height=8, selectmode=tk.EXTENDED)
    prev_summary_listbox.grid(column=0, row=8, columnspan=4)
    
    prev_selections_df = load_previous_selections(r'C:\Users\samsung-user\Documents\code_project\hwp_local\word_book\selections.csv')
    
    delete_button = tk.Button(frame, text="과거기록_삭제", command=lambda: prev_on_delete(r'C:\Users\samsung-user\Documents\code_project\hwp_local\word_book\selections.csv'))
    delete_button.grid(column=0, row=9,padx = 10,sticky=tk.W)
    
    # "불러오기" 버튼 생성
    load_button = ttk.Button(frame, text="불러오기", command=from_prev_to_present_summary)
    load_button.grid(column=3, row=9, pady=10, sticky=tk.E)
    
    # GUI 메인 루프 시작
    root.mainloop()
    root.destroy()  # 창 닫기

    return selected_items_list  # 선택된 항목들 반환

def filter_and_merge_data(df, selected_items_list):
    combined_df = pd.DataFrame()  # 빈 DataFrame 생성

    for selected_items in selected_items_list:
        # 각 selected_items에 대해 DataFrame 필터링
        filtered_df = df[
            (df['구분1'] == selected_items['구분1']) &
            (df['구분2'] == selected_items['구분2']) &
            (df['구분3'] == selected_items['구분3']) &
            (df['구분4'] == selected_items['구분4']) &
            (df['구분5'] == selected_items['구분5']) &
            (df['구분6'].isin(selected_items['구분6']))
        ]
        
        if selected_items['구분7']:
            filtered_df = filtered_df[filtered_df['구분7'].isin(selected_items['구분7'])]
        
        # 필터링된 DataFrame을 combined_df에 추가 (순서대로)
        combined_df = pd.concat([combined_df, filtered_df], ignore_index=True)

    return combined_df
def 한글_텍스트입력(text):
    hwp.HAction.GetDefault("InsertText", hwp.HParameterSet.HInsertText.HSet)
    hwp.HParameterSet.HInsertText.Text = text
    hwp.HAction.Execute("InsertText", hwp.HParameterSet.HInsertText.HSet)
def 한글_이후페이지_삭제():
        hwp.Run("Cancel") 
        hwp.MovePageEnd()
        hwp.Run("Select")
        hwp.MoveDocEnd()
        hwp.Run("Delete")
        if total_blocks % 2 != 0:
            hwp.Run("BreakPage")
    
    
    
    
#####################################
    
    
    
if __name__ == "__main__":
    
    # 단어 DB 엑셀 파일 및 시트 이름
    db_path = r"G:\공유 드라이브\Workspace\[자체 교재]\[0. 교재 제작 Form]\[01] 단어장 제작 form\단어_DB.xlsx"
    db_sheet_name = "단어_DB"
    
    # 메인 타이틀, 서브타이틀 입력값 User에게 받아오기
    cover_title, main_title, sub_title = get_user_titles()
    # cover_title, main_title, sub_title = 1,2,3
    folder_name = f"{main_title}_{sub_title}"
    
    # 필요한 단어 리스트를 User에게 받아서, combined_df 생성
    df = pd.read_excel(db_path, sheet_name=db_sheet_name)# 선택한 시트를 읽어옴
    selected_items_list = select_items(df) # 선택한 시트에서 사용할 구부1,구분4,구분5을 선택함
    combined_df = filter_and_merge_data(df, selected_items_list)
    
    def get_user_batch_size():
        return simpledialog.askinteger("Batch Size", "Day당 들어갈 단어의 개수 : (30, 40, or 50 중 택1):", minvalue=30, maxvalue=50)

    # 사용자로부터 기준 값을 받아오는 부분
    batch_size = get_user_batch_size()
    
     # 단어장 hwp 폼 경로 및 해당 디렉토리
    if batch_size == 50:
        form_path = r"G:\공유 드라이브\Workspace\[자체 교재]\[0. 교재 제작 Form]\[01] 단어장 제작 form\단어_암기장_Form.hwpx"
    else: 
        form_path = r"G:\공유 드라이브\Workspace\[자체 교재]\[0. 교재 제작 Form]\[01] 단어장 제작 form\단어_암기장_Form(30_40v).hwpx"
    
    form_dir = os.path.dirname(form_path)
    
    # 시험답안지 hwp 폼 경로
    answer_form_path = r"G:\공유 드라이브\Workspace\[자체 교재]\[0. 교재 제작 Form]\[01] 단어장 제작 form\단어_시험지_답안_form.hwpx"
    
    # combined_df 항목들 수정(1) : 23년 6월 / 능률(김) 5과 이렇게 합쳐주기
    combined_df['구분'] = combined_df.apply(
        lambda row: f"{row['구분4']} {row['구분5']}" if "교과서" in row['구분2'] else
                    f"{row['구분4']} {row['구분5']}" if "모의고사" in row['구분2'] else 
                    f"{row['구분5']}" if "단어장" in row['구분1'] else 
                    f"{str(row['구분4'])} {str(row['구분5'])}",
        axis=1
    )


    # combined_df 항목들 수정(2) : 구분2의 값이 "모의고사_보강"인 경우 '구분6'의 값을 "주요단어"로 변경
    combined_df.loc[combined_df['구분2'].str.contains("보강"), '구분6'] = "주요단어"

    
    
    # 단어 암기장 form 열어서 타이틀 입력
    hwp = Hwp(visible=False)
    hwp.open(form_path)
    hwp.PutFieldText("표지_제목",cover_title)
    hwp.PutFieldText("메인타이틀",main_title)
    hwp.PutFieldText("서브타이틀",sub_title)
    
    
    # 작업할 행의 수와 블록수(=페이지수)를 계산하고
    total_rows = len(combined_df)
    total_blocks = math.ceil(total_rows / 25)
    
    # df의 데이터를 순서대로 단어암기장에 기입
    for i in range(0, total_blocks):
        # i = 1
        hwp.MoveToField(f"블록{i+1}")
        work_rows = min(25, total_rows - 25*i)

        for j in range(work_rows):
            # j = 2
            row = j + i*25
            한글_텍스트입력(combined_df['구분'].iloc[row])
            hwp.TableRightCell()
            한글_텍스트입력(combined_df['구분6'].iloc[row])
            hwp.TableRightCell()
            한글_텍스트입력(combined_df['단어'].iloc[row])
            hwp.TableRightCell()
            한글_텍스트입력(combined_df['뜻'].iloc[row])
            hwp.TableColBegin()
            hwp.TableLowerCell()
            hwp.TableRightCell()
    
    # 단어장 만들고 필요없는 밑에 페이지 모두 삭제            
    한글_이후페이지_삭제()
    
    # 저장하기
    save_hwp_path = os.path.join(form_dir,folder_name, f"{main_title}_{sub_title}_단어암기장.hwpx")
    hwp.SaveAs(save_hwp_path)
    # range(start, stop, step)
    print("암기장 제작완료") 
    print("학습용, 연습용 MP3 엑셀 생성 시작") 
    
    # MP3 제작용 엑셀을 만들기 위해 '단어'와 '뜻'만 가져옴
    selected_columns = combined_df[['단어','뜻']]
    df_for_excel = selected_columns.copy()
    df_for_excel.insert(0, 'num', range(1, len(combined_df) + 1))
                    # DataFrame.insert(loc, column, value)

    # 전체 단어장 목록을 excel파일로 반환함
    full_words_list_path = os.path.join(form_dir,folder_name, f"{main_title}_{sub_title}_전체 단어장 목록.xlsx")
    df_for_excel.to_excel(full_words_list_path, index=False, header=False)
    
    # 주기화 복습을 위해 day 단위의 df를 저장할 리스트 객체 생성
    day_dataframes = []
    total_days = math.ceil(total_rows / batch_size)
    
    # 학습용, 연습용 MP3 파일 제작용 엑셀파일 생성
    for i in range(total_days): # 총 day 개수만큼 엑셀파일 생성
        # i=1
        start_row = i * batch_size
        end_row = min(start_row + batch_size, total_rows)
        
        # 학습용
        block_df = df_for_excel.iloc[start_row:end_row]
        day_dataframes.append(block_df) # day프레임에 넣어서 주기화복습에서 활용함
        
        # 엑셀 저장 경로 선언
        
        save_excel_path = os.path.join(form_dir,folder_name,"학습+연습_mp3제작용_엑셀", f"{main_title}_{sub_title}_단어_학습용_(day {i+1:02}).xlsx")
        save_excel_path_practice = os.path.join(form_dir,folder_name,"학습+연습_mp3제작용_엑셀", f"{main_title}_{sub_title}_단어_연습용_(day {i+1:02}).xlsx")
        
        # 디렉터리가 없으면 생성
        os.makedirs(os.path.dirname(save_excel_path), exist_ok=True)
        
        # 엑셀로 변환
        block_df.to_excel(save_excel_path, index=False, header=False)
        block_df.to_excel(save_excel_path_practice, index=False, header=False)
    
    print("학습용, 연습용 MP3 엑셀 생성 완료") 
    print("주기화 시험 MP3 엑셀, 답안지 hwp작성 시작") 
    
    # 주기화복습 MP3엑셀 + 답안지hwp 제작
    for day, df_on_date in enumerate(day_dataframes):   
        for i in [1,2,3]:  # 각 1회차,2회차,3회차 3번 반복
            
            if i == 1:
                본_재_재재시험 = "본시험"
            elif i == 2:
                본_재_재재시험 = "재시험"
            elif i == 3:
                본_재_재재시험 = "재재시험"
            
            # day01의 경우    
            if day == 0:
                finished_exam_df = df_on_date.sample(frac=1).reset_index(drop=True)
                day_scope = "1"

            # day02의 경우
            elif day == 1 :
                words_day2_30 = df_on_date.sample(frac=1).reset_index(drop=True).head(30)
                words_day1_20 = day_dataframes[day-1].sample(frac=1).reset_index(drop=True).head(20)
                finished_exam_df = pd.concat([words_day2_30, words_day1_20]).sample(frac=1).reset_index(drop=True)
                day_scope = "1+2"
                
            # day03 이상
            elif day >= 2:
                # day =2
                # df_on_date = block_df
                words_on_date_30 = df_on_date.sample(frac=1).reset_index(drop=True).head(30)
                words_prev_day_10 = day_dataframes[day-1].sample(frac=1).reset_index(drop=True).head(10)
                words_prev_prev_10 = day_dataframes[day-2].sample(frac=1).reset_index(drop=True).head(10)
                finished_exam_df = pd.concat([words_on_date_30,words_prev_day_10,words_prev_prev_10])
                day_scope = f"{day-1}+{day}+{day+1}"
            
            finished_exam_df['num'] = range(1, len(finished_exam_df) + 1)
            
            # 엑셀파일로 제작
            save_excel_path_exam = os.path.join(form_dir,folder_name,"주기화시험_MP3제작용_엑셀", f"{main_title}_{sub_title}_시험용_(day {day+1:02})_{i}회.xlsx")
            os.makedirs(os.path.dirname(save_excel_path_exam), exist_ok=True)
            finished_exam_df.to_excel(save_excel_path_exam, index= False, header=False)
            
            
            ## 답안지hwp 제작
            hwp.open(answer_form_path)
            hwp.put_field_text("day_scope",f"{day_scope}")
            hwp.put_field_text("exam_title",f"{main_title}_{본_재_재재시험}")

            blocks_count = 1 if len(finished_exam_df) <= 25 else 2
            
            # 표에 단어&뜻 입력
            for j in range(0, blocks_count):
                # j = 1    
                hwp.MoveToField(f"블록{j+1}")
                work_rows = min(25, len(finished_exam_df) - 25*j)

                for k in range(work_rows):
                    # k = 2
                    row = k + 25*j
                    한글_텍스트입력(finished_exam_df['단어'].iloc[row])
                    hwp.TableRightCell()
                    한글_텍스트입력(finished_exam_df['뜻'].iloc[row])
                    hwp.TableLowerCell()
                    hwp.TableLeftCell()
                
            # 저장
            save_hwp_exam_path = os.path.join(form_dir,folder_name,"시험지 답안", f"{main_title}_{sub_title}_day {day+1:02}_{i}회_답안지.hwpx")
            hwp.SaveAs(save_hwp_exam_path)
            
            save_hwp_writing_answer_path = os.path.join(form_dir,folder_name,"쓰기시험", f"쓰기_{main_title}_{sub_title}_day {day+1:02}_{i}회_시험지.hwpx")
            
            
            hwp.put_field_text("시험지or답안지","뜻 쓰기")
            hwp.MoveToField(f"블록1")
            hwp.TableRightCell()
            hwp.TableCellBlockCol()
            hwp.TableDeleteCell(remain_cell=True)
            hwp.Run("Cancel")
            hwp.TableRightCell()
            hwp.TableRightCell()
            hwp.TableRightCell()
            hwp.TableCellBlockCol()
            hwp.TableDeleteCell(remain_cell=True) #테이블 셀을 지워도, 내용은 남아있게함
            
            hwp.SaveAs(save_hwp_writing_answer_path)
            # hwp = Hwp()
            
            
        # 주기화복습 MP3엑셀 + 답안지hwp 제작
    if len(day_dataframes) >= 4:
        for d in [1,2]:  
            for i in [1,2,3]:  # 각 1회차,2회차,3회차 3번 반복
                if i == 1:
                    본_재_재재시험 = "본시험"
                elif i == 2:
                    본_재_재재시험 = "재시험"
                elif i == 3:
                    본_재_재재시험 = "재재시험"
                
                # ex. day 9+10+1 인 경우
                if d == 1 :
                    words_first_30 = day_dataframes[0].sample(frac=1).reset_index(drop=True).head(30)
                    words_last_10 = day_dataframes[len(day_dataframes)-1].sample(frac=1).reset_index(drop=True).head(10)
                    words_last_second_10 = day_dataframes[len(day_dataframes)-2].sample(frac=1).reset_index(drop=True).head(10)
                    finished_exam_df = pd.concat([words_first_30,words_last_10,words_last_second_10])
                    day_scope = f"{len(day_dataframes)-1}+{len(day_dataframes)}+1"
                    
                # ex. day 9+10+1 인 경우
                if d == 2 :
                    words_second_30 = day_dataframes[1].sample(frac=1).reset_index(drop=True).head(30)
                    words_first_10 = day_dataframes[0].sample(frac=1).reset_index(drop=True).head(10)
                    words_last_10 = day_dataframes[len(day_dataframes)-1].sample(frac=1).reset_index(drop=True).head(10)
                    
                    finished_exam_df = pd.concat([words_second_30,words_first_10,words_last_10])
                    day_scope = f"{len(day_dataframes)}+1+2"
                
                finished_exam_df['num'] = range(1, len(finished_exam_df) + 1)
                
                # 엑셀파일로 제작
                save_excel_path_exam = os.path.join(form_dir,folder_name,"주기화시험_MP3제작용_엑셀", f"2회전_{main_title}_{sub_title}_시험용_(day {d:02})_{i}회.xlsx")
                os.makedirs(os.path.dirname(save_excel_path_exam), exist_ok=True)
                finished_exam_df.to_excel(save_excel_path_exam, index= False, header=False)
                
                
                ## 답안지hwp 제작
                hwp.open(answer_form_path)
                hwp.put_field_text("day_scope",f"{day_scope}")
                hwp.put_field_text("exam_title",f"{main_title}_{본_재_재재시험}")

                blocks_count = 1 if len(finished_exam_df) <= 25 else 2
                
                # 표에 단어&뜻 입력
                for j in range(0, blocks_count):
                    # j = 1    
                    hwp.MoveToField(f"블록{j+1}")
                    work_rows = min(25, len(finished_exam_df) - 25*j)

                    for k in range(work_rows):
                        # k = 2
                        row = k + 25*j
                        한글_텍스트입력(finished_exam_df['단어'].iloc[row])
                        hwp.TableRightCell()
                        한글_텍스트입력(finished_exam_df['뜻'].iloc[row])
                        hwp.TableLowerCell()
                        hwp.TableLeftCell()
                    
                # 저장
                save_hwp_exam_path = os.path.join(form_dir,folder_name,"시험지 답안", f"2회전_{main_title}_{sub_title}_day {d:02}_{i}회_답안지.hwpx")
                hwp.SaveAs(save_hwp_exam_path)
                
                save_hwp_writing_answer_path = os.path.join(form_dir,folder_name,"쓰기시험", f"2회전_쓰기_{main_title}_{sub_title}_day {d:02}_{i}회_시험지.hwpx")
                
                hwp.put_field_text("시험지or답안지","뜻 쓰기")
                hwp.MoveToField(f"블록1")
                hwp.TableRightCell()
                hwp.TableCellBlockCol()
                hwp.TableDeleteCell(remain_cell=True)
                hwp.Run("Cancel")
                hwp.TableRightCell()
                hwp.TableRightCell()
                hwp.TableRightCell()
                hwp.TableCellBlockCol()
                hwp.TableDeleteCell(remain_cell=True) #테이블 셀을 지워도, 내용은 남아있게함
                
                hwp.SaveAs(save_hwp_writing_answer_path)
                # hwp = Hwp()
            
            
    hwp.quit()
    print("모든 작업이 완료되었습니다.")


        
            
            
            
        
        
            
            
            
            
            
            
        

    


