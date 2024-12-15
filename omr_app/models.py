# models.py
from django.db import models


### 학생 모델 관련

class Student(models.Model):
    SCHOOL_TYPE_CHOICES = [
        ('M', '중학교'),
        ('H', '고등학교'),
    ]
    GRADE_CHOICES = [
        (1, '1학년'),
        (2, '2학년'),
        (3, '3학년'),
    ]
    
    # 재원 상태 필드
    STATUS_CHOICES = [
        ('enrolled', '재원'),  # 현재 재원 중인 학생
        ('leave', '휴원'),    # 일시적 휴원
        ('dropout', '퇴원'),  # 완전히 그만둔 경우
        ('graduated', '졸업') # 졸업한 경우
    ]
    
    id = models.AutoField(primary_key=True)
    status = models.CharField('재원 상태', max_length=10, choices=STATUS_CHOICES, default='enrolled')  
    status_changed_date = models.DateField('상태변경일', null=True, blank=True)  # 신규 필드
    status_reason = models.TextField('상태변경사유', null=True, blank=True)  # 신규 추가 필드


    student_code = models.CharField('학번', max_length=8, null=True, blank=True, unique=True)
    registration_number = models.CharField('등록번호', max_length=11, null=True, blank=True)
    registered_date = models.DateField(null=True, blank=True)
    name = models.CharField('이름', max_length=10)
    
    class_name_by_school = models.CharField('내신반', max_length=50, null=True, blank=True)
    class_name = models.CharField('소속반', max_length=20, null=True, blank=True)

    school_type = models.CharField('중/고등 구분', max_length=1, choices=SCHOOL_TYPE_CHOICES, null=True, blank=True)
    school_name = models.CharField('학교명', max_length=30, null=True, blank=True)
    grade = models.IntegerField('학년', choices=GRADE_CHOICES, null=True, blank=True)
    phone_number = models.CharField('본인 연락처', max_length=11, null=True, blank=True)
    parent_phone = models.CharField('보호자 연락처', max_length=11, null=True, blank=True)
    note = models.TextField('비고', blank=True, null=True)
    
    class Meta:
        verbose_name = '학생'
        verbose_name_plural = '학생들'
        
    @classmethod
    def generate_registration_number(cls, reg_date, exclude_id=None):
        """
        Model 내부에서 사용하기 위한 등록번호 생성 메서드.
        """
        students = cls.objects.filter(registered_date=reg_date)
        if exclude_id:
            students = students.exclude(id=exclude_id)

        date_str = reg_date.strftime("%y%m%d")  # datetime.date 객체를 YYMMDD 포맷 문자열로 변환

        existing_numbers = [] # 이미 등록번호가 존재하는 학생들의 해당일자 등록번호 중 뒷자리 숫자들(_XX 에서 XX) 모아놓은 리스트
        for s in students:
            if s.registration_number and '_' in s.registration_number:
                num_str = s.registration_number.split('_')[1]
                try:
                    existing_numbers.append(int(num_str))
                except ValueError:
                    pass

        if existing_numbers: # 존재하는 등록번호중 최대값을 구하고 +1을 해서 다음 등록번호를 생성
            max_num = max(existing_numbers)
            next_num = max_num + 1
        else:
            next_num = 1

        return f"{date_str}_{str(next_num).zfill(2)}"
        
        
    def save(self, *args, **kwargs):
        # detail_type이 있을 경우 자동으로 category와 evaluation_area 설정
        if self.detail_type:
            # CATEGORY_MAPPING과 EVALUATION_MAPPING에서 해당 detail_type에 대한 값을 가져옴
            # 매핑에 없는 경우 빈 문자열('') 대신 None을 반환하도록 수정
            self.category = self.CATEGORY_MAPPING.get(self.detail_type)
            self.evaluation_area = self.EVALUATION_MAPPING.get(self.detail_type)
            
            # 매핑된 값이 없는 경우를 위한 예외처리
            if self.category is None:
                raise ValueError(f"Invalid detail_type: {self.detail_type}. No matching category found.")
            if self.evaluation_area is None:
                raise ValueError(f"Invalid detail_type: {self.detail_type}. No matching evaluation_area found.")
                
        super().save(*args, **kwargs)   
        
    def __str__(self):
        return f"[{self.id} {self.student_code}] {self.name} ({self.class_name})"



## 시험지 모델 ##
class ExamSheet(models.Model):
    serial_number = models.CharField('일련번호', max_length=20, unique=True)
    exam_date = models.DateField('시행일')
    title = models.CharField('시험명', max_length=100)
    total_questions = models.IntegerField('총 문항수')
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    
    class Meta:
        verbose_name = '시험지'
        verbose_name_plural = '시험지들'


### 원문 모델 ##
class OriginalText(models.Model):
    TEXT_TYPE_CHOICES = [
        ('TB', '교과서'),
        ('ET', '모의고사'),
        ('EX', '외부지문'),
    ]
    
    text_type = models.CharField('원문 유형', max_length=2, choices=TEXT_TYPE_CHOICES)
    content = models.TextField('본문')
    
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    
    class Meta:
        verbose_name = '지문 원문'
        verbose_name_plural = '지문 원문들'

