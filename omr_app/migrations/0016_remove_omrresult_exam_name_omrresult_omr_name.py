# Generated by Django 5.1.3 on 2024-12-11 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr_app', '0015_student_status_reason'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='omrresult',
            name='exam_name',
        ),
        migrations.AddField(
            model_name='omrresult',
            name='omr_name',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='OMR 이름'),
        ),
    ]
