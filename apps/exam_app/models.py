from django.db import models
from django.core.exceptions import ValidationError


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
    - created_at, updated_at: 생성/수정 시각
    """
    passage_serial = models.CharField('지문 일련번호', max_length=20, unique=True, blank=True, null=True)
    passage_source = models.CharField('지문출처', max_length=200, null=True, blank=True, help_text="원본을 명시하고 싶을 경우.")
    passage_text = models.TextField('지문 내용', blank=True, null=True)

    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    @classmethod
    def generate_serial_number(cls):
        """
        AA0001부터 ZZ9999까지 순차적으로 증가하는 serial number를 생성
        
        Raises:
            ValueError: 시리얼 번호 생성 중 오류가 발생한 경우
        """
        last_passage = cls.objects.order_by('-passage_serial').first()
        if not last_passage or not last_passage.passage_serial:
           # 첫 번째 serial number
           return 'AA0001'
       
        last_serial = last_passage.passage_serial
        alpha_part = last_serial[:2] # 알파벳 부분
        num_part_str = last_serial[2:] # 숫자 부분
        
        try:
            num_part = int(num_part_str)
        except ValueError:
            raise ValidationError("시험지에 잘못된 형식의 시리얼 번호가 있습니다.")

        # 숫자가 9999에 도달했다면
        if num_part >= 9999:
            if alpha_part == 'ZZ':  # 최대값 도달
                raise ValueError("더 이상 사용 가능한 serial number가 없습니다.")
            
            # 다음 알파벳 조합 생성
            first_char = alpha_part[0] # 첫번째 알파벳
            second_char = alpha_part[1] # 두번째 알파벳
            if second_char == 'Z': # 두번째 알파벳이 Z이면
                first_char = chr(ord(first_char) + 1) # 첫번째 알파벳 증가
                second_char = 'A'
            else:
                second_char = chr(ord(second_char) + 1) # 두번째 알파벳 증가
            alpha_part = first_char + second_char # 알파벳 조합 생성
            num_part = 1 # 숫자 부분 초기화
        # 숫자가 9999에 도달하지 않았다면
        else:
            num_part += 1 # 숫자 부분 증가
        
        serial_number = f"{alpha_part}{str(num_part).zfill(4)}" # 알파벳 조합과 숫자 부분을 결합하여 반환
        return serial_number

    def save(self, *args, **kwargs):
        if not self.passage_serial:
            self.passage_serial = self.generate_serial_number()
        super().save(*args, **kwargs)

    def __str__(self):
        # 일련번호도 표시
        return f"Passage #{self.id} - {self.passage_serial or ''} ({self.passage_source or ''})"



## 문제 모델 ##
class Question(models.Model):

    # 영역 CHOICES        
    CATEGORY_CHOICES = [
        '단어',
        '어법',
        '독해',
        '논술형',
    ]
    EVALUATION_AREA_CHOICES = [
        '어법 이해',
        '글의_흐름_파악',
        '핵심_내용',
        '논리적_추론',
        '단어'
    ]
    DETAIL_TYPE_CHOICES = [
        '객관식_어법',
        '논술형_어법',
        '순서배열',
        '문장삽입',
        '제목',
        '주제',
        '요약문',
        '빈칸추론',
        '함축의미',
        '문맥어휘',
        '영영풀이'
    ]
    
    DETAIL_TYPE_TO_EVALUATION_AREA = {
        '객관식_어법': '어법 이해',
        '논술형_어법': '어법 이해',
        '순서배열': '글의_흐름_파악',
        '문장삽입': '글의_흐름_파악',
        '제목': '핵심_내용',
        '주제': '핵심_내용',
        '요약문': '핵심_내용',
        '빈칸추론': '논리적_추론',
        '함축의미': '논리적_추론',
        '문맥어휘': '단어',
        '영영풀이': '단어',
    }   
    EVALUATION_AREA_TO_CATEGORY = {
        '어법 이해': '어법',
        '글의_흐름_파악': '독해',
        '핵심_내용': '독해',
        '논리적_추론': '독해',
        '단어': '단어',
    }
    
    
    # detail_type에 따른 맵핑을 위한 GROUPS
    EVALUATION_GROUPS = {
        '어법': ['객관식_어법', '논술형_어법'],
        '글의_흐름_파악': ['순서배열', '문장삽입'],
        '핵심_내용': ['제목', '주제', '요약문'],
        '논리적_추론': ['빈칸추론', '함축의미'],
        '어휘': ['문맥어휘', '영영풀이']
    }
    CATEGORY_GROUPS = {
        '어법': ['객관식_어법', '논술형_어법'],
        '독해': ['순서배열', '문장삽입', '제목', '주제', '요약문', '빈칸추론', '함축의미', '문맥어휘', '영영풀이']
    }
    
    # detail_type에 따른 맵핑
    EVALUATION_MAPPING = {
        detail_type: evaluation_area
        for evaluation_area, detail_types in EVALUATION_GROUPS.items()
        for detail_type in detail_types
    }
    CATEGORY_MAPPING = {
        detail_type : category
        for category, detail_types in CATEGORY_GROUPS.items() # items()메서드로 키와 값을 튜플로 반환하여 함께 순회시킴
        for detail_type in detail_types
    } # 리스트 컴프리헨션
    
    ## 필드 ##

    passage = models.ForeignKey(
        Passage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='questions', # 연결된 모델에서 나를 참조할 때 사용하는 이름
        verbose_name='연결된 지문' # UI에서 사용자에게 보여지는 이름
    )
       
    detail_type = models.CharField('상세유형', max_length=20, choices=[(choice, choice) for choice in DETAIL_TYPE_CHOICES], null=True, blank=True)  # django의 models.charField의 choices 파라미터는 튜플 리스트를 기대하기 때문에, 첫째와 두번째 요소가 같은 튜플의 형태로 변환함.
    answer = models.JSONField('정답', null=True, blank=True) # 객관식의 경우 [2], [1,3], ..., 주관식인 경우 str이 넘어오는데, 이걸 모두 처리할 수 있다.

    question_text = models.TextField('발문', default='')
    question_text_extra = models.TextField('발문 추가 내용(HTML)', blank=True, null=True)

    is_essay = models.BooleanField('논술형 여부', default=False)    
    
    ## 객관식 전용 필드 ##
    explanation = models.TextField('해설')
    
    ## 주관식 전용 필드 ##
    answer_format = models.TextField('답안형식', blank=True, null=True)
    
    ## 다대다 관계 필드 ##
    exam_sheets = models.ManyToManyField(
        ExamSheet, 
        through='ExamSheetQuestionMapping',
        related_name='questions'
    )
    
    ## 자동 설정 필드 ##
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    category = models.CharField('구분', max_length=10, choices=[(choice, choice) for choice in CATEGORY_CHOICES], null=True, blank=True)
    evaluation_area = models.CharField('평가영역', max_length=20, choices=[(choice, choice) for choice in EVALUATION_AREA_CHOICES], null=True, blank=True)
    
    
    class Meta:
        verbose_name = '문제'
        verbose_name_plural = '문제들'

    def save(self, *args, **kwargs):
        # 1) detail_type -> evaluation_area
        if self.detail_type:
            self.evaluation_area = self.DETAIL_TYPE_TO_EVALUATION_AREA.get(self.detail_type)

        # 2) evaluation_area -> category
        if self.evaluation_area:
            self.category = self.EVALUATION_AREA_TO_CATEGORY.get(self.evaluation_area)

        super().save(*args, **kwargs)

        
# 보기 모델 (Choice 모델과 Question 모델 1:1 관계)
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_number = models.IntegerField('보기 번호')  # 1, 2, 3, 4, 5
    text_content = models.TextField('보기 내용')
    
    class Meta:
        verbose_name = '보기'
        verbose_name_plural = '보기들'
        ordering = ['choice_number']
        unique_together = ['question', 'choice_number']



# 시험지와 문제 매핑 모델
class ExamSheetQuestionMapping(models.Model):
    exam_sheet = models.ForeignKey(ExamSheet, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    question_number = models.IntegerField('OMR 채점번호') # 객관식1번과 주관식1번 모두 1로 할당됨.
    order_number = models.IntegerField('시험지상 출제순서', null=True) # 실제 시험지에 정렬용으로 사용될 번호.
    
    
    class Meta:
        verbose_name = '시험지-문제 매핑'
        verbose_name_plural = '시험지-문제 매핑들'
        unique_together = ['exam_sheet', 'order_number']