class TextbookText(OriginalText):
    subject = models.CharField('과목', max_length=50)
    publisher = models.CharField('출판사', max_length=100)
    chapter = models.CharField('과', max_length=50)
    text_number = models.CharField('본문번호', max_length=50)

class ExamText(OriginalText):
    grade = models.IntegerField('학년')
    year = models.IntegerField('년도')
    month = models.IntegerField('시행월')
    question_number = models.IntegerField('문항번호')

class ExternalText(OriginalText):
    category1 = models.CharField('구분1', max_length=100)
    category2 = models.CharField('구분2', max_length=100)


## 문제 모델 ##
class Question(models.Model):
    
    CATEGORY_CHOICES = [
        ('단어', '단어'),
        ('어법', '어법'),
        ('독해', '독해'),
        ('복합', '복합'),
    ]
    
    EVALUATION_AREA_CHOICES = [
        ('단어', '단어'),
        ('어법', '어법'),
        ('글의_흐름_파악', '글의 흐름 파악'),
        ('핵심_내용', '핵심 내용'),
        ('논리적_추론', '논리적 추론'),
        ('어휘', '어휘')
    ]
    
    DETAIL_TYPE_CHOICES = [
        ('객관식_어법', '객관식 어법'),
        ('논술형_어법', '논술형 어법'),
        
        ('순서배열', '순서배열'),
        ('문장삽입', '문장삽입'),
        
        ('제목', '제목'),
        ('주제', '주제'),
        ('요약문', '요약문'),
        
        ('빈칸추론', '빈칸추론'),
        ('함축의미', '함축의미'),
        
        ('문맥어휘', '문맥어휘'),
        ('영영풀이', '영영풀이')
    ]
    
     # HWP 키워드와 detail_type 매핑
    HWP_MAPPING_TO_DETAIL_TYPE = {
        '어법': '객관식_어법',
        '논술형(어법)': '논술형_어법',
        
        '순서': '순서배열',
        '삽입': '문장삽입',

        '제목': '제목',
        '주제': '주제',
        '요약': '요약문',
        
        '빈칸': '빈칸추론',
        '함축': '함축의미',

        '문맥': '문맥어휘',
        '영영풀이': '영영풀이',
    }
    
    # detail_type에 따른 evaluation_area 매핑
    EVALUATION_MAPPING = {
        '객관식_어법': '어법',
        '논술형_어법': '어법',
        '순서배열': '글의_흐름_파악',
        '문장삽입': '글의_흐름_파악',
        '제목': '핵심_내용',
        '주제': '핵심_내용',
        '요약문': '핵심_내용',
        '빈칸추론': '논리적_추론',
        '함축의미': '논리적_추론',
        '문맥어휘': '어휘',
        '영영풀이': '어휘'
    }
    
    
     # detail_type에 따른 category 매핑
    CATEGORY_MAPPING = {
        '객관식_어법': '어법',
        '논술형_어법': '어법',
        '순서배열': '독해',
        '문장삽입': '독해',
        '제목': '독해',
        '주제': '독해',
        '요약문': '독해',
        '빈칸추론': '독해',
        '함축의미': '독해',
        '문맥어휘': '독해',
        '영영풀이': '독해'
    }

    
    
    ANSWER_FORMAT_CHOICES = [
        ('MC', '객관식'),  # Multiple Choice
        ('SA', '논술형'),  # Short Answer
    ]
    
    serial_number = models.CharField('일련번호', max_length=20, unique=True)
    exam_sheets = models.ManyToManyField(
        ExamSheet, 
        through='ExamSheetQuestionMapping',
        related_name='questions'
    )
    
    # 원문 연결 (교과서/모의고사/외부지문)
    original_text = models.ForeignKey(OriginalText, on_delete=models.PROTECT, verbose_name='원문')
    
    category = models.CharField('구분', max_length=10, choices=CATEGORY_CHOICES, null=True, blank=True)
    evaluation_area = models.CharField('평가영역', max_length=20, choices=EVALUATION_AREA_CHOICES, null=True, blank=True)
    detail_type_1 = models.CharField('상세유형1', max_length=20, choices=DETAIL_TYPE_CHOICES, null=True, blank=True)
    detail_type_2 = models.CharField('상세유형2', max_length=20, choices=DETAIL_TYPE_CHOICES, null=True, blank=True)
    answer_format = models.CharField('답안형식', max_length=2, choices=ANSWER_FORMAT_CHOICES, default='MC')
    content = models.TextField('본문')
    
    
    answer = models.CharField('정답', max_length=100)
    explanation = models.TextField('해설')
    
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    
    
    is_double_question = models.BooleanField('2문제 여부', default=False)
    double_question_label = models.CharField('지문 라벨', max_length=100, null=True, blank=True, help_text='예: 다음 글을 읽고 물음에 답하시오.')

    question_text_1 = models.TextField('발문1', default='')
    question_text_2 = models.TextField('발문2', null=True, blank=True)
    
    
    
    class Meta:
        verbose_name = '문제'
        verbose_name_plural = '문제들'

    def save(self, *args, **kwargs):
        # detail_type_1은 필수값이므로 항상 처리
        self.category = self.CATEGORY_MAPPING.get(self.detail_type_1)
        self.evaluation_area = self.EVALUATION_MAPPING.get(self.detail_type_1)
        
        # detail_type_2가 있는 경우 (2문제 문항)
        if self.detail_type_2:
            # 두 문제의 카테고리가 다른 경우 '복합'으로 처리
            if self.CATEGORY_MAPPING.get(self.detail_type_2) != self.category:
                self.category = '복합'
            
            # 평가영역도 다른 경우 '복합'으로 처리
            if self.EVALUATION_MAPPING.get(self.detail_type_2) != self.evaluation_area:
                self.evaluation_area = '복합'


