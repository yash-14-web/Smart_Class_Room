from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_course_end_date_course_start_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='results_released',
            field=models.BooleanField(default=False, help_text='Allow students to view pass/fail results for this course'),
        ),
    ]
