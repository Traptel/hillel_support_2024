from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied

from users.enums import Role

from .enums import Status
from .models import Issue


class IssueSerializer(serializers.ModelSerializer):
    status = serializers.CharField(required=False)
    junior = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Issue
        fields = "__all__"

    def validate(self, attrs):
        attrs["status"] = Status.OPEND
        return attrs


class IssueAPI(generics.ListCreateAPIView):
    http_method_names = ["get", "post"]
    serializer_class = IssueSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == Role.ADMIN:
            return Issue.objects.all()
        elif user.role == Role.SENIOR:
            return Issue.objects.filter(senior=user) | Issue.objects.filter(
                senior=None
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
