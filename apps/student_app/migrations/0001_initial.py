# Generated by Django 5.1.3 on 2025-02-01 03:56

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('enrolled', '재원'), ('leave', '휴원'), ('dropout', '퇴원'), ('graduated', '졸업')], default='enrolled', max_length=10, verbose_name='재원 상태')),
                ('status_changed_date', models.DateField(blank=True, null=True, verbose_name='상태변경일')),
                ('status_reason', models.TextField(blank=True, null=True, verbose_name='상태변경사유')),
                ('student_code', models.CharField(blank=True, max_length=8, null=True, unique=True, verbose_name='학번')),
                ('registration_number', models.CharField(blank=True, max_length=11, null=True, verbose_name='등록번호')),
                ('registered_date', models.DateField(blank=True, null=True)),
                ('name', models.CharField(max_length=10, verbose_name='이름')),
                ('class_name_by_school', models.CharField(blank=True, max_length=50, null=True, verbose_name='내신반')),
                ('class_name', models.CharField(blank=True, max_length=20, null=True, verbose_name='소속반')),
                ('school_type', models.CharField(blank=True, choices=[('초등', '초등'), ('중등', '중등'), ('고등', '고등')], max_length=2, null=True, verbose_name='중/고등 구분')),
                ('school_name', models.CharField(blank=True, max_length=30, null=True, verbose_name='학교명')),
                ('grade', models.IntegerField(blank=True, choices=[(1, '1학년'), (2, '2학년'), (3, '3학년')], null=True, verbose_name='학년')),
                ('phone_number', models.CharField(blank=True, max_length=11, null=True, verbose_name='본인 연락처')),
                ('parent_phone', models.CharField(blank=True, max_length=11, null=True, verbose_name='보호자 연락처')),
                ('note', models.TextField(blank=True, null=True, verbose_name='비고')),
            ],
            options={
                'verbose_name': '학생',
                'verbose_name_plural': '학생들',
            },
        ),
    ]
