# apps/exam_app/models.py
from django.db import models

class ExamSheet(models.Model):
    title = models.CharField('시험명', max_length=100)
    total_questions = models.IntegerField('총 문항수')
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    
    class Meta:
        verbose_name = '시험지'
        verbose_name_plural = '시험지들'
        
    def __str__(self):
        return self.title


class Question(models.Model):
    exam_sheet = models.ForeignKey(
        ExamSheet,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='시험지'
    )
    order_number = models.PositiveIntegerField('문항 번호')
    multi_or_essay = models.CharField('문항 유형', max_length=20)  # 예: "객관식", "논술형"
    number = models.PositiveIntegerField('유형 내 번호') # 1부터 시작
    detail_type = models.CharField('세부 유형', max_length=50, null=True, blank=True)
    question_text = models.TextField('문제 본문')
    answer = models.JSONField('정답')
    score = models.FloatField('배점')
    
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    
    class Meta:
        verbose_name = '문항'
        verbose_name_plural = '문항들'
        ordering = ['order_number']
        
    def __str__(self):
        return f"{self.exam_sheet.title} - Q{self.order_number}"