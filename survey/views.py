from datetime import datetime,timezone
import re
import json
import logging

from django.shortcuts import render
from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .models import Student, OneSurvey
from .forms import LoginForm

from Qute.settings import \
QUS_LARGE, QUS_SMALL, FEEDBACK_QUESTIONS, MAX_SCORE_LARGE, MAX_SCORE_SMALL, MAX_SUBMIT_COUNT

logger = logging.getLogger('django')

def is_integer(s):
    try:
        int(s)
        return True
    except Exception:
        return False

legal_prefix = [
    'PB',
    'SA','SB','SM','SE','SG','SI','SJ',
    'BA','BO','BZ',
    'JL','SC','BC',
    'PL','SL','BL',
    'CJ','CS','CB'
]

def is_id_valid(student_id):
    if len(student_id) != 10:
        return False
    prefix = student_id[:2].upper()
    if prefix not in legal_prefix:
        return False
    year = student_id[2:4]
    if not (year.isdigit() and 17 <= int(year) <= 25):
        return False
    if not student_id[4:].isdigit():
        return False
    return True

re_name = re.compile(r'^([\u00b7\u0387\u16eb\u2022\u2027\u2219\u22c5\u2e31\u30fb\uff65\u3007\u3400-\u9fff\uf900-\ufad9\U00020000-\U000323af]{2,}|[a-zA-Z\.\s]{3,})$')
def is_name_valid(name):
    return re_name.fullmatch(name) is not None

def my_login(request, student):
    student.login_count += 1
    student.save()
    logger.info(f'{student.username}-"{student.name}"第{student.login_count}次登录')
    return login(request, student)
    
def login_view(request):
    # html or json
    if request.method == 'POST':

        # form valid
        form = LoginForm(request.POST)
        if not form.is_valid():
            return JsonResponse({ 'err': '验证码错误，请重试或刷新页面'})
        
        # input valid
        student_id = form.cleaned_data['id']
        student_name = form.cleaned_data['name']
        if is_id_valid(student_id) and is_name_valid(student_name):

            #输入合法
            student_id = student_id.upper()
            student = Student.objects.filter(username=student_id).first()

            if student is None:
                student = Student.objects.create_user(username=student_id, name=student_name)
            else:
                if student.name != student_name:
                    from .models import OldNames
                    OldNames.objects.create(student=student, name=student.name, murder_login=student.login_count + 1)
                    logger.warning(f'{student.username} 第{student.login_count+1}次登录时使用了不同的名字（"{student.name}"->"{student_name}"）')
                    student.name = student_name
                    
            
            student.save()
            my_login(request, student)
            return JsonResponse({'err': 0})
        
        else:#输入不合法

            now = datetime.now(timezone.utc).timestamp()
            dt = now - request.session.get('last_try', now)
            request.session['last_try'] = now

            if not 40 < dt < 300:
                logger.warning(f'阻止了以id:"{student_id}"，名字:"{student_name}"的登录')
                return JsonResponse({'err': '请检查输入内容或与工作人员确认身份'})

            n = 1 + int(Student.objects.filter(username__contains="TMP").order_by('-username').first().username[3:])
            student = Student.objects.create_user(username=f'TMP{n:04d}', name=f'{student_id}\t{student_name}')
            
            logger.warning(f'创建了临时用户{student.username}')
            my_login(request, student)
            request.session['last_try'] = now
            return JsonResponse({'err': 0})
        
    else:
        if request.user.is_authenticated:
            return HttpResponseRedirect('/result/')
        else:
            return render(request, 'login.html', {\
                'form': LoginForm(),"max_count": MAX_SUBMIT_COUNT})

@csrf_exempt
def logout_view(request):
    if request.method != 'POST' or not request.user.is_authenticated or request.body != b'logout':
        raise Http404
    student = request.user
    logout(request)
    logger.info(f'{student.username}-"{student.name}"退出了其第{student.login_count}次登录')
    return JsonResponse({'err': 0})
    
#survey_type = 'small'
survey_type = 'large'
def is_pass(sur):
    if sur.is_small:
        return sur.score >= MAX_SCORE_SMALL * 0.9
    else:
        return sur.score >= MAX_SCORE_LARGE * 0.6
    
