from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, response, serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from users.enums import Role

from .enums import Status
from .models import Issue, Message


class IssueSerializer(serializers.ModelSerializer):
    status = serializers.CharField(required=False)
    junior = serializers.HiddenField(default=serializers.CurrentUserDefault())

    senior_email = serializers.CharField(source="senior.email", read_only=True)

    class Meta:
        model = Issue
        fields = "__all__"

    def validate(self, attrs):
        attrs["status"] = Status.OPENED
        return attrs


class IssueAPI(generics.ListCreateAPIView):
    http_method_names = ["get", "post"]
    serializer_class = IssueSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == Role.ADMIN:
            return Issue.objects.all()
        elif user.role == Role.SENIOR:
            return Issue.objects.filter(
                Q(senior=self.request.user)
                | (Q(senior=None) & Q(status=Status.OPENED))
            )
        elif user.role == Role.JUNIOR:
            return Issue.objects.filter(junior=user)

    def post(self, request):
        if request.user.role == Role.SENIOR:
            raise Exception("The role is senior")

        return super().post(request)


class IssuesRetrieveAPI(generics.RetrieveUpdateDestroyAPIView):
    http_method_names = ["get", "put", "patch", "delete"]
    serializer_class = IssueSerializer
    queryset = Issue.objects.all()
    lookup_url_kwarg = "id"

    def delete(self, request, *args, **kwargs):
        user = request.user
        if user.role != Role.ADMIN:
            raise PermissionDenied(
                "Only administrators can perform this action."
            )
        return super().delete(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = request.user
        if user.role not in [Role.ADMIN, Role.SENIOR]:
            raise PermissionDenied(
                "Only administrators and seniors can perform this action."
            )
        return super().update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        issue = self.get_object()
        if user.role == Role.JUNIOR and issue.junior != user:
            raise PermissionDenied(
                "You can't access another person's question."
            )
        return super().retrieve(request, *args, **kwargs)


class MessegaSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    issue = serializers.PrimaryKeyRelatedField(queryset=Issue.objects.all())

    author_role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Message
        fields = "__all__"

    def save(self):
        if (user := self.validated_data.pop("user", None)) is not None:
            self.validated_data["user_id"] = user.id

        if (issue := self.validated_data.pop("issue", None)) is not None:
            self.validated_data["issue_id"] = issue.id

        return super().save()


@api_view(["GET", "POST"])
def messages_api_dispatcher(request: Request, issue_id: int):

    try:
        issue = Issue.objects.get(id=issue_id)
    except Issue.DoesNotExist:
        return response.Response({"message": "Запит не знайдено"}, status=404)

    if request.user not in [issue.junior, issue.senior]:
        raise PermissionDenied("Ви не є учасником цього чату")

    if request.method == "GET":
        messages = Message.objects.filter(issue=issue).order_by("-timestamp")
        serializers = MessegaSerializer(messages, many=True)
        return response.Response(serializers.data)

    else:
        if issue.status != Status.IN_PROGRESS:
            return response.Response(
                {"message": "Писати можна тільки в активні запити"},
                status=403,
            )

        payload = request.data | {"issue": issue.id}
        serializer = MessegaSerializer(
            data=payload, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return response.Response(serializer.data)


class IssueCloseSerializer(serializers.Serializer):
    rating = serializers.IntegerField(
        min_value=1, max_value=5, help_text="Оцінка від 1 до 5"
    )


@swagger_auto_schema(method="put", request_body=IssueCloseSerializer)
@api_view(["PUT"])
def issues_close(request: Request, id: int):
    try:
        issue = Issue.objects.get(id=id)
    except Issue.DoesNotExist:
        return response.Response({"message": "Запит не знайдено"}, status=404)

    if request.user != issue.junior:
        raise PermissionDenied(
            "Тільки автор запиту може його закрити та оцінити"
        )

    if issue.status != Status.IN_PROGRESS:
        return response.Response(
            {"message": "Можна закрити лише запит, який знаходиться в роботі"},
            status=422,
        )

    rating = request.data.get("rating")
    if rating is None:
        return response.Response(
            {"message": "Необхідно вказати оцінку (rating)"}, status=400
        )

    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError()
    except ValueError:
        return response.Response(
            {"message": "Оцінка має бути цілим числом від 1 до 5"}, status=400
        )

    issue.status = Status.CLOSED
    issue.rating = rating
    issue.save()

    serializer = IssueSerializer(issue)
    return response.Response(serializer.data)


@api_view(["PUT"])
def issues_take(request: Request, id: int):
    issue = Issue.objects.get(id=id)

    if request.user.role != Role.SENIOR:
        raise PermissionError("Only senior users can take issues")

    if (issue.status != Status.OPENED) or (issue.senior is not None):
        return response.Response(
            {"message": "Issue is not Opened or senior is set..."},
            status=422,
        )
    else:
        issue.senior = request.user
        issue.status = Status.IN_PROGRESS
        issue.save()

    serializer = IssueSerializer(issue)

    return response.Response(serializer.data)


# @api_view(["GET"])
# def fetch_issues(request):
#     all_issues = Issue.objects.all()
#     serialized_issues = IssueSerializer(all_issues, many=True)
#     return Response(serialized_issues.data)


# @api_view(["POST"])
# def add_new_issue(request):
#     received_data = request.data
#     new_issue_serializer = IssueSerializer(data=received_data)

#     if new_issue_serializer.is_valid():
#         new_issue_serializer.save()
#         return Response(new_issue_serializer.data)
#     else:
#         return Response(new_issue_serializer.errors)
