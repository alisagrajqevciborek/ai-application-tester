from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0011_alter_testrun_test_type_general"),
    ]

    operations = [
        migrations.CreateModel(
            name="TestRunStepResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("step_key", models.CharField(help_text="Stable identifier for the step", max_length=50)),
                ("step_label", models.CharField(help_text="Human-readable step label", max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("pass_rate", models.IntegerField(default=0)),
                ("fail_rate", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("details_json", models.JSONField(default=dict, help_text="Raw details for this step")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "test_run",
                    models.ForeignKey(
                        help_text="Parent test run for this step result",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="step_results",
                        to="applications.testrun",
                    ),
                ),
            ],
            options={
                "verbose_name": "Test Run Step Result",
                "verbose_name_plural": "Test Run Step Results",
                "db_table": "test_run_step_results",
                "ordering": ["created_at"],
                "unique_together": {("test_run", "step_key")},
            },
        ),
    ]


