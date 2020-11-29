from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, get_list_or_404, redirect
from django.urls import reverse
from django.views import generic, View
from django.contrib import auth, messages
from django.contrib.auth.models import User
from django.conf import settings

from .models import Account, Task, Participation, ParsedFile, SchemaAttribute, MappingInfo, MappingPair
from .forms import LoginForm, GradeForm, SchemaChoiceForm, UploadForm, CreateTask, CreateSchemaAttribute, CreateMappingInfo, CreateMappingPair

from datetime import date, datetime, timedelta
import os
import pandas as pd
import numpy as np
import mimetypes
import urllib


# 홈
def index(request):
    # if request.user.:
    #     return render(request, 'collect/index.html')
    if not request.user.is_authenticated:
        return render(request, 'collect/index.html')
    user = Account.objects.filter(user=request.user)[0]
    if user.role == "제출자":
        return redirect(reverse('collect:submitter'))
    elif user.role == "평가자":
        return redirect(reverse('collect:grader'))
    elif user.role == "관리자":
        return redirect(reverse('collect:manager'))


def fileList(request):
    """
    docstring
    """
    return render(request, 'manager/list.html', {
        'files': str(list(ParsedFile.objects.values())),
        'files_parsed': str(list(ParsedFile.objects.values())),
    })


# 회원가입
def signup(request):
    context = {}
    if request.method == "POST":
        if request.POST["password1"] == request.POST["password2"]:
            user = User.objects.create_user(
                username=request.POST["username"],
                password=request.POST["password1"])
            account = Account(
                user=user,
                name=request.POST["name"],
                contact=request.POST["contact"],
                birth=request.POST["birth"],
                gender=request.POST["gender"],
                address=request.POST["address"],
                role=request.POST["role"])
            account.save()
            auth.login(request, user)
            if account.role == '제출자':
                return redirect(reverse('collect:submitter'))
            elif account.role == '평가자':
                return redirect(reverse('collect:grader'))
            elif account.role == '관리자':
                return redirect(reverse('manager:list'))
        else:
            context.update({'error': "비밀번호가 일치하지 않습니다."})
    return render(request, 'collect/signup.html', context)


# 로그인
def login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            if user.account.role == '제출자':
                return redirect(reverse('collect:submitter'))
            elif user.account.role == '평가자':
                return redirect(reverse('collect:grader'))
            elif user.account.role == '관리자':
                return redirect(reverse('collect:manager'))
        messages.error(request, '로그인 실패. 다시 시도 해보세요.')
        return render(request, 'collect/login.html')
    else:
        return render(request, 'collect/login.html')


# 로그아웃
def logout(request):
    auth.logout(request)
    return redirect(reverse('collect:index'))


# 정보 조회
def userinfo(request, pk):
    user = request.user
    account = user.account
    context = {
        'user': user,
        'account': account
    }
    return render(request, 'collect/userinfo.html', context)


# 회원 정보 수정
def update(request, pk):
    if request.method == "POST":
        user = request.user
        if request.POST["password1"] == request.POST["password2"]:
            user.set_password(request.POST["password1"])
            user.save()
            account = user.account
            account.name = request.POST["name"]
            account.contact = request.POST["contact"]
            account.birth = request.POST["birth"]
            account.gender = request.POST["gender"]
            account.address = request.POST["address"]
            account.save()
            auth.login(request, user)
            if account.role == '제출자':
                return redirect(reverse('collect:tasks'))
            elif account.role == '평가자':
                return redirect(reverse('collect:allocated-parsedfiles'))
    return render(request, 'collect/update.html')


# 회원 탈퇴
def delete(request, pk):
    user = User.objects.get(pk=pk)
    user.delete()
    return redirect(reverse('collect:index'))


# 태스크 목록
class TaskList(View):
    def get(self, request):
        account = request.user.account
        task_list = Task.objects.all()
        participations = Participation.objects.filter(account=account)
        participate_tasks = [
            participation.task for participation in participations]
        context = {
            'task_list': task_list,
            'participate_tasks': participate_tasks
        }
        return render(request, 'collect/task.html', context)


