from django.db import models
from django.db.models import Q

from users.models import User

ISSUE_STATUS_CHOICES = (
    (1, "Opened"),
    (2, "In progress"),
    (3, "Closed"),
)


class IssueManager(models.Manager):
    def filter_by_participant(self, user: User):
        return self.filter(Q(junior=user) | Q(senior=user))


class Issue(models.Model):
    title = models.CharField(max_length=100)
    body = models.TextField(null=True)
    status = models.PositiveSmallIntegerField(choices=ISSUE_STATUS_CHOICES)

    junior = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="junior_issues"
    )
    senior = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="senior_issues", null=True
    )

    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    objects = IssueManager()

    def __repr__(self) -> str:
        return f"Issue[{self.pk} {self.title[:10]}]"

    def __str__(self) -> str:
        return self.title[:10]


class Message(models.Model):
    body = models.TextField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_messages"
    )
    issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE, related_name="issue_messages"
    )
