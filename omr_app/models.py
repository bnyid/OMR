from django.db import models

class OMRResult(models.Model):
    exam_date = models.DateField('시험 날짜')
    class_code = models.CharField('반 코드', max_length=2)
    student_id = models.CharField('학번', max_length=8)
    student_name = models.CharField('이름', max_length=10)
    answer_sheet = models.ImageField('답안지', upload_to='answer_sheets/')
    processed_sheet = models.ImageField('처리된 답안지', upload_to='processed_sheets/', null=True, blank=True)
    answers = models.JSONField('답안 결과')
    created_at = models.DateTimeField('생성일', auto_now_add=True)

    class Meta:
        verbose_name = 'OMR 결과'
        verbose_name_plural = 'OMR 결과들'

    def __str__(self):
        return f"{self.exam_date} - {self.class_code} - {self.student_name}"

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
    
    student_id = models.CharField('학번', max_length=8, primary_key=True)
    registered_date = models.DateField('등록일', auto_now_add=True)
    name = models.CharField('이름', max_length=10)
    class_name = models.CharField('소속반', max_length=20)
    school_type = models.CharField('중/고등 구분', max_length=1, choices=SCHOOL_TYPE_CHOICES)
    grade = models.IntegerField('학년', choices=GRADE_CHOICES)
    school_name = models.CharField('학교명', max_length=30)
    phone_number = models.CharField('본인 연락처', max_length=11)
    parent_phone = models.CharField('보호자 연락처', max_length=11)
    note = models.TextField('비고', blank=True)
    
    class Meta:
        verbose_name = '학생'
        verbose_name_plural = '학생들'
        
    def __str__(self):
        return f"[{self.class_name}] {self.name} ({self.student_id})"