# 태스크 상세 정보
class TaskDetail(View):
    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if request.user.account.role == '관리자':
            return render(request, 'manager/task_detail.html', {'task': task})
        return render(request, 'collect/task_detail.html', {'task': task})


# 태스크 참여
def create_participation(request, pk):
    user = request.user
    task = get_object_or_404(Task, pk=pk)
    participation = Participation(account=user.account, task=task)
    participation.save()
    return redirect(reverse('collect:participations'))


# 참여 중인 태스크 목록
class ParticipationList(View):
    def get(self, request):
        user = request.user
        participations = user.account.participations.all()
        return render(request, 'collect/participation.html', {'participations': participations})



# 제출자: 태스크 참여 취소
def delete_participation(request, pk):
    if not request.user.is_superuser:
        participation = get_object_or_404(Participation, pk=pk)
        participation.delete()
        return redirect(reverse('collect:participations'))


# 관리자: 태스크 참여 승인
def manager_acknowledge_participation(request, part_id):
    if request.user.is_superuser:
        task = Participation.objects.filter(id=part_id)[0].task
        participation = get_object_or_404(Participation, pk=part_id)
        participation.admission = True
        participation.save()
        return redirect(reverse('show task', kwargs={'task_id': task.id}))


# 관리자: 태스크 참여 거절
def manager_delete_participation(request, part_id):
    if request.user.is_superuser:
        task = Participation.objects.filter(id=part_id)[0].task
        participation = get_object_or_404(Participation, pk=part_id)
        participation.delete()
        return redirect(reverse('show task', kwargs={'task_id': task.id}))


# 관리자: 제출자가 제출한 파일 목록
def submittedfile_list(request, task_id, user_id):
    user = get_object_or_404(User, pk=user_id)
    task = get_object_or_404(Task, pk=task_id)
    parsedfile_list = user.account.parsed_submits.filter(task=task)
    total_tuple = sum(parsedfile.total_tuple if parsedfile.total_tuple else 0 for parsedfile in parsedfile_list)
    context = {
        'task': task,
        'parsedfile_list': parsedfile_list,
        'total_tuple': total_tuple
    }
    return render(request, 'manager/submitted_parsedfile.html', context)


def syncTotalTableFile(task):
    """
    파싱된 파일 전부 통합해 마스터 테이블에 등록
    사용처
     - 평가자가 패스한 후
     - 관리자가 태스크 조회할 때
    """
    attr = [ attrObj.attr for attrObj in SchemaAttribute.objects.filter(task=task) ]
    parsedfile_list = ParsedFile.objects.filter(task=task)

    if not parsedfile_list:
        return
    
    # df = pd.DataFrame(columns=attr)
    # df = pd.read_csv(os.path.join(settings.JOINED_PATH_DATA_PARSED, parsedfile_list[0].__str__()))
    file_list = []
    # print(df)
    # print("#####")

    for parsedFileObj in parsedfile_list:
        if not parsedFileObj.file_parsed is None:
            df_parsedFile = pd.read_csv(os.path.join(settings.JOINED_PATH_DATA_PARSED, parsedFileObj.__str__()))
            # df.append(df_parsedFile, ignore_index=True)
            file_list.append(df_parsedFile)
            # print(df_parsedFile)
        # print(df)
        # print("#")

    if not os.path.exists(settings.JOINED_PATH_DATA_INTEGRATED):
        os.mkdir(settings.JOINED_PATH_DATA_INTEGRATED)
    
    download_file_path = os.path.join(settings.JOINED_PATH_DATA_INTEGRATED, task.name) + ".csv"
    df = pd.concat(file_list, axis=0, ignore_index=True)
    df.to_csv(download_file_path, header=attr, index=True)

    return download_file_path


