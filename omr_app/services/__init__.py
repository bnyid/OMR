from .omr_service import omr_image_to_OMRResult
from .student_service import update_students, generate_registration_number

__all__ = [
    'omr_image_to_OMRResult',
    'update_students',
    'generate_registration_number',
]


# __all__은 명시적으로 어떤 함수들이 패키지의 공개 API인지 문서화하는 효과를 가짐
