# Generated by Django 5.1.3 on 2024-12-07 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr_app', '0008_remove_omrresult_exam_order_omrresult_teacher_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='omrresult',
            name='exam_identifier',
            field=models.CharField(blank=True, max_length=8, null=True, verbose_name='시험식별자'),
        ),
    ]
