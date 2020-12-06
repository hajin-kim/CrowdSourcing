from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, get_list_or_404, redirect
from django.urls import reverse
from django.views import generic, View
from django.contrib import auth, messages
from django.contrib.auth.models import User
from django.conf import settings

from .models import Account, Task, Participation, ParsedFile, SchemaAttribute, MappingInfo, MappingPair
from .forms import LoginForm, GradeForm, CreateTask

from string import ascii_lowercase
from random import choice, randint, random
from datetime import date, datetime, timedelta
import os
import pandas as pd
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
        if User.objects.filter(username=request.POST["username"]):
            context.update({'error': "이미 존재하는 ID입니다."})
            return render(request, 'collect/signup.html', context)
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
    parsedfile_list = ParsedFile.objects.filter(task=task, pass_state=True)

    if not parsedfile_list:
        return None, "Pass된 튜플 없음"
    
    # df = pd.DataFrame(columns=attr)
    # df = pd.read_csv(os.path.join(settings.JOINED_PATH_DATA_PARSED, parsedfile_list[0].__str__()))
    file_list = []
    # print(df)
    # print("#####")

    for parsedFileObj in parsedfile_list:
        if not parsedFileObj.file_parsed is None:
            df_parsedFile = pd.read_csv(os.path.join(settings.JOINED_PATH_DATA_PARSED, parsedFileObj.__str__()), header=0, names=attr)
            # df.append(df_parsedFile, ignore_index=True)
            file_list.append(df_parsedFile)
            # print(df_parsedFile)
        # print(df)
        # print("#")

    if not os.path.exists(settings.JOINED_PATH_DATA_INTEGRATED):
        os.mkdir(settings.JOINED_PATH_DATA_INTEGRATED)
    
    download_file_path = os.path.join(settings.JOINED_PATH_DATA_INTEGRATED, task.name) + ".csv"
    df = pd.concat(file_list, axis=0, ignore_index=True)
    num_total_tuples = len(df)
    df.to_csv(download_file_path, header=attr, index=True)

    return download_file_path, num_total_tuples


