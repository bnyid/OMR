# models.py
from django.db import models

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
    
    id = models.AutoField(primary_key=True)
    student_code = models.CharField('학번', max_length=8, null=True, blank=True, unique=True)
    registration_number = models.CharField('등록번호', max_length=11, null=True, blank=True)
    registered_date = models.DateField(null=True, blank=True)
    name = models.CharField('이름', max_length=10)
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


## 원문 모델 ##
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
    QUESTION_TYPES = [
        ('SO', '순서배열'),
        ('SI', '문장삽입'),
        ('BL', '빈칸추론'),
        ('IM', '함축의미'),
        ('SU', '요약'),
        ('VO', '문맥어휘'),
        ('TH', '주제'),
        ('TI', '제목'),
        # 다른 유형들 추가 가능
    ]
    ANSWER_FORMAT_CHOICES = [
        ('MC', '객관식'),  # Multiple Choice
        ('SA', '주관식'),  # Short Answer
    ]
    
    serial_number = models.CharField('일련번호', max_length=20, unique=True)
    exam_sheets = models.ManyToManyField(
        ExamSheet, 
        through='ExamSheetQuestionMapping',
        related_name='questions'
    )
    
    # 원문 연결 (교과서/모의고사/외부지문)
    original_text = models.ForeignKey(OriginalText, on_delete=models.PROTECT, verbose_name='원문')
    
    type = models.CharField('유형', max_length=2, choices=QUESTION_TYPES)
    answer_format = models.CharField('답안형식', max_length=2, choices=ANSWER_FORMAT_CHOICES, default='MC')
    content = models.TextField('본문')
    
    # 보기 객관식인 경우에만 사용
    choice_1 = models.CharField('보기1', max_length=200, null=True, blank=True)
    choice_2 = models.CharField('보기2', max_length=200, null=True, blank=True)
    choice_3 = models.CharField('보기3', max_length=200, null=True, blank=True)
    choice_4 = models.CharField('보기4', max_length=200, null=True, blank=True)
    choice_5 = models.CharField('보기5', max_length=200, null=True, blank=True)
    
    answer = models.CharField('정답', max_length=100)
    explanation = models.TextField('해설')
    
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    
    class Meta:
        verbose_name = '문제'
        verbose_name_plural = '문제들'

# 주제
class ThemeQuestion(Question):
    question_text = models.TextField('발문')
    
    class Meta:
        verbose_name = '주제 문제'
        verbose_name_plural = '주제 문제들'

# 제목
class TitleQuestion(Question):
    question_text = models.TextField('발문')
    
    class Meta:
        verbose_name = '제목 문제'
        verbose_name_plural = '제목 문제들'


# 순서배열
class SequenceOrderQuestion(Question):
    question_text = models.TextField('발문')
    text_a = models.TextField('본문A')
    text_b = models.TextField('본문B')
    text_c = models.TextField('본문C')
    
    class Meta:
        verbose_name = '순서배열 문제'
        verbose_name_plural = '순서배열 문제들'

# 문장삽입
class SentenceInsertQuestion(Question):
    question_text = models.TextField('발문')
    insert_sentence = models.TextField('삽입 문장')
    first_sentence = models.TextField('첫 문장')
    sentence_1 = models.TextField('1번 뒤 문장')
    sentence_2 = models.TextField('2번 뒤 문장')
    sentence_3 = models.TextField('3번 뒤 문장')
    sentence_4 = models.TextField('4번 뒤 문장')
    sentence_5 = models.TextField('5번 뒤 문장')
    
    class Meta:
        verbose_name = '문장삽입 문제'
        verbose_name_plural = '문장삽입 문제들'

# 빈칸추론
class BlankInferenceQuestion(Question):
    question_text = models.TextField('발문')
    blank_text = models.TextField('빈칸 본문')
    
    class Meta:
        verbose_name = '빈칸추론 문제'
        verbose_name_plural = '빈칸추론 문제들'

# 함축의미
class ImpliedMeaningQuestion(Question):
    question_text = models.TextField('발문')
    underlined_sentence = models.TextField('밑줄 문장')
    
    class Meta:
        verbose_name = '함축의미 문제'
        verbose_name_plural = '함축의미 문제들'
        

# 요약
class SummaryQuestion(Question):
    question_text = models.TextField('발문')
    summary_text = models.TextField('요약문')
    
    class Meta:
        verbose_name = '요약 문제'
        verbose_name_plural = '요약 문제들'

# 문맥어휘
class VocaInContextQuestion(Question):
    question_text = models.TextField('발문')
    
    class Meta:
        verbose_name = '문맥어휘 문제'
        verbose_name_plural = '문맥어휘 문제들'

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
    exam_identifier = models.CharField('시험식별자', max_length=8, null=True, blank=True)  
    # exam_date와 teacher_code 결합 후 save()에서 자동 설정할 수 있음
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    is_matched = models.BooleanField('매칭 여부', default=False)
    unmatched_student_code = models.CharField('미매칭 학생코드', max_length=8, null=True, blank=True)
    unmatched_student_name = models.CharField('미매칭 학생이름', max_length=10, null=True, blank=True)
    
    answer_sheet = models.ImageField('답안지', upload_to='answer_sheets/')
    processed_sheet = models.ImageField('처리된 답안지', upload_to='processed_sheets/', null=True, blank=True)
    answers = models.JSONField('답안 결과')
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    
    temp_exam_name = models.CharField('임시 시험명', max_length=50, null=True, blank=True)
    
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
    
    
    