# 보기 모델 (Choice 모델과 Question 모델 1:1 관계)



class QuestionTable(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='tables')
    table_group = models.IntegerField('테이블 그룹', default=1)  # 발문1 또는 발문2에 대한 테이블
    
    table_type = models.CharField('표 유형', max_length=10, choices=[
        ('CONDITION', '조건'),
        ('EXAMPLE', '보기'),
        ('SUMMARY', '요약문')
    ])
    content = models.TextField('표 내용')

    
    class Meta:
        verbose_name = '문제 테이블'
        verbose_name_plural = '문제 테이블들'
        ordering = ['table_group', 'table_type']
        

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_group = models.IntegerField('보기 그룹', default=1)  # 발문1 또는 발문2에 대한 보기
    choice_number = models.IntegerField('보기 번호')  # 1, 2, 3, 4, 5
    text_content = models.TextField('텍스트 내용')
    
    class Meta:
        verbose_name = '보기'
        verbose_name_plural = '보기들'
        ordering = ['choice_group', 'choice_number']
        unique_together = ['question', 'choice_group', 'choice_number']


## 주관식 답안 작성란
class AnswerField(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answer_fields')
    field_group = models.IntegerField('작성란 그룹', default=1)  # 발문1 또는 발문2에 대한 작성란
    text_format = models.TextField('작성란 형식')  # ex: "______", "(A): __________"
    
    class Meta:
        verbose_name = '답안 작성란'
        verbose_name_plural = '답안 작성란들'
        ordering = ['field_group', 'id']





# 시험지와 문제 매핑 모델
class ExamSheetQuestionMapping(models.Model):
    exam_sheet = models.ForeignKey(ExamSheet, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    question_number = models.IntegerField('문항번호')
    
    class Meta:
        verbose_name = '시험지-문제 매핑'
        verbose_name_plural = '시험지-문제 매핑들'
        unique_together = ['exam_sheet', 'question_number']  # 같은 시험지 내에서 문항번호 중복 방지
        
        
        
        
## OMR 결과 모델 ##
class OMRResult(models.Model):
    exam_date = models.DateField('시험 날짜')
    teacher_code = models.CharField('강사코드', max_length=2)  # '01', '02', ... 형태로 저장
    exam_identifier = models.CharField('시험식별자', max_length=8, null=True, blank=True)  # exam_date와 teacher_code 결합 후 save()에서 자동 설정
    exam_sheet = models.ForeignKey('ExamSheet', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='omr_results',
        verbose_name='시험지'
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    is_matched = models.BooleanField('매칭 여부', default=False)
    unmatched_student_code = models.CharField('미매칭 학생코드', max_length=8, null=True, blank=True)
    unmatched_student_name = models.CharField('미매칭 학생이름', max_length=10, null=True, blank=True)
    
    answer_sheet = models.ImageField('답안지', upload_to='answer_sheets/')
    processed_sheet = models.ImageField('처리된 답안지', upload_to='processed_sheets/', null=True, blank=True)
    answers = models.JSONField('답안 결과')
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    
    class_name = models.CharField('반이름', max_length=20, null=True, blank=True)
    omr_name = models.CharField('OMR 이름', max_length=50, default='', blank=True)
    
    class Meta:
        verbose_name = 'OMR 결과'
        verbose_name_plural = 'OMR 결과들'

    def save(self, *args, **kwargs):
        # exam_date는 YYYY-MM-DD 형태, 여기서 YYMMDD로 변환 필요
        y = str(self.exam_date.year)[2:].zfill(2)
        m = str(self.exam_date.month).zfill(2)
        d = str(self.exam_date.day).zfill(2)
        # exam_order는 이미 '01', '02' 이런 식으로 저장한다고 가정
        self.exam_identifier = f"{y}{m}{d}{self.teacher_code}"
        super().save(*args, **kwargs)

    def __str__(self):
        # student_name은 student가 있으면 student.name, 없으면 unmatched_student_name 사용(것도 없으면 미매칭)
        name = self.student.name if self.student else (self.unmatched_student_name or "미매칭")
        return f"{self.exam_identifier} - {name}"
    
    