# 제출자: 제출한 파일 목록 확인 및 업로드
def parsedFileListAndUpload(request, pk):
    os.makedirs(settings.JOINED_PATH_DATA_ORIGINAL, exist_ok=True)
    os.makedirs(settings.JOINED_PATH_DATA_PARSED, exist_ok=True)

    user = request.user
    task = get_object_or_404(Task, pk=pk)
    schemas = MappingInfo.objects.filter(task=task)

    if request.method == 'POST':
        submitter = Account.objects.filter(user=user)[0]
        # grader_pk = 2
        # grader = Account.objects.filter(id=grader_pk)[0]
        grader = Account.objects.filter(role="평가자")[:]
        grader = None
            
        # check if the user is participating in the task
        participation = Participation.objects.filter(
            account=submitter, task=task)
        if len(participation.values_list()) == 0:
            return HttpResponse("참여중인 태스크가 아닙니다!")
        participation = participation[0]

        mapping_info = MappingInfo.objects.get(task=task, derived_schema_name=request.POST['derived_schema'])
        
        parsedFile = ParsedFile(
            task=task,
            submitter=submitter,
            grader=grader,
            derived_schema=mapping_info,
            start_date=request.POST['start_date'],
            end_date=request.POST['end_date'],
        )
        parsedFile.file_original = request.FILES['file_original']
        parsedFile.save()
        
        original_file_path = os.path.join(settings.MEDIA_ROOT, 
            parsedFile.file_original.name)
        
        # get parsing information into a dictionary
        # { 파싱전: 파싱후 }
        mapping_from_to = {
            i.parsing_column_name: i.schema_attribute.attr
            for i in MappingPair.objects.filter(
                mapping_info=mapping_info
            )
        }

        # attr = [ attrObj.attr for attrObj in SchemaAttribute.objects.filter(task=task) ]
        # attr = list(mapping_from_to.keys())

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
            # assume that header exists
            df = pd.read_csv(original_file_path, header=0, na_values=('', '\n'), keep_default_na=True)
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
            df = pd.read_excel(original_file_path, header=0, na_values=('', ), keep_default_na=True)
        elif original_file_type[0] == 'application/json':
            df = pd.read_json(original_file_path)
        elif original_file_type[0] == 'text/html':
            df = pd.read_html(original_file_path, na_values=('', ), keep_default_na=True)
        
        if df is None:
            return HttpResponse("제출 error (file empty 등)")

        # parse
        print(df.columns)
        print('keys:', mapping_from_to.keys())
        print('values:', mapping_from_to.values())
        for key in df.columns:
            if str(key) in mapping_from_to.keys():
                df.rename(columns={key: mapping_from_to[str(key)]}, inplace=True)
                print("#", "key", key, "changed to", mapping_from_to[str(key)])
            else:
                df.drop([key], axis='columns', inplace=True)
                df.drop([str(key)], axis='columns', inplace=True)
                print("#", "key", key, "a.k.a.", str(key), "is dropped")
        
        i = 0
        for key in mapping_from_to.values():
            if str(key) not in df.columns:
                df.insert(loc=i, column=key, value=None, allow_duplicates=False)
                print("#", "key", key, "is inserted")
            # df.insert(loc=i, column=key, value=None)
            i += 1

        df = df[mapping_from_to.values()]
        print(df)

        # save the parsed file
        # parsed_file_path = os.path.join(settings.DATA_PARSED, parsedFile.__str__()) 
        base_path = os.path.join(settings.MEDIA_ROOT, parsedFile.file_original.name.replace('data_original/', 'data_parsed/'))
        parsed_file_path = os.path.splitext(base_path)[0] + '.csv'
        while os.path.exists(parsed_file_path):
            parsed_file_path = os.path.splitext(base_path)[0] + '_' + ''.join([choice(ascii_lowercase) for _ in range(randint(5, 8))]) + '.csv'
        df.to_csv(parsed_file_path, index=False)

        # increment submit count of Participation tuple by 1
        participation.submit_count += 1
        participation.save()

        # make statistic
        duplicated_tuple = len(df)-len(df.drop_duplicates())
        null_ratio = df.isnull().sum().sum()/(len(df)*len(df.columns)) if (len(df)*len(df.columns)) > 0 else 1
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
        parsedFile.file_parsed.name = os.path.basename(parsed_file_path)
        print("parsed file path:", parsed_file_path)
        parsedFile.save()

        # TODO: data too long error
        # select @@global.sql_mode;  # SQL 설정 보기
        # TODO: remove "STRICT_TRANS_TABLES" by set command without this attribute
        # set @@global.sql_mode="ONLY_FULL_GROUP_BY,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION";
        
        return redirect(reverse('collect:submitted-parsedfiles', kwargs={'pk': pk}))
    
    
    parsedfile_list = user.account.parsed_submits.filter(task=task)
    total_tuple = sum(
        parsedfile.total_tuple if parsedfile.total_tuple else 0 for parsedfile in parsedfile_list
    )

    context = {
        'task': task,
        'schemas': schemas,
        'parsedfile_list': parsedfile_list,
        'total_tuple': total_tuple,
        # 'file_upload_form': form,
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

    # return grade_parsedfile(request, pk)
    return HttpResponse("파싱 데이터 시퀀스 파일 다운로드 에러. 지속될 경우 관리자에게 문의해주세요.")



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
    _, num_of_tuples = syncTotalTableFile(task)
    # if table_file:
    #     df_table_file = pd.read_csv(table_file)
    #     num_of_tuples = len(df_table_file)

    return render(request, 'manager/task_select.html', {
        'task': task,
        # 'task_info': str(list(Task.objects.filter(id=task_id).values())),
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

    download_file_path, _ = syncTotalTableFile(task)

    file_name = urllib.parse.quote((task.name+'.csv').encode('utf-8'))
    
    if download_file_path is None:
        return redirect('show task', task_id=task_id)
    if os.path.exists(download_file_path):
        with open(download_file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type='text/csv')
            # response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(download_file_path)[0])
            response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'%s' % file_name
            return response
    
    return redirect('show task', task_id=task_id)



# 관리자: 파싱데이터 시퀀스 파일 목록
def parsedfile_list(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    parsedfiles = ParsedFile.objects.filter(task=task)
    context = {
        'parsedfiles': parsedfiles,
        'count': len(parsedfiles),
        'task_id': task_id,
    }
    return render(request, 'manager/parsedfile_list.html', context)


# 관리자: 평가자 목록
def grader_list(request, task_id, file_id):
    graders = Account.objects.filter(role='평가자')
    context = {
        'graders': graders,
        'file_id': file_id,
        'task_id': task_id,
    }
    return render(request, 'manager/grader_list.html', context)


# 관리자: 평가자 배정
def allocate_file(request, task_id, file_id, account_id):
    file = get_object_or_404(ParsedFile, pk=file_id)
    account = get_object_or_404(Account, pk=account_id)
    file.grader = account
    file.grading_end_date = date.today() + timedelta(weeks=1)
    file.save()
    return redirect('parsedfile list', task_id=task_id)


def createTask(request):
    """
    docstring
    """

    form = None
    if request.method == 'POST':
        form = CreateTask(request.POST, request.FILES)
        if form.is_valid():
            # if not Task.objects.filter(name=form.name):
            # task = form.save(commit=False) # 중복 DB save를 방지
            form.save()
            # task.activation_state = True
            # TODO: basically task should be disabled when just created
            # TODO: now this is in forms.py
            # task.save()

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


def endTask(request, task_id):
    """
    docstring
    """
    
    task = Task.objects.get(id=task_id)
    task.activation_state = False
    task.save()

    return redirect('show task', task_id=task_id)


"""
view functions for attribute
"""
def listAttributes(request, task_id, error_message=None):
    """
    docstring
    """
    task = Task.objects.get(id=task_id)
    attributes = generateListString(SchemaAttribute.objects.filter(task=task))

    context = {
        'task_name': task.name,
        'task_id': task_id,
        'list_of_attributes': attributes,
    }

    # prohibit duplication
    if error_message:
        context.update(error_message)
    return render(request, 'manager/attribute_list.html', context)


def createAttribute(request, task_id):
    """
    docstring
    """
    task = Task.objects.get(id=task_id)
    
    # if task.activation_state:
    #     return HttpResponse("<h2>태스크가 활성화되어 있습니다!</h3>")

    if request.method == 'POST':
        attr = request.POST['attr']

        # prohibit duplication
        error_message = {}
        if SchemaAttribute.objects.filter(
            task=task,
            attr=attr
        ):
            error_message.update({'error_at_attr': "속성이 이미 존재합니다."})
        if error_message:
            return listAttributes(request, task_id, error_message)
        
        # create
        attribute = SchemaAttribute(
            task=task,
            attr=attr
        )
        attribute.save()

    return redirect('list attributes', task_id=task_id)

"""
view functions for derived schema
"""
def listDerivedSchemas(request, task_id, error_message=None):
    """
    docstring
    """
    task = Task.objects.get(id=task_id)
    derived_schemas = MappingInfo.objects.filter(task=task)

    context = {
        'task_id': task_id,
        'task_name': task.name,
        'list_of_derived_schemas': derived_schemas,
    }

    # prohibit duplication
    if error_message:
        context.update(error_message)
    return render(request, 'manager/derived_schema_list.html', context)


def showDerivedSchema(request, task_id, schema_id):
    """
    docstring
    """
    task = Task.objects.get(id=task_id)
    schema = MappingInfo.objects.get(id=schema_id, task=task)

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
    task = Task.objects.get(id=task_id)
    if request.method == 'POST':
        derived_schema_name=request.POST['derived_schema_name']
        
        # prohibit duplication
        error_message = {}
        if MappingInfo.objects.filter(
            task=task,
            derived_schema_name=derived_schema_name,
        ):
            error_message.update({'error_at_derived_schema_name': "파생 스키마가 이미 존재합니다."})
        if error_message:
            return listDerivedSchemas(request, task_id, error_message)

        # create
        schema = MappingInfo(
            task=task,
            derived_schema_name=derived_schema_name
        )
        schema.save()

    return redirect('list derived schemas', task_id=task_id)


"""
view functions for mapping pairs
"""


def listMappingPairs(request, task_id, schema_id, error_message=None):
    """
    docstring
    """
    task = Task.objects.get(id=task_id)
    derived_schema = MappingInfo.objects.get(id=schema_id, task=task)

    mapping_pairs = generateListString(MappingPair.objects.filter(mapping_info=derived_schema))
    schema_attribute_list = SchemaAttribute.objects.filter(task=task)

    context = {
        'task_id': task_id,
        'task_name': task.name,
        'schema_id': schema_id,
        'schema_name': derived_schema.derived_schema_name,
        'schema_attribute_list': schema_attribute_list,
        'list_of_mapping_pairs': mapping_pairs,
    }

    # prohibit duplication
    if error_message:
        context.update(error_message)
    return render(request, 'manager/mapping_pair_list.html', context)


def createMappingPair(request, task_id, schema_id):
    """
    docstring
    """
    task = Task.objects.get(id=task_id)
    derived_schema = MappingInfo.objects.get(id=schema_id, task=task)

    if request.method == 'POST':
        schema_attribute = SchemaAttribute.objects.get(task=task, attr=request.POST['attr'])
        parsing_column_name = request.POST['parsing_column_name']
        
        # prohibit duplication
        error_message = {}
        if MappingPair.objects.filter(
            mapping_info=derived_schema,
            parsing_column_name=parsing_column_name,
        ):
            error_message.update({'error_at_parsing_column_name': "파생 스키마의 컬럼 이름이 이미 매핑되었습니다."})
        if MappingPair.objects.filter(
            mapping_info=derived_schema,
            schema_attribute=schema_attribute,
        ):
            error_message.update({'error_at_schema_attribute': "원본 스키마의 컬럼이 이미 매핑되었습니다."})
        if error_message:
            return listMappingPairs(request, task_id, schema_id, error_message)
        
        # create
        mapping_pair = MappingPair(
            mapping_info=derived_schema,
            schema_attribute=schema_attribute,
            parsing_column_name=parsing_column_name,
        )
        mapping_pair.save()

    return redirect('list mapping pairs', task_id=task_id, schema_id = schema_id)