@login_required
def result_view(request):

    student = request.user
    surs = OneSurvey.objects.filter(student=student).order_by('-score')
    sub_count = surs.count()
    
    if request.method == 'POST':
        if request.body != b'retry':
            raise Http404
        if sub_count >= MAX_SUBMIT_COUNT:
            return JsonResponse({'err': '重试次数已用完'})
        request.session['type'] = survey_type
        return JsonResponse({'err': 0})
    else:
        if request.session.get('type') is not None:
            return HttpResponseRedirect('/survey/')
        if sub_count == 0:
            request.session['type'] = survey_type
            return HttpResponseRedirect('/survey/')
            
        username = student.username
        name = student.name
        if username[:3] == 'TMP':
            username, name = name.split()
        return render(request, 'result.html', {\
            'username': username,\
            'name': name,\
            'is_pass':is_pass(surs.first()),\
            'remain': max(0,MAX_SUBMIT_COUNT - sub_count)\
        })

def qus2json(qus):
    js = []
    for q in qus:
        js.append({
            "question": q['question'],
            "choices": [line['text'] for line in q['choices']],
        })
    return json.dumps(js, ensure_ascii=False)

@login_required
def survey_view(request, page = None):

    if request.method != 'GET':
        raise Http404

    # 提交次数判断
    student = request.user
    sub_count = OneSurvey.objects.filter(student=student).count()
    if sub_count >= MAX_SUBMIT_COUNT:
        request.session.pop('type')
        return HttpResponseRedirect('/result/')
    
    #问卷类型判断
    r_type = request.session.get('type', None)
    if r_type is None:
        return HttpResponseRedirect('/result/')
    if r_type == 'large':
        qpages = QUS_LARGE
        page_count = len(QUS_LARGE)
        tpl_path = 's-large/'
    else:
        qpages = QUS_SMALL
        page_count = len(QUS_SMALL)
        tpl_path = 's-small/'

    # url page参数判断
    if page is None or not is_integer(page) or int(page) == 0:
        return HttpResponseRedirect('/survey/1/')
    page = int(page)
    if page > page_count:
        return HttpResponseRedirect(f'/survey/{page_count}/')
    elif page < 0:
        return HttpResponseRedirect(f'/survey/{page % page_count + 1}/')
    
    return render(request, tpl_path+f'p{page}.html',{\
        'name': student.name,\
        'current_page': page,\
        'total_pages': page_count,\
        'questions': qus2json(qpages[page - 1])})

chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
def ans2str(page):
    astr = ""
    for q in page:
        abit = 0
        for c in q:
            abit|= 1 << int(c)
        astr += chars[abit]
    return astr

def strlist_strip(lst):
    for i in range(len(lst) - 1, -1, -1):
        if lst[i] != "":
            return lst[:i + 1]
    return None

@login_required
def feedback_view(request):
    # 提交次数判断
    student = request.user
    sub_count = OneSurvey.objects.filter(student=student).count()
    if sub_count >= MAX_SUBMIT_COUNT:
        request.session.pop('type')
        return HttpResponseRedirect('/result/') 
    
    #问卷类型判断
    r_type = request.session.get('type', None)
    if r_type is None:
        return HttpResponseRedirect('/result/')
    if r_type == 'large':
        qpages = QUS_LARGE
        page_count = len(QUS_LARGE)
    else:
        qpages = QUS_SMALL
        page_count = len(QUS_SMALL)

    # 提交处理
    if request.method == 'POST':
        if request.headers.get('Content-Type') != 'application/json' or len(request.body) > 9999:
            logger.warning(f'阻止{student.username}-"{student.name}"提交巨大的数据包')
            raise Http404

        try:
            data = json.loads(request.body)
            score = 0
            answers = []
            for i in range(page_count):
                for j in range(len(qpages[i])):
                    for choice in data['pn'][i][j]:
                        score += qpages[i][j]['choices'][int(choice)]['value']
                answers.append(ans2str(data['pn'][i][:len(qpages[i])]))
            feedbacks = strlist_strip(data['fb'])
        except Exception:
            logger.warning(f'{student.username}-"{student.name}"提交了错误的数据')
            return JsonResponse({'err': '数据格式有误，请重试'})
        
        OneSurvey.objects.create(\
                student=student, \
                submit_login=student.login_count, \
                is_small=(r_type=='small'), \
                score=score,
                answers=answers,
                feedbacks=feedbacks
        )
        request.session.pop('type')
        logger.info(f'{student.username}-"{student.name}"第{sub_count+1}次提交问卷，得分{score}')
        return JsonResponse({'err': 0})
    
    return render(request, 'feedback.html', {\
        'name': student.name,\
        'remain': max(0,MAX_SUBMIT_COUNT - sub_count),\
        'fbquestions': FEEDBACK_QUESTIONS
    })

