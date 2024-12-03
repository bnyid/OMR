from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import OMRResult, Student
import json
import cv2
import numpy as np
from .omr_processors.main import process_omr_image
from .omr_processors.omr_data_processing import handle_image_file
from django.db.models import Q
from django.views.decorators.http import require_POST

def omr_upload(request):
    return render(request, 'omr_app/omr_upload.html')

@csrf_exempt
def omr_process(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            image = handle_image_file(image_file) # 이미지 파일이 pdf인 경우 BGR 이미지로 변환

            if image is None:
                return JsonResponse({'status': 'error', 'message': '이미지 변환 실패'}, status=400)

            result_df = process_omr_image(image)
            
            result = OMRResult.objects.create(
                exam_date=f"20{result_df['시행일'].iloc[0]}",
                class_code=result_df['반코드'].iloc[0],
                student_id=result_df['학번'].iloc[0],
                student_name=result_df['이름'].iloc[0],
                answer_sheet=image_file,
                answers=result_df.to_dict('records')
            )

            return JsonResponse({
                'status': 'success',
                'data': {
                    'id': result.id,
                    'exam_date': f"20{result_df['시행일'].iloc[0]}",
                    'class_code': result_df['반코드'].iloc[0],
                    'student_id': result_df['학번'].iloc[0],
                    'student_name': result_df['이름'].iloc[0],
                    'answers': result_df.to_dict('records')
                }
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    }, status=400)

def omr_result_list(request):
    results = OMRResult.objects.all().order_by('-exam_date', 'class_code', 'student_id')
    
    exam_date = request.GET.get('exam_date')
    class_code = request.GET.get('class_code')
    student_id = request.GET.get('student_id')
    
    if exam_date:
        results = results.filter(exam_date=exam_date)
    if class_code:
        results = results.filter(class_code=class_code)
    if student_id:
        results = results.filter(student_id=student_id)
    
    return render(request, 'omr_app/omr_result_list.html', {
        'results': results,
        'exam_dates': OMRResult.objects.dates('exam_date', 'day', order='DESC'),
        'class_codes': OMRResult.objects.values_list('class_code', flat=True).distinct()
    })

def omr_result_detail(request, result_id):
    result = get_object_or_404(OMRResult, id=result_id)
    return render(request, 'omr_app/omr_result_detail.html', {'result': result})

def student_list(request):
    students = Student.objects.all().order_by('school_type', 'grade', 'class_name', 'name')
    return render(request, 'omr_app/student_list.html', {
        'students': students,
        'grades': [1, 2, 3],
        'class_names': Student.objects.values_list('class_name', flat=True).distinct()
    })

def student_detail(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    omr_results = OMRResult.objects.filter(student_id=student_id).order_by('-exam_date')
    
    return render(request, 'omr_app/student_detail.html', {
        'student': student,
        'omr_results': omr_results
    })

@require_POST
def student_add(request):
    try:
        print("받은 데이터:", request.POST)
        print("Content-Type:", request.headers.get('Content-Type'))
        print("Method:", request.method)
        
        # POST 데이터 검증
        required_fields = ['student_id', 'name', 'class_name', 'school_type', 'grade', 
                         'school_name', 'phone_number', 'parent_phone']
        
        missing_fields = [field for field in required_fields if not request.POST.get(field)]
        if missing_fields:
            return JsonResponse({
                'status': 'error',
                'message': f'다음 필드가 누락되었습니다: {", ".join(missing_fields)}'
            })
        
        student = Student.objects.create(
            student_id=request.POST['student_id'],
            name=request.POST['name'],
            class_name=request.POST['class_name'],
            school_type=request.POST['school_type'],
            grade=int(request.POST['grade']),
            school_name=request.POST['school_name'],
            phone_number=request.POST['phone_number'],
            parent_phone=request.POST['parent_phone'],
            note=request.POST.get('note', '')
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        import traceback
        print("에러 발생:", str(e))
        print("상세 에러:", traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': str(e)})

@require_POST
def student_delete(request, student_id):
    try:
        student = get_object_or_404(Student, student_id=student_id)
        student.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# Create your views here.