# 제출자: 제출한 파일 목록 확인 및 업로드
def parsedFileListAndUpload(request, pk):
    os.makedirs(settings.JOINED_PATH_DATA_ORIGINAL, exist_ok=True)
    os.makedirs(settings.JOINED_PATH_DATA_PARSED, exist_ok=True)

    user = request.user
    task = get_object_or_404(Task, pk=pk)

    form = None
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        # schema_choice_form = SchemaChoiceForm(request.POST, request.FILES)
        if form.is_valid():
            # TODO: 이 부분 구현해야 합니다!
            # 각 릴레이션의 튜풀을 받아야 합니다.
            # 이런 식으로요:
            # task = Task.objects.filter(***)[0]
            # 아마 key 등을 이 함수의 파라미터를 통해 받아오는 방법 등을 택할 것 같네요.
            grader_pk = 2
            
            submitter = Account.objects.filter(user=user)[0]
            grader = Account.objects.filter(id=grader_pk)[0]

            # form = form.save(commit=False) # 중복 DB save를 방지
            parsedFile = form.save()
            parsedFile.task = task
            parsedFile.submitter = submitter
            parsedFile.grader = grader
            parsedFile.save()

            derived_schema = parsedFile.derived_schema
            original_file_path = os.path.join(settings.MEDIA_ROOT, 
                parsedFile.file_original.name)

            # guess type and load file into pd.DataFrame
            # types: https://www.iana.org/assignments/media-types/media-types.xhtml
            original_file_type = mimetypes.guess_type(original_file_path)
            print(original_file_type)

            df = None
            # names=['ID', 'A', 'B', 'C', 'D'], header=None
            # header=0
            # encoding='CP949'
            # encoding='latin'
            if original_file_type[0] in (
                    'text/csv',
                    'text/plain'
                ):
                # load csv file from the server-stored file
                df = pd.read_csv(original_file_path, na_values=('', ), keep_default_na=True)
            elif original_file_type[0] in (
                    'application/vnd.ms-excel', # official
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # xlsx
                    'application/msexcel',
                    'application/x-msexcel',
                    'application/x-ms-excel',
                    'application/x-excel',
                    'application/x-dos_ms_excel',
                    'application/xls',
                    'application/x-xls',
                ):
                df = pd.read_excel(original_file_path, na_values=('', ), keep_default_na=True)
            elif original_file_type[0] == 'application/json':
                df = pd.read_json(original_file_path)
            elif original_file_type[0] == 'text/html':
                df = pd.read_html(original_file_path, na_values=('', ), keep_default_na=True)
            
            if df is None:
                return HttpResponse("제출 error")
            
            # print(saved_original_file.get_absolute_path(), "###")

            # get DB tuples
            mapping_info = MappingInfo.objects.filter(
                task=task,
                derived_schema_name=derived_schema
            )[0]
            # get parsing information into a dictionary
            # { 파싱전: 파싱후 }
            mapping_from_to = {
                i.parsing_column_name: i.schema_attribute.attr
                for i in MappingPair.objects.filter(
                    mapping_info=mapping_info
                )
            }

            # parse
            for key in df.columns:
                if key in mapping_from_to.keys():
                    df.rename(columns={key: mapping_from_to[key]}, inplace=True)
                else:
                    df.drop([key], axis='columns', inplace=True)

            # save the parsed file
            # parsed_file_path = os.path.join(settings.DATA_PARSED, parsedFile.__str__()) 
            parsed_file_path = os.path.join(settings.MEDIA_ROOT, parsedFile.file_original.name.replace('data_original/', 'data_parsed/'))
            df.to_csv(parsed_file_path, index=False)

            # increment submit count of Participation tuple by 1
            participation = Participation.objects.filter(
                account=submitter, task=task)[0]
            participation.submit_count += 1
            participation.save()

            # make statistic
            duplicated_tuple = len(df)-len(df.drop_duplicates())
            null_ratio = (df.isnull().sum().sum() + df.isna().sum().sum())/(len(df)*len(df.columns)
                                                ) if (len(df)*len(df.columns)) > 0 else 1
            print("###", null_ratio)
            
            # save the parsed file
            parsedFile.submit_number = participation.submit_count
            parsedFile.total_tuple = len(df)
            parsedFile.duplicated_tuple = duplicated_tuple
            parsedFile.null_ratio = null_ratio
            # grading_score=,   # TODO: should be immplemented
            # pass_state=False,
            # parsedFile.grading_end_date = datetime.now(),    # TODO: should be implemented
            parsedFile.file_parsed = parsed_file_path
            parsedFile.save()

            # TODO: data too long error
            # select @@global.sql_mode;  # SQL 설정 보기
            # TODO: remove "STRICT_TRANS_TABLES" by set command without this attribute
            # set @@global.sql_mode="ONLY_FULL_GROUP_BY,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION";
            
            # TODO: Return 부분 수정해야함
            form = UploadForm()
        # elif schema_choice_form.is_valid():

    else:
        form = UploadForm()
        # schema_choice_form = SchemaChoiceForm()
    
    parsedfile_list = user.account.parsed_submits.filter(task=task)
    total_tuple = sum(
        parsedfile.total_tuple if parsedfile.total_tuple else 0 for parsedfile in parsedfile_list
    )

    context = {
        'task': task,
        'parsedfile_list': parsedfile_list,
        'total_tuple': total_tuple,
        'file_upload_form': form,
    }
    # return redirect(reverse('collect:submitted-parsedfiles', kwargs=context))

    return render(request, 'collect/submitted_parsedfile.html', context)


