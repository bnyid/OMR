# Generated by Django 5.1.3 on 2025-02-01 03:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('exam_app', '0001_initial'),
        ('student_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OMRResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exam_date', models.DateField(verbose_name='시험 날짜')),
                ('teacher_code', models.CharField(max_length=2, verbose_name='강사코드')),
                ('exam_identifier', models.CharField(blank=True, max_length=8, null=True, verbose_name='시험식별자')),
                ('is_matched', models.BooleanField(default=False, verbose_name='매칭 여부')),
                ('unmatched_student_code', models.CharField(blank=True, max_length=8, null=True, verbose_name='미매칭 학생코드')),
                ('unmatched_student_name', models.CharField(blank=True, max_length=10, null=True, verbose_name='미매칭 학생이름')),
                ('answer_sheet', models.ImageField(upload_to='answer_sheets/', verbose_name='답안지')),
                ('processed_sheet', models.ImageField(blank=True, null=True, upload_to='processed_sheets/', verbose_name='처리된 답안지')),
                ('answers', models.JSONField(verbose_name='답안 결과')),
                ('class_name', models.CharField(blank=True, max_length=20, null=True, verbose_name='반이름')),
                ('omr_name', models.CharField(blank=True, default='', max_length=50, verbose_name='OMR 이름')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('front_page', models.ImageField(blank=True, null=True, upload_to='omr_front_pages/', verbose_name='OMR 앞면 이미지')),
                ('exam_sheet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='omr_results', to='exam_app.examsheet', verbose_name='시험지')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='student_app.student')),
            ],
            options={
                'verbose_name': 'OMR 결과',
                'verbose_name_plural': 'OMR 결과들',
            },
        ),
        migrations.CreateModel(
            name='OMRResultEssayImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_number', models.PositiveIntegerField(verbose_name='주관식 문항 번호')),
                ('image', models.ImageField(upload_to='essay_images/', verbose_name='주관식 문항 이미지')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('omr_result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='essay_images', to='omr_app.omrresult', verbose_name='OMR 결과')),
            ],
        ),
        migrations.CreateModel(
            name='OMRStudentAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected_answers', models.JSONField(blank=True, null=True, verbose_name='선택한 답')),
                ('is_correct', models.BooleanField(default=False, verbose_name='정답 여부')),
                ('score_earned', models.FloatField(default=0.0, verbose_name='획득 점수')),
                ('total_score', models.FloatField(default=1.0, verbose_name='배점')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('omr_result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_answers', to='omr_app.omrresult')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_answers', to='exam_app.question')),
            ],
            options={
                'verbose_name': '학생-문항별 응답',
                'verbose_name_plural': '학생-문항별 응답(OMRStudentAnswer)',
                'unique_together': {('omr_result', 'question')},
            },
        ),
    ]
