# Generated by Django 5.1.3 on 2024-12-11 04:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr_app', '0012_student_class_name_by_school'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='status',
            field=models.CharField(choices=[('enrolled', '재원'), ('leave', '휴원'), ('dropout', '퇴원'), ('graduated', '졸업')], default='enrolled', max_length=10, verbose_name='재원 상태'),
        ),
    ]
