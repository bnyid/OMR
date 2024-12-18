

passage_dict_list = []

passage_dict = {
    'passage_number': 1,
    'passage_serial':   1,
    'passage_source': "교과서 4과 프린트",
    'is_double_question': False,
    'passage_text': "본문",
    'passage_table': {'title : "표타입",
                    'content' : "표내용"
                    },
    'question_dict_list': []
}

question_dict = {
    'question_number': 1,
    'question_serial': 1,
    'question_type': "객관식",
    'is_essay' : False,
    'question_text': "문제내용",
    'question_table': {'title' : "표타입",
                    'content' : "표내용"
                    },
    'question_answer': "정답",
    'choices' : { 1 : "보기1", 
                    2 : "보기2", 
                    3 : "보기3", 
                    4 : "보기4", 
                    5 : "보기5" 
                },
    'explanation' : "해설",
    'answer_format' : "정답포맷"}
}






#
#
#
#
## 시험지 출제 규칙
## (1) 모든 문제유형을 막론하고 가장 상단에는 #이 위치한다. 만약 2개짜리 문제라면 ## 으로 두개 표시한다.
## (2) 한개짜리 문제는 #인덱스 -> 발문 -> 지문 -> 보기 의 순서로 구성한다.
## (3) 두개짜리 문제는 #인덱스 -> [3,4] 다음글을 읽고 물음에 답하시오 -> 지문 -> 발문1 -> 보기1 -> 발문2 -> 보기2로 구성한다.
## (4) 객관식 문제는 반드시 미주로 정답을 표시해야 하며, 미주의 가장 첫번째에 오는 문자가 정답을 나타내야 한다.
## (6) 지문의 중간에 보기가 있어서는 안된다. 원문자 1,2,3,4,5는 반드시 지문다 끝난 뒤에 와야한다. 지문 내에서 원문자가 필요할경우 알파벳 원문자나 한글 원문자를 사용한다.
## (7) 보기의 원문자는 반드시 정해진 원문자를 사용해야 한다.
## (8) 빈칸을 만들 때는, 폰트를 하얀색으로 바꾸는 것이 아니라 언더바를 사용해야한다 ex. it seems __________.
## (9) 논술형의 답안 작성란에는 반드시 [답안] 이라는 문자열이 있어야 한다.