# 평가된 파일 목록
class GradedfileList(View):
    def get(self, request):
        user = request.user
        parsedfiles = user.account.parsed_grades.filter(
            grading_score__isnull=False)
        return render(request, 'collect/graded_parsedfile.html', {'parsedfiles': parsedfiles})


# 할당된 파일 목록
class AllocatedfileList(View):
    def get(self, request):
        user = request.user
        parsedfiles = user.account.parsed_grades.filter(
            grading_score__isnull=True)
        now = date.today()
        context = {
            'parsedfiles': parsedfiles,
            'now': now
        }
        return render(request, 'collect/allocated_parsedfile.html', context)


# 파일 평가
def grade_parsedfile(request, pk):
    if request.method == "POST":
        form = GradeForm(request.POST)
        parsedfile = get_object_or_404(ParsedFile, pk=pk)
        if form.is_valid():
            parsedfile.grading_score = form.cleaned_data['grading_score']
            parsedfile.pass_state = form.cleaned_data['pass_state']
            parsedfile.save()
            return redirect(reverse('collect:graded-parsedfiles'))
        context = {
            'form': form,
            'parsedfile': parsedfile
        }
        context.update({'error': '0 ~ 10 사이의 숫자를 입력해주세요.'})
        return render(request, 'collect/grade.html', context)
    else:
        form = GradeForm()
        parsedfile = get_object_or_404(ParsedFile, pk=pk)
        context = {
            'form': form,
            'parsedfile': parsedfile
        }
        return render(request, 'collect/grade.html', context)


def download_parsedfile(request, pk):
    """
    docstring
    """
    parsedfile = get_object_or_404(ParsedFile, pk=pk)
    
    file_base_name = parsedfile.__str__()
    download_file_path = os.path.join(settings.JOINED_PATH_DATA_PARSED, file_base_name)
    file_name = urllib.parse.quote(file_base_name).encode('utf-8')
    
    print(file_base_name)
    print(download_file_path)
    print(file_name)

    if os.path.exists(download_file_path):
        with open(download_file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type='text/csv')
            # response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(download_file_path)[0])
            response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'%s' % file_base_name
            return response

    return grade_parsedfile(request, pk)



# 유저 검색
class UserList(View):
    def get(self, request):
        tasks = Task.objects.all()
        accounts = Account.objects.all()
        username = request.GET.get('username')
        gender = request.GET.get('gender')
        role = request.GET.get('role')
        birth1 = request.GET.get('birth1')
        birth2 = request.GET.get('birth2')
        taskname = request.GET.get('taskname')
        if username:
            accounts = accounts.filter(user__username__contains=username)
        if gender:
            accounts = accounts.filter(gender__exact=gender)
        if role:
            accounts = accounts.filter(role__exact=role)
        if birth1 and birth2:
            accounts = accounts.filter(birth__range=(birth1, birth2))
        if taskname:
            task = Task.objects.get(name=taskname)
            accounts = accounts.filter(
                participations__in=task.participations.all())
        context = {
            'accounts': accounts,
            'tasks': tasks
        }
        return render(request, 'collect/userlist.html', context)


