# Generated by Django 5.1.3 on 2024-12-07 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr_app', '0005_omrresult_is_matched_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='omrresult',
            name='unmatched_student_name',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='미매칭 학생이름'),
        ),
    ]