def control_view(request):
    global survey_type

    if not request.user.is_authenticated:
        logger.warning(f'未登录者尝试访问控制台')
        raise Http404

    if not request.user.is_superuser:
        student = request.user
        logger.warning(f'{student.username}-"{student.name}"尝试访问控制台')
        raise Http404
    
    if request.method == 'POST':
        if request.body == b'large':
            survey_type = 'large'
            return JsonResponse({'err': 0})
        elif request.body == b'small':
            survey_type = 'small'
            return JsonResponse({'err': 0})
        else:
            raise Http404
    
    user_count = Student.objects.count()-2
    all_surs = OneSurvey.objects.all()
    
    fbd_surveys = OneSurvey.objects.filter(feedbacks__isnull=False).order_by('-score')
    new_surveys = all_surs.order_by('-submit_time')[:7]

    all_fbd_surveys = []
    part_fbd_surveys = []

    for sur in fbd_surveys:
        if len(sur.feedbacks) >= len(FEEDBACK_QUESTIONS):
            all_fbd_surveys.append(sur)
        else:
            part_fbd_surveys.append(sur)

    fail_surveys = []
    for sur in all_surs:
        if not is_pass(sur):
            fail_surveys.append(sur)

    logger.info(f'{request.user.username} 访问了控制台')

    return render(request, 'control.html', {\
        'is_large': survey_type=='large',\
        'user_count': user_count,\
        'sur_count': all_surs.count(),\
        'fbd_count': fbd_surveys.count(),\
        'all_fbd_count': len(all_fbd_surveys),\
        'max_small':MAX_SCORE_SMALL,\
        'max_large':MAX_SCORE_LARGE,\
        'all_fbd_surveys': all_fbd_surveys,\
        'part_fbd_surveys': part_fbd_surveys,\
        'new_surveys': new_surveys,\
        'fail_surveys':fail_surveys})

def strGetSub(a,i):
    try:
        return a[i]
    except Exception:
        return ""

def viewsur_view(request, sur_id):
    if not request.user.is_authenticated:
        logger.warning(f'未登录者尝试访问控制台')
        raise Http404

    if not request.user.is_superuser:
        student = request.user
        logger.warning(f'{student.username}-"{student.name}"尝试访问控制台')
        raise Http404
    
    sur = OneSurvey.objects.filter(id=int(sur_id)).first()
    if sur is None:
        raise Http404
    all_surs = OneSurvey.objects.filter(student=sur.student).order_by('id')
    
    if sur.is_small:
        qpages = QUS_SMALL
        max_score = MAX_SCORE_SMALL
    else:
        qpages = QUS_LARGE
        max_score = MAX_SCORE_LARGE
    
    pn = []
    ans = sur.answers

    for pindex,page in enumerate(qpages):
        for qindex,q in enumerate(page):
            pn.append({
                "question": q['question'],
                "choices": [f"☐［<code>{line['value']:+2}</code>］{line['text']}" for line in q['choices']],
            })

            try:
                abit = chars.index(ans[pindex][qindex])
            except Exception:
                abit = 0
            
            i = 0
            while abit > 0:
                if abit & 1:
                    pn[-1]['choices'][i] = '☑' + pn[-1]['choices'][i][1:]
                abit >>= 1
                i += 1

    fb = [{"q":q, "a": strGetSub(sur.feedbacks, qindex)} for qindex,q in enumerate(FEEDBACK_QUESTIONS)]

    logger.info(f'{request.user.username} 查看了问卷{sur.id}，提交者为 {sur.student.username}-"{sur.student.name}"')
    return render(request, 'surview.html', {\
        'survey': sur,\
        'max_score': max_score,\
        'all_surveys': all_surs,\
        'pn': pn,\
        'fb': fb})