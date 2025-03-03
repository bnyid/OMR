# Generated by Django 5.1.3 on 2025-02-01 03:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ExamSheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
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
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.PositiveIntegerField(verbose_name='문항 번호')),
                ('multi_or_essay', models.CharField(max_length=20, verbose_name='문항 유형')),
                ('number', models.PositiveIntegerField(verbose_name='유형 내 번호')),
                ('detail_type', models.CharField(blank=True, max_length=50, null=True, verbose_name='세부 유형')),
                ('question_text', models.TextField(verbose_name='문제 본문')),
                ('answer', models.TextField(verbose_name='정답')),
                ('score', models.FloatField(verbose_name='배점')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('exam_sheet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='exam_app.examsheet', verbose_name='시험지')),
            ],
            options={
                'verbose_name': '문항',
                'verbose_name_plural': '문항들',
                'ordering': ['order_number'],
                'unique_together': {('exam_sheet', 'multi_or_essay', 'number')},
            },
        ),
    ]
