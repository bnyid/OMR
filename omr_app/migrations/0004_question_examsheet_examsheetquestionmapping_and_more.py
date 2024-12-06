# Generated by Django 5.1.3 on 2024-12-06 15:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr_app', '0003_alter_student_registered_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial_number', models.CharField(max_length=20, unique=True, verbose_name='일련번호')),
                ('type', models.CharField(choices=[('SO', '순서배열'), ('SI', '문장삽입'), ('BL', '빈칸추론'), ('IM', '함축의미'), ('SU', '요약'), ('VO', '문맥어휘'), ('TH', '주제'), ('TI', '제목')], max_length=2, verbose_name='유형')),
                ('answer_format', models.CharField(choices=[('MC', '객관식'), ('SA', '주관식')], default='MC', max_length=2, verbose_name='답안형식')),
                ('content', models.TextField(verbose_name='본문')),
                ('choice_1', models.CharField(blank=True, max_length=200, null=True, verbose_name='보기1')),
                ('choice_2', models.CharField(blank=True, max_length=200, null=True, verbose_name='보기2')),
                ('choice_3', models.CharField(blank=True, max_length=200, null=True, verbose_name='보기3')),
                ('choice_4', models.CharField(blank=True, max_length=200, null=True, verbose_name='보기4')),
                ('choice_5', models.CharField(blank=True, max_length=200, null=True, verbose_name='보기5')),
                ('answer', models.CharField(max_length=100, verbose_name='정답')),
                ('explanation', models.TextField(verbose_name='해설')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '문제',
                'verbose_name_plural': '문제들',
            },
        ),
        migrations.CreateModel(
            name='ExamSheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial_number', models.CharField(max_length=20, unique=True, verbose_name='일련번호')),
                ('exam_date', models.DateField(verbose_name='시행일')),
                ('title', models.CharField(max_length=100, verbose_name='시험명')),
                ('total_questions', models.IntegerField(verbose_name='총 문항수')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '시험지',
                'verbose_name_plural': '시험지들',
            },
        ),
        migrations.CreateModel(
            name='ExamSheetQuestionMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_number', models.IntegerField(verbose_name='문항번호')),
                ('exam_sheet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omr_app.examsheet')),
            ],
            options={
                'verbose_name': '시험지-문제 매핑',
                'verbose_name_plural': '시험지-문제 매핑들',
            },
        ),
        migrations.CreateModel(
            name='OriginalText',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_type', models.CharField(choices=[('TB', '교과서'), ('ET', '모의고사'), ('EX', '외부지문')], max_length=2, verbose_name='원문 유형')),
                ('content', models.TextField(verbose_name='본문')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '지문 원문',
                'verbose_name_plural': '지문 원문들',
            },
        ),
        migrations.RemoveField(
            model_name='omrresult',
            name='student_code',
        ),
        migrations.RemoveField(
            model_name='omrresult',
            name='student_name',
        ),
        migrations.AddField(
            model_name='omrresult',
            name='student',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='omr_app.student'),
        ),
        migrations.CreateModel(
            name='BlankInferenceQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
                ('blank_text', models.TextField(verbose_name='빈칸 본문')),
            ],
            options={
                'verbose_name': '빈칸추론 문제',
                'verbose_name_plural': '빈칸추론 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.CreateModel(
            name='ImpliedMeaningQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
                ('underlined_sentence', models.TextField(verbose_name='밑줄 문장')),
            ],
            options={
                'verbose_name': '함축의미 문제',
                'verbose_name_plural': '함축의미 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.CreateModel(
            name='SentenceInsertQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
                ('insert_sentence', models.TextField(verbose_name='삽입 문장')),
                ('first_sentence', models.TextField(verbose_name='첫 문장')),
                ('sentence_1', models.TextField(verbose_name='1번 뒤 문장')),
                ('sentence_2', models.TextField(verbose_name='2번 뒤 문장')),
                ('sentence_3', models.TextField(verbose_name='3번 뒤 문장')),
                ('sentence_4', models.TextField(verbose_name='4번 뒤 문장')),
                ('sentence_5', models.TextField(verbose_name='5번 뒤 문장')),
            ],
            options={
                'verbose_name': '문장삽입 문제',
                'verbose_name_plural': '문장삽입 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.CreateModel(
            name='SequenceOrderQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
                ('text_a', models.TextField(verbose_name='본문A')),
                ('text_b', models.TextField(verbose_name='본문B')),
                ('text_c', models.TextField(verbose_name='본문C')),
            ],
            options={
                'verbose_name': '순서배열 문제',
                'verbose_name_plural': '순서배열 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.CreateModel(
            name='SummaryQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
                ('summary_text', models.TextField(verbose_name='요약문')),
            ],
            options={
                'verbose_name': '요약 문제',
                'verbose_name_plural': '요약 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.CreateModel(
            name='ThemeQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
            ],
            options={
                'verbose_name': '주제 문제',
                'verbose_name_plural': '주제 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.CreateModel(
            name='TitleQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
            ],
            options={
                'verbose_name': '제목 문제',
                'verbose_name_plural': '제목 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.CreateModel(
            name='VocaInContextQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.question')),
                ('question_text', models.TextField(verbose_name='발문')),
            ],
            options={
                'verbose_name': '문맥어휘 문제',
                'verbose_name_plural': '문맥어휘 문제들',
            },
            bases=('omr_app.question',),
        ),
        migrations.AddField(
            model_name='question',
            name='exam_sheets',
            field=models.ManyToManyField(related_name='questions', through='omr_app.ExamSheetQuestionMapping', to='omr_app.examsheet'),
        ),
        migrations.AddField(
            model_name='examsheetquestionmapping',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omr_app.question'),
        ),
        migrations.CreateModel(
            name='ExamText',
            fields=[
                ('originaltext_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.originaltext')),
                ('grade', models.IntegerField(verbose_name='학년')),
                ('year', models.IntegerField(verbose_name='년도')),
                ('month', models.IntegerField(verbose_name='시행월')),
                ('question_number', models.IntegerField(verbose_name='문항번호')),
            ],
            bases=('omr_app.originaltext',),
        ),
        migrations.CreateModel(
            name='ExternalText',
            fields=[
                ('originaltext_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.originaltext')),
                ('category1', models.CharField(max_length=100, verbose_name='구분1')),
                ('category2', models.CharField(max_length=100, verbose_name='구분2')),
            ],
            bases=('omr_app.originaltext',),
        ),
        migrations.CreateModel(
            name='TextbookText',
            fields=[
                ('originaltext_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='omr_app.originaltext')),
                ('subject', models.CharField(max_length=50, verbose_name='과목')),
                ('publisher', models.CharField(max_length=100, verbose_name='출판사')),
                ('chapter', models.CharField(max_length=50, verbose_name='과')),
                ('text_number', models.CharField(max_length=50, verbose_name='본문번호')),
            ],
            bases=('omr_app.originaltext',),
        ),
        migrations.AddField(
            model_name='question',
            name='original_text',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='omr_app.originaltext', verbose_name='원문'),
        ),
        migrations.AlterUniqueTogether(
            name='examsheetquestionmapping',
            unique_together={('exam_sheet', 'question_number')},
        ),
    ]
