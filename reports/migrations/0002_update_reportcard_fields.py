from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reportcard',
            old_name='total_test_score',
            new_name='test_score',
        ),
        migrations.AddField(
            model_name='reportcard',
            name='assignment_score',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='quiz_score',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='overall_score',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='reportcard',
            name='course',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='report_cards',
                to='courses.course',
            ),
        ),
        migrations.RemoveField(
            model_name='reportcard',
            name='project_count',
        ),
        migrations.RemoveField(
            model_name='reportcard',
            name='status',
        ),
        migrations.RemoveField(
            model_name='reportcard',
            name='released_at',
        ),
        migrations.RemoveField(
            model_name='reportcard',
            name='released_by',
        ),
        migrations.AlterUniqueTogether(
            name='reportcard',
            unique_together={('student', 'course')},
        ),
    ]
