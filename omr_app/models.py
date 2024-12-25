# models.py
from django.db import models
import re

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
    text_source = models.CharField('원문 출처', max_length=200, null=True, blank=True)
    
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


class Passage(models.Model):
    """
    한 지문(Passage)을 저장하는 모델
    - passage_source: 지문 출처(예: '수능 2023년 6월', '고2 2022년 7월 34번' 등)
    - passage_text: 지문 본문(HTML 또는 일반 텍스트)
    - passage_table: 지문 내에 포함된 표(HTML). 여러 개면 <hr>로 구분하거나, JSON으로 저장해도 됨
    - created_at, updated_at: 생성/수정 시각
    """
    passage_source = models.CharField('지문출처', max_length=200, null=True, blank=True,
                                      help_text="원본을 명시하고 싶을 경우.")
    passage_text = models.TextField('지문 내용', blank=True, null=True)
    passage_table = models.TextField('지문 표(HTML)', blank=True, null=True)

    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    def __str__(self):
        return f"Passage #{self.id} - {self.passage_source or ''}"



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

    passage = models.ForeignKey(
        Passage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='questions',
        verbose_name='연결된 지문'
    )
    
    category = models.CharField('구분', max_length=10, choices=CATEGORY_CHOICES, null=True, blank=True)
    evaluation_area = models.CharField('평가영역', max_length=20, choices=EVALUATION_AREA_CHOICES, null=True, blank=True)
    detail_type = models.CharField('상세유형', max_length=20, choices=DETAIL_TYPE_CHOICES, null=True, blank=True)
    answer_format = models.CharField('답안형식', max_length=2, choices=ANSWER_FORMAT_CHOICES, default='MC')
    
    
    answer = models.CharField('정답', max_length=100)
    explanation = models.TextField('해설')
    
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    question_text = models.TextField('발문', default='')
    
    
    
    class Meta:
        verbose_name = '문제'
        verbose_name_plural = '문제들'

    def save(self, *args, **kwargs):
        # serial_number가 없는 경우에만 생성
        if not self.serial_number:
            self.serial_number = self.generate_serial_number()

        # 2. detail_type 기반 category/evaluation_area 매핑
        if self.detail_type:
            self.category = self.CATEGORY_MAPPING.get(self.detail_type)
            self.evaluation_area = self.EVALUATION_MAPPING.get(self.detail_type)
            
        super().save(*args, **kwargs)

    @classmethod
    def generate_serial_number(cls):
        """
        AA0001부터 ZZ9999까지 순차적으로 증가하는 serial number를 생성
        """
        # 가장 최근 serial number 조회
        last_question = cls.objects.order_by('-serial_number').first()
        
        if not last_question or not last_question.serial_number:
            return 'AA0001'  # 첫 번째 serial number
            
        current_serial = last_question.serial_number
        
        # 알파벳 부분과 숫자 부분 분리
        alpha_part = current_serial[:2]
        num_part = int(current_serial[2:])
        
        # 숫자가 9999에 도달했는지 확인
        if num_part >= 9999:
            # 알파벳 증가
            if alpha_part == 'ZZ':  # 최대값 도달
                raise ValueError("더 이상 사용 가능한 serial number가 없습니다.")
                
            # 다음 알파벳 조합 생성
            first_char = alpha_part[0]
            second_char = alpha_part[1]
            
            if second_char == 'Z':
                first_char = chr(ord(first_char) + 1)
                second_char = 'A'
            else:
                second_char = chr(ord(second_char) + 1)
                
            alpha_part = first_char + second_char
            num_part = 1
        else:
            num_part += 1
            
        return f"{alpha_part}{str(num_part).zfill(4)}"



# 문제에 딸린 표 모델
class QuestionTable(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='tables')
    content = models.TextField('표 내용')
    order = models.IntegerField('순서', default=1)
    
    class Meta:
        verbose_name = '문제 테이블'
        verbose_name_plural = '문제 테이블들'
        ordering = ['order']
        
# 보기 모델 (Choice 모델과 Question 모델 1:1 관계)
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_number = models.IntegerField('보기 번호')  # 1, 2, 3, 4, 5
    text_content = models.TextField('텍스트 내용')
    
    class Meta:
        verbose_name = '보기'
        verbose_name_plural = '보기들'
        ordering = ['choice_number']
        unique_together = ['question', 'choice_number']


## 주관식 답안 작성란
class AnswerField(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answer_fields')
    text_format = models.TextField('작성란 형식')  # ex: "______", "(A): __________"
    
    class Meta:
        verbose_name = '답안 작성란'
        verbose_name_plural = '답안 작성란들'





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
    
    
class PassageTable(models.Model):
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, related_name='tables')
    table_group = models.IntegerField('테이블 그룹', default=1)  # passage 밑의 테이블 순서
    content = models.TextField('표 내용')
    
    class Meta:
        verbose_name = '지문 테이블'
        verbose_name_plural = '지문 테이블들'
        ordering = ['table_group']
    
    