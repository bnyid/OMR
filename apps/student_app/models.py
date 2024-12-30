from django.db import models

class Student(models.Model):
    SCHOOL_TYPE_CHOICES = [
        ('초등', '초등'),
        ('중등', '중등'),
        ('고등', '고등'),
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

    school_type = models.CharField('중/고등 구분', max_length=2, choices=SCHOOL_TYPE_CHOICES, null=True, blank=True)
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
    # 등록번호가 없고, 등록일자가 있는 경우에만 등록번호 생성
        if not self.registration_number and self.registered_date:
            # registered_date가 문자열인 경우 datetime으로 변환
            if isinstance(self.registered_date, str):
                try:
                    from datetime import datetime
                    self.registered_date = datetime.strptime(self.registered_date, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError("등록일자 형식이 올바르지 않습니다. (YYYY-MM-DD)")
                    
            self.registration_number = self.generate_registration_number(
                self.registered_date, 
                self.id  # 기존 레코드 수정 시 자신의 ID 제외
            )
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"[{self.id} {self.student_code}] {self.name} ({self.class_name})"