# 유저 상세 정보
class UserDetail(View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.account.role == '제출자':
            participations = user.account.participations.all()
            return render(request, 'manager/submitter_info.html', {'participations': participations, 'user':user})
        elif user.account.role == '평가자':
            user = User.objects.get(pk=pk)
            parsedfiles = user.account.parsed_grades.filter(
                grading_score__isnull=False)
            return render(request, 'manager/graded_parsedfile.html', {'parsedfiles': parsedfiles})


def submitter(request):
    return render(request, 'collect/submitter.html')


def grader(request):
    return render(request, 'collect/grader.html')


def manager(request):
    return render(request, 'collect/manager.html')


def generateListString(iterable):
    """
    1. each element of iterable contains .__str__()
    2. use |linebreaks tag on template html file to display
    """
    text = ""
    for i in iterable:
        text += i.__str__()
        text += '\n'
    return text


"""
view functions for task
"""


def listTasks(request):
    """
    docstring
    """
    tasks = Task.objects.values()
    return render(request, 'manager/task_list.html', {
        'list_of_tasks': tasks,
    })


def showTask(request, task_id):
    """
    docstring
    """
    task = Task.objects.filter(id=task_id)[0]
    attributes = generateListString(SchemaAttribute.objects.filter(task=task))
    derived_schemas = generateListString(MappingInfo.objects.filter(task=task))

    part_in = Participation.objects.filter(task=task, admission=True)
    applied = Participation.objects.filter(task=task, admission=False)

    # count the number of tuple
    num_of_tuples = 0
    table_file = syncTotalTableFile(task)
    if table_file:
        df_table_file = pd.read_csv(table_file)
        num_of_tuples = len(df_table_file)

    return render(request, 'manager/task_select.html', {
        'task': task,
        'task_info': str(list(Task.objects.filter(id=task_id).values())),
        'task_attributes': attributes,
        'task_derived_schemas': derived_schemas,
        'num_of_tuples': num_of_tuples,
        'part_in': part_in,
        'applied': applied,
    })

def downloadAllFiles(request, task_id):
    """
    docstring
    """

    task = get_object_or_404(Task, pk=task_id)

    download_file_path = syncTotalTableFile(task)

    file_name = urllib.parse.quote((task.name+'.csv').encode('utf-8'))
    
    if os.path.exists(download_file_path):
        with open(download_file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type='text/csv')
            # response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(download_file_path)[0])
            response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'%s' % file_name
            return response

    return showTask(request, task_id)



# 관리자: 파싱데이터 시퀀스 파일 목록
def parsedfile_list(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    parsedfiles = ParsedFile.objects.filter(task=task)
    context = {
        'parsedfiles': parsedfiles,
        'count': len(parsedfiles)
    }
    return render(request, 'manager/parsedfile_list.html', context)


# 관리자: 평가자 목록
def grader_list(request, file_id):
    graders = Account.objects.filter(role='평가자')
    context = {
        'graders': graders,
        'file_id': file_id
    }
    return render(request, 'manager/grader_list.html', context)


# 관리자: 평가자 배정
def allocate_file(request, file_id, account_id):
    file = get_object_or_404(ParsedFile, pk=file_id)
    account = get_object_or_404(Account, pk=account_id)
    file.grader = account
    file.grading_end_date = date.today() + timedelta(weeks=1)
    file.save()
    return redirect('list tasks')


def createTask(request):
    """
    docstring
    """

    form = None
    task = None
    if request.method == 'POST':
        form = CreateTask(request.POST, request.FILES)
        if form.is_valid():
            # form = form.save(commit=False) # 중복 DB save를 방지
            task = form.save()
            task.activation_state = True    # TODO: basically task should be disabled when just created
            task.save()

            # return render(request, 'manager/done_task.html', {})
            return redirect('list tasks')
    else:
        form = CreateTask()

    # name = "test_task"
    # minimal_upload_frequency = 0
    # description = "test_desc"
    # original_data_description = "what is this?"

    # task = Task(
    #     name=name,
    #     minimal_upload_frequency=minimal_upload_frequency,
    #     activation_state=True,
    #     description=description,
    #     original_data_description=original_data_description
    # )

    return render(request, 'manager/task_create.html', {
        'create_task_form': form
    })


"""
view functions for attribute
"""


def listAttributes(request, task_id):
    """
    docstring
    """
    task = Task.objects.filter(id=task_id)[0]
    attributes = generateListString(SchemaAttribute.objects.filter(task=task))
    return render(request, 'manager/attribute_list.html', {
        'task_name': task.name,
        'list_of_attributes': attributes,
    })


def createAttribute(request, task_id):
    """
    docstring
    """
    form = None
    task = Task.objects.filter(id=task_id)[0]
    attribute = None

    
    # if task.activation_state:
    #     return HttpResponse("<h2>태스크가 활성화되어 있습니다!</h3>")
    
    attributes = generateListString(SchemaAttribute.objects.filter(task=task))

    if request.method == 'POST':
        form = CreateSchemaAttribute(request.POST, request.FILES)
        if form.is_valid():
            # form = form.save(commit=False) # 중복 DB save를 방지
            attribute = form.save(task)
            # attribute.task = task
            attribute.save()

            return redirect('create attribute', task_id=task_id)

    else:
        form = CreateSchemaAttribute()

    return render(request, 'manager/attribute_create.html', {
        'create_attribute_form': form,
        'list_of_attributes': attributes,
    })


"""
view functions for derived schema
"""


def listDerivedSchemas(request, task_id):
    """
    docstring
    """
    task = Task.objects.filter(id=task_id)[0]

    derived_schemas = MappingInfo.objects.filter(task=task)
    return render(request, 'manager/derived_schema_list.html', {
        'task_id': task_id,
        'task_name': task.name,
        'list_of_derived_schemas': derived_schemas,
    })


def showDerivedSchema(request, task_id, schema_id):
    """
    docstring
    """
    task = Task.objects.filter(id=task_id)[0]
    schema = MappingInfo.objects.filter(id=schema_id, task=task)[0]

    schema_info = MappingInfo.objects.filter(id=schema_id).values()[0]
    mapping_pairs = generateListString(
        MappingPair.objects.filter(mapping_info=schema))
    return render(request, 'manager/derived_schema_select.html', {
        'task_name': task.name,
        'schema_name': schema.derived_schema_name,
        'schema_info': schema_info,
        'mapping_pairs': mapping_pairs,
    })


def createDerivedSchema(request, task_id):
    """
    docstring
    """
    form = None
    task = Task.objects.filter(id=task_id)[0]
    schema = None
    if request.method == 'POST':
        form = CreateMappingInfo(request.POST, request.FILES)
        if form.is_valid():
            # form = form.save(commit=False) # 중복 DB save를 방지
            schema = form.save(task)
            # schema.task = task
            schema.save()

            return redirect('list derived schemas', task_id=task_id)

    else:
        form = CreateMappingInfo()

    return render(request, 'manager/derived_schema_create.html', {
        'create_derived_schema_form': form
    })


"""
view functions for mapping pairs
"""


def listMappingPairs(request, task_id, schema_id):
    """
    docstring
    """
    task = Task.objects.filter(id=task_id)[0]
    derived_schema = MappingInfo.objects.filter(id=schema_id, task=task)[0]

    mapping_pairs = generateListString(
        MappingPair.objects.filter(mapping_info=derived_schema))
    return render(request, 'manager/mapping_pair_list.html', {
        'task_name': task.name,
        'schema_name': derived_schema.derived_schema_name,
        'list_of_mapping_pairs': mapping_pairs,
    })


def createMappingPair(request, task_id, schema_id):
    """
    docstring
    """
    form = None
    task = Task.objects.filter(id=task_id)[0]
    derived_schema = MappingInfo.objects.filter(id=schema_id, task=task)[0]

    mapping_pairs = generateListString(
        MappingPair.objects.filter(mapping_info=derived_schema))

    mapping_pair = None
    if request.method == 'POST':
        form = CreateMappingPair(request.POST, request.FILES)
        if form.is_valid():
            # form = form.save(commit=False) # 중복 DB save를 방지
            mapping_pair = form.save(derived_schema)
            # schema.task = task
            mapping_pair.save()

            return redirect('create mapping pair', task_id=task_id, schema_id=schema_id)

    else:
        form = CreateMappingPair()

    return render(request, 'manager/mapping_pair_create.html', {
        'create_mapping_pair_form': form,
        'list_of_mapping_pairs': mapping_pairs,
    })
