# Generated by Django 4.2.11 on 2024-05-13 14:52

from django.db import migrations, models
import users.enums


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="first_name",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("senior", "Senior"),
                    ("junior", "Junior"),
                ],
                default=users.enums.Role["JUNIOR"],
                max_length=15,
            ),
        ),
    ]
