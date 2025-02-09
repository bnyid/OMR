# apps/omr_app/models.py
from django.db import models

      
## OMR 결과 모델 ##
class OMRResult(models.Model):
    exam_date = models.DateField('시험 날짜')
    teacher_code = models.CharField('강사코드', max_length=2)  # '01', '02', ... 형태로 저장
    exam_identifier = models.CharField('시험식별자', max_length=8, null=True, blank=True)  # exam_date와 teacher_code 결합 후 save()에서 자동 설정
    exam_sheet = models.ForeignKey('exam_app.ExamSheet',  # 'app이름.모델이름'의 문자열 형식으로 참조하면 순환 참조를 피할 수 있음.
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='omr_results',
        verbose_name='시험지'
    )
    student = models.ForeignKey('student_app.Student', on_delete=models.CASCADE, null=True, blank=True, default=None)
    unmatched_student_code = models.CharField('미매칭 학생코드', max_length=8, null=True, blank=True)
    unmatched_student_name = models.CharField('미매칭 학생이름', max_length=10, null=True, blank=True)
    
    answer_sheet = models.ImageField('답안지', upload_to='answer_sheets/')
    processed_sheet = models.ImageField('처리된 답안지', upload_to='processed_sheets/', null=True, blank=True)
    answers = models.JSONField('답안 결과')
    
    class_name = models.CharField('반이름', max_length=20, null=True, blank=True)
    omr_name = models.CharField('OMR 이름', max_length=50, default='', blank=True)
    
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    
    front_page = models.ImageField('OMR 앞면 이미지', upload_to='omr_front_pages/', null=True, blank=True)
    
    is_graded = models.BooleanField('채점 완료 여부', default=False)
    
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
    


class OMRResultEssayImage(models.Model):
    """
    주관식(서술형) 이미지 정보
    """
    omr_result = models.ForeignKey(
        OMRResult,
        on_delete=models.CASCADE,
        related_name='essay_images',  # OMRResult에서 역참조할 때 omr_result.essay_images.all()
        verbose_name='OMR 결과'
    )
    question_number = models.PositiveIntegerField('주관식 문항 번호')
    image = models.ImageField('주관식 문항 이미지', upload_to='essay_images/')
    created_at = models.DateTimeField('등록일', auto_now_add=True)

    def __str__(self):
        return f"OMR {self.omr_result.id} - 문항 {self.question_number}"
    
    
    
class OMRStudentAnswer(models.Model):
    """
    한 학생(OMRResult)이 특정 문항(Question)에 대해 어떤 응답을 했고,
    채점 결과가 어떠한지 저장하는 테이블
    """
    omr_result = models.ForeignKey(
        OMRResult,
        on_delete=models.CASCADE,
        related_name='student_answers'
    )
    question = models.ForeignKey(
        'exam_app.Question',
        on_delete=models.CASCADE,
        related_name='student_answers'
    )

    # 복수응답인 경우, ex) [2,3] 형태도 가능
    # 단일응답 ex) 2, 혹은 문자열 "2"
    selected_answers = models.JSONField('선택한 답', null=True, blank=True)

    # 채점 결과
    is_correct = models.BooleanField('정답 여부', default=False)
    # 부분점수 / 만점 저장
    score_earned = models.FloatField('획득 점수', null=True, blank=True, default=None)
    total_score = models.FloatField('배점', default=1.0)

    created_at = models.DateTimeField('생성일', auto_now_add=True)

    class Meta:
        verbose_name = '학생-문항별 응답'
        verbose_name_plural = '학생-문항별 응답(OMRStudentAnswer)'
        unique_together = [('omr_result', 'question')]

    def __str__(self):
        return f"식별자 {self.omr_result.exam_identifier}시험의 {self.omr_result.student.name}의 - {self.question.multi_or_essay} 문항 {self.question.number}번 ROW"
    

    def save(self, *args, **kwargs):
        self.total_score = self.question.score
        
        # 객관식 (채점 수행)
        if self.question.multi_or_essay == '객관식':  # 새로운 객체 생성시에만 자동 채점
            if not self.selected_answers:
                self.selected_answers = ['9']
                
            # 정답  JSONField 형태로 저장되었기 때문에, 사용 시 DJANGO에 의해 list로 자동 변환
            correct_answer = self.question.answer    
            # 학생의 답안 리스트로 변환
            selected = [str(x).strip() for x in self.selected_answers]
            
            # 채점
            self.is_correct = (set(correct_answer) == set(selected))
            self.score_earned = self.total_score if self.is_correct else 0.0

        # 논술형 (점수는 뷰에서 받아오므로 유효성 검사만 수행)
        else:
            # 논술형의 경우, 채점이 아직 이루어지지 않았다면 score_earned는 None(=default)인 상태일 것임.
            # 만약 사용자가 점수를 입력했다면(=score_earned가 None이 아니라면), 유효성 검사를 수행.
            if self.score_earned is not None:
                if self.score_earned > self.total_score:
                    raise ValueError(f"{self.omr_result.student.name}의 주관식 {self.question.number}번의 획득 점수가 배점을 초과하여 오류 발생")
                if self.score_earned < 0:
                    raise ValueError(f"{self.omr_result.student.name}의 주관식 {self.question.number}번의 획득 점수가 음수로 오류 발생")

        super().save(*args, **kwargs)
        
        # 부모 OMRResult의 모든 학생 답안이 채점되었는지 검사하여 is_graded를 업데이트
        all_answers = self.omr_result.student_answers.all()
        
        if all(answer.score_earned is not None for answer in all_answers):
            self.omr_result.is_graded = True
            self.omr_result.save(update_fields=['is_graded'])
        
            

