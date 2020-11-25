from django import forms
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist


class Account(models.Model):
    GENDER_CHOICES = [
        ('남성', '남성'),
        ('여성', '여성'),
    ]

    ROLE_CHOICES = [
        ('제출자', '제출자'),
        ('평가자', '평가자'),
        ('관리자', '관리자'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField('이름', max_length=20)
    contact = models.CharField('연락처', max_length=20)
    birth = models.DateField('생년월일', null=True, blank=True)
    gender = models.CharField('성별', max_length=5, choices=GENDER_CHOICES)
    address = models.CharField('주소', max_length=100)
    role = models.CharField('역할', max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return self.user.username


class Task(models.Model):
    name = models.CharField('태스크 이름', max_length=45, unique=True)
    minimal_upload_frequency = models.CharField('최소 업로드 주기', max_length=45)
    activation_state = models.BooleanField('활성화 상태', default=False)
    description = models.CharField('태스크 설명', max_length=100)
    original_data_description = models.CharField('원본 데이터 설명', max_length=100)

    def __str__(self):
        return self.name


class Participation(models.Model):
    class Meta:
        unique_together = (('account', 'task'),)

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='participations', verbose_name='제출자')
    task = models.ForeignKey(Task, on_delete=models.CASCADE,
                             related_name='participations', verbose_name='태스크')
    admission = models.BooleanField('승인 상태', default=False)
    submit_count = models.IntegerField('제출 횟수', default=0)

    def __str__(self):
        return "\"" + self.account.__str__() + "\" parts in \"" + self.task.__str__() + "\""


def grading_score_validator(value):
    if value < 0 or value > 10:
        raise forms.ValidationError('0 ~ 10 사이의 숫자를 입력해주세요.')


class ParsedFile(models.Model):
    submitter = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='parsed_submits', verbose_name='제출자')
    grader = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='parsed_grades', verbose_name='평가자')
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name='parsedfiles', verbose_name='태스크')
    directory = models.CharField('파일 이름', max_length=200)
    submit_number = models.IntegerField('제출 회차')
    start_date = models.DateField('수집 시작 날짜')
    end_date = models.DateField('수집 종료 날짜')
    total_tuple = models.IntegerField('전체 튜플 수')
    duplicated_tuple = models.IntegerField('중복 튜플 수')
    null_ratio = models.FloatField('null 비율')
    grading_score = models.IntegerField('평가 점수', null=True, blank=True)
    pass_state = models.BooleanField('패스 여부', null=True, blank=True)
    grading_end_date = models.DateField('평가 종료 날짜')

    file_original = models.FileField(
        '파일',
        null=True,
        blank=True,
        upload_to="data_original/"
    )

    file_parsed = models.FileField(
        '처리된 파일',
        null=True,
        blank=True,
        upload_to="data_parsed/"
    )

    def __str__(self):
        """
        return file name
        """
        return self.directory


class SchemaAttribute(models.Model):
    """
    docstring
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE,
                             related_name='schema_definition', verbose_name='태스크')
    attr = models.CharField('컬럼 레이블', max_length=45)

    def __str__(self):
        """
        """
        return self.attr


class MappingInfo(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE,
                             related_name='mapping_info', verbose_name='파생 스키마 매핑 정보')
    derived_schema_name = models.CharField('파생 스키마 이름', max_length=45)

    def __str__(self):
        """
        """
        return self.derived_schema_name


class MappingPair(models.Model):
    """
    docstring
    """
    mapping_info = models.ForeignKey(
        MappingInfo, on_delete=models.CASCADE, related_name='mapping_info_attribute', verbose_name='매핑 정보')
    # 실제 마스터 스키마의 FK
    schema_attribute = models.ForeignKey(SchemaAttribute, on_delete=models.CASCADE,
                                         related_name='derived_schema_to_unique_schema_mapping', verbose_name='고유 스키마 속성')
    # schema for user to parse
    parsing_column_name = models.CharField('파생 스키마 속성 레이블', max_length=45)

    def __str__(self):
        dictionary = {
            self.mapping_info.__str__(): {
                "master": self.schema_attribute.__str__(),
                "derived": self.parsing_column_name.__str__()
            }
        }
        return dictionary.__str__()


class OriginFile(models.Model):
    """
    docstring
    """
    # name = models.CharField('파일명', max_length=200)
    derived_schema = models.ForeignKey(
        MappingInfo, on_delete=models.CASCADE, related_name='file_parsing_schema', verbose_name='파생 스키마')
    file_original = models.FileField(
        '파일', null=True, blank=True, upload_to="data_original/", max_length=100)

    def __str__(self):
        """
        docstring
        """
        return self.file_original.name

    def get_absolute_path(self):
        return os.path.join(settings.MEDIA_ROOT, self.file_original.name)

    def delete(self, *args, **kargs):
        if self.file_original:
            os.remove(os.path.join(
                settings.MEDIA_ROOT, self.file_original.name))
        super(OriginFile, self).delete(*args, **kargs)
