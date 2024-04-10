from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from django.contrib import messages
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from exam.models.allmodels import (
    Course,
    UploadVideo,
    UploadReadingMaterial,
    CourseStructure,
    CourseEnrollment,
    Quiz,
    Question,
)
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
# from exam.models.coremodels import *
from exam.serializers.createcourseserializers import (
    ActivateCourseSerializer,
    CourseSerializer, 
    CourseStructureSerializer,
    CreateChoiceSerializer,
    InActivateCourseSerializer, 
    UploadReadingMaterialSerializer, 
    UploadVideoSerializer, 
    QuizSerializer, 
    CreateCourseSerializer,
    CreateUploadReadingMaterialSerializer,
    CreateUploadVideoSerializer,
    CreateQuizSerializer,
    CreateQuestionSerializer,
)
import pandas as pd # type: ignore


class CreateCourseView(APIView):
    """
        view to used for creating a course instance.especially version 1 courses
        triggers with POST request.
        should be allowed for only [super admin].

        table : Course
        
        in request body:
                    title , summary 

        while creating instance :
                    # slug = auto generated by pre_save()
                    title = request body
                    summary = request body
                    created_at = updated_at = models.DateTimeField(auto_now=True)
                    active = False
                    original_course = null (as it is original course itself)
                    version_number = 1
        and instance is saved
    """
    def post(self, request, *args, **kwargs):        
        # Extract data from request body
        data = request.data
        
        # Create new course instance
        serializer = CreateCourseSerializer(data=data)
        if serializer.is_valid():
            # Set additional fields
            serializer.validated_data['active'] = False
            serializer.validated_data['original_course'] = None
            serializer.validated_data['version_number'] = 1
            
            # Save the instance
            course = serializer.save()
            
            return Response({"message": "Course created successfully", "course_id": course.pk}, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class CreateReadingMaterialView(APIView):
    """
        view to create reading material inside a course.
        triggers with POST request.
        should be allowed for only [super admin].
        
        in URL : course_id  in which we are inputting the content will be passed
        
        table : UploadReadingMaterial
        
        if course.original_course is null :
            while creating instance :
                        title = request body
                        courses = id in url
                        reading_content = request body
                        uploaded_at = updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
            and instance is saved
        if if course.original_course is not null :
            while creating instance :
                        title = request body
                        courses = id in url
                        reading_content = request body
                        uploaded_at = updated_at = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
            and instance is saved
            and 
            in CourseStructure table, make new instance with :
                    course = in url
                    order_number = filter last entry allocated with this course in courseStructure table and it's order number , and increment it by 1 for here
                    content_type = reading
                    content_id = pk of newly created instance of reading material
            
    """
    def post(self, request, course_id, *args, **kwargs):
        # Check if course exists
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        # Check if the course is active
        if course.active:
            return Response({"error": "Course is active, cannot proceed"}, status=status.HTTP_403_FORBIDDEN)
        
        # Extract data from request body
        data = request.data
        
        # Validate and save reading material
        serializer = CreateUploadReadingMaterialSerializer(data=data)
        if serializer.is_valid():
            # Set additional fields
            serializer.validated_data['courses'] = [course_id]
            
            # Save the reading material instance
            reading_material = serializer.save()
            
            # If original_course is null, only save reading material
            if course.original_course is None:
                return Response({"message": "Reading material created successfully"}, status=status.HTTP_201_CREATED)
            else:
                # If original_course is not null, also create a CourseStructure entry
                try:
                    last_order_number = CourseStructure.objects.filter(course=course).latest('order_number').order_number
                except CourseStructure.DoesNotExist:
                    last_order_number = 0
                
                # Create new CourseStructure instance
                course_structure_data = {
                    'course': course_id,
                    'order_number': last_order_number + 1,
                    'content_type': 'reading',
                    'content_id': reading_material.pk
                }
                course_structure_serializer = CourseStructureSerializer(data=course_structure_data)
                if course_structure_serializer.is_valid():
                    course_structure_serializer.save()
                    return Response({"message": "Reading material created successfully"}, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": course_structure_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class CreateVideoView(APIView):
    """
        view to create video inside a course.
        triggers with POST request.
        should be allowed for only [super admin].

        in URL : course_id in which we are inputting the content will be passed
        
        table :  UploadVideo

        if course.original_course is null :
            while creating instance :
                    title = request body
                    slug = auto generated by pre_save
                    courses = id in url
                    video = request body
                    summary = request body
                    uploaded_at = auto now
            and instance is saved
        if if course.original_course is not null :
            while creating instance :
                    title = request body
                    slug = auto generated by pre_save
                    courses = id in url
                    video = request body
                    summary = request body
                    uploaded_at = auto now
            and instance is saved
            and 
            in CourseStructure table, make new instance with :
                    course = in url
                    order_number = filter last entry allociated with this course in courseStructure table and it's order number , and increment it by 1 for here
                    content_type = video
                    content_id = pk of newly created instance of video 
            
    """
    def post(self, request, course_id, *args, **kwargs):

        # Check if course exists
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        # Check if the course is active
        if course.active:
            return Response({"error": "Course is active, cannot proceed"}, status=status.HTTP_403_FORBIDDEN)
        
        # Extract data from request body
        data = request.data
        
        # Validate and save video
        serializer = CreateUploadVideoSerializer(data=data)
        if serializer.is_valid():
            # Set additional fields
            serializer.validated_data['courses'] = [course_id]
            
            # Save the video instance
            video = serializer.save()
            
            # If original_course is null, only save video
            if course.original_course is None:
                return Response({"message": "Video created successfully"}, status=status.HTTP_201_CREATED)
            else:
                # If original_course is not null, also create a CourseStructure entry
                try:
                    last_order_number = CourseStructure.objects.filter(course=course).latest('order_number').order_number
                except CourseStructure.DoesNotExist:
                    last_order_number = 0
                
                # Create new CourseStructure instance
                course_structure_data = {
                    'course': course_id,
                    'order_number': last_order_number + 1,
                    'content_type': 'video',
                    'content_id': video.pk
                }
                course_structure_serializer = CourseStructureSerializer(data=course_structure_data)
                if course_structure_serializer.is_valid():
                    course_structure_serializer.save()
                    return Response({"message": "Video created successfully"}, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": course_structure_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class CreateQuizView(APIView):
    """
        view to create quiz inside a course.
        triggers with POST request.
        should be allowed for only [super admin].
        
        in URL : course_id in which we are inputting the content will be passed
        
        table : Quiz

        if course.original_course is null :
            while creating instance :
                    courses = id in url
                    title = request body
                    slug = auto generated by pre_save
                    random_order = request body
                    description = request body
                    answers_at_end = request body
                    exam_paper = t/f from request body
                    pass_mark = request body
                    created_at = updated_at = models.DateField(auto_now=True)
                    active = True by default
            and instance is saved
        if if course.original_course is not null :
            while creating instance :
                    courses = id in url
                    title = request body
                    slug = auto generated by pre_save
                    description = request body
                    answers_at_end = request body
                    exam_paper = t/f from request body
                    pass_mark = request body
                    created_at = updated_at = models.DateField(auto_now=True)
                    active = True by default
            and instance is saved
            and 
            in CourseStructure table, make new instance with :
                    course = in url
                    order_number = filter last entry allociated with this course in courseStructure table and it's order number , and increment it by 1 for here
                    content_type = quiz
                    content_id = pk of newly created instance of quiz 
    """
    def post(self, request, course_id, *args, **kwargs):
        # Check if course exists
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        # Check if the course is active
        if course.active:
            return Response({"error": "Course is active, cannot proceed"}, status=status.HTTP_403_FORBIDDEN)
        
        # Extract data from request body
        data = request.data
        
        # Validate and save quiz
        requested_data = request.data.copy()
        requested_data['courses'] = [course_id]
        serializer = QuizSerializer(data=requested_data)
        if serializer.is_valid():
            # Set additional fields
            # serializer.validated_data['courses'] = [course_id]
            
            # Save the quiz instance
            quiz = serializer.save()
            # quiz.courses.add(course)
            
            # If original_course is null, only save quiz
            if course.original_course is None:
                return Response({"message": "Quiz created successfully"}, status=status.HTTP_201_CREATED)
            else:
                # If original_course is not null, also create a CourseStructure entry
                try:
                    last_order_number = CourseStructure.objects.filter(course=course).latest('order_number').order_number
                except CourseStructure.DoesNotExist:
                    last_order_number = 0
                
                # Create new CourseStructure instance
                course_structure_data = {
                    'course': course_id,
                    'order_number': last_order_number + 1,
                    'content_type': 'quiz',
                    'content_id': quiz.pk
                }
                course_structure_serializer = CourseStructureSerializer(data=course_structure_data)
                if course_structure_serializer.is_valid():
                    course_structure_serializer.save()
                    return Response({"message": "Quiz created successfully"}, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": course_structure_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# TODO: if a instance with similar course id , content_type, content_id and order_number then skip mapping that instance again.
class CreateCourseStructureForCourseView(APIView):
    """
        [SHOULD BE USED FOR NEW ENTRY IN COURSE STRUCTURE TABLE RATHER THAN EDITING EXISTNG ONES]
        view is used to create instances in course structure table.
        triggers with POST request.
        should be allowed for only [super admin].
        
        in URL : course_id in which we are inputting the content will be passed
        
        table : CourseStructure
        
        while creating instance :
                    course = in url
                    order_number = in request body [list]
                    content_type = in request body [list]
                    content_id = in request body [list]
    """
    '''
    how will we do it :
                    first check if len of order_number = content_type = content_id list is same that is passed in request body
                    for course id passed in url , 
                    if :
                                        course = 3
                    order_number = [1,2,3]
                    content_type = [reading, video , quiz]
                    content_id = [12,34,2]
                    
                    table will be like :
                    id course order_number content_type content_id
                    1 3 1 reading 12
                    2 3 2 video 34
                    3 3 3 quiz 2
                    set will be filled.
    '''
    def post(self, request, course_id, *args, **kwargs):
        # Check if course exists
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if the course is active
        if course.active:
            return Response({"error": "Course is active, cannot proceed"}, status=status.HTTP_403_FORBIDDEN)
        
        # Extract data from request body
        order_numbers = request.data.get('order_number', [])
        content_types = request.data.get('content_type', [])
        content_ids = request.data.get('content_id', [])
        
        # Check if lengths of lists are same
        if len(order_numbers) != len(content_types) or len(content_types) != len(content_ids):
            return Response({"error": "Length of order_number, content_type, and content_id lists must be the same"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create CourseStructure instances
        new_created_course_structure = []
        course_structure_data = []
        existing_course_structure_data = []
        edited_existing_course_structure_data = []
        
        for order_number, content_type, content_id in zip(order_numbers, content_types, content_ids):
            # Check if an instance with similar course_id, content_type, content_id, and order_number exists
            instance_exists = CourseStructure.objects.filter(course=course_id, content_type=content_type, content_id=content_id, order_number=order_number).exists()
            if instance_exists:
                data = {
                    'course': course_id,
                    'order_number': order_number,
                    'content_type': content_type,
                    'content_id': content_id
                }
                existing_course_structure_data.append(data)
                course_structure_data.append(data)
                # Skip mapping this instance
                continue
            
            # Check if there's an existing instance with the same content_id and content_type but different order_number
            existing_instance = CourseStructure.objects.filter(course=course_id, content_type=content_type, content_id=content_id).first()
            if existing_instance:
                # Update the order_number
                existing_instance.order_number = order_number
                existing_instance.save()
                data = {
                    'course': course_id,
                    'order_number': order_number,
                    'content_type': content_type,
                    'content_id': content_id
                }
                edited_existing_course_structure_data.append(data)
                course_structure_data.append(data)
            else:
                # Create a new instance
                data = {
                    'course': course_id,
                    'order_number': order_number,
                    'content_type': content_type,
                    'content_id': content_id
                }
                new_created_course_structure.append(data)
                course_structure_data.append(data)
        
        # Save new instances
        serializer = CourseStructureSerializer(data=new_created_course_structure, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Course structure created successfully", 
                            "existing_record": existing_course_structure_data,
                            "edited_records" : edited_existing_course_structure_data,
                            "new_records": new_created_course_structure,
                            "all_record": course_structure_data
                            }, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class CreateQuestionView(APIView):
    """
        view to create the instance of question inside quiz
        triggers with POST request.
        in URL : course_id and quiz_id in which we are inputting the content will be passed
        
        if course in url is active :
                forbidden for any further action
        if course is not active:
                        if course.original_course is null :
                            while creating instance of question:
                                quiz = from url
                                figure = request body
                                content = request body
                                explanation = request body
                                choice_order = request body
                                active = false by default
            and instance is saved
                    if course.original_course is not null :
                        while creating instance :
                                if quiz in url is related with courses other than that in url :
                                                create new instance of quiz using data of instance of quiz in url for course for in url
                                                make sure that new instance of quiz all questions in relation with it which were with quiz in url
                                                and add new instance of question
                                                    quiz = newly created quiz instance
                                                    figure = request body
                                                    content = request body
                                                    explanation = request body
                                                    choice_order = request body
                                                    active = false by default
                                            and instance is saved 
                                            and in CourseStructure table, do editing , for content id as quiz id , and content_type as quiz for course in url change the quiz id to id of new quiz's instance's id.
                                    make sure this new quiz instance of quiz creation and updating course structure is done  if a new instance of question is actually created, with some data in it.
                                if quiz in url is only in relation with course in url :
                                                while creating instance of question:
                                                quiz = from url
                                                figure = request body
                                                content = request body
                                                explanation = request body
                                                choice_order = request body
                                                active = false by default
    """
    def post(self, request, course_id, quiz_id, *args, **kwargs):
        try:
            # Check if the course is active
            course = Course.objects.get(pk=course_id)
            if course.active:
                return Response({"error": "Forbidden: The course is active"}, status=status.HTTP_403_FORBIDDEN)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        # Extract data from request body
        data = request.data
        

        # Check if the quiz is related to other courses
        related_courses_count = Quiz.objects.exclude(courses__pk=course_id).filter(pk=quiz_id).count()

        if related_courses_count > 0:
            # Create a new instance of quiz and add the question
            new_quiz = self.create_new_quiz_instance(course_id, quiz_id, data)
            if new_quiz is not None:
                # Update the quiz_id in the course structure
                self.update_course_structure(course_id,quiz_id, new_quiz.id)
                return Response({"message": "Question created successfully"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "Failed to create new quiz instance"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Add the question to the existing quiz
            serializer = CreateQuestionSerializer(data=data)
            if serializer.is_valid():
                serializer.save(quizzes=[quiz_id])
                return Response({"message": "Question created successfully"}, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create_new_quiz_instance(self, course_id, quiz_id, data):
        try:
            with transaction.atomic():
                # Retrieve the existing quiz
                existing_quiz = Quiz.objects.get(pk=quiz_id)

                # Create a new instance of quiz with the same data
                new_quiz = Quiz.objects.create(
                    title=existing_quiz.title,
                    description=existing_quiz.description,
                    answers_at_end=existing_quiz.answers_at_end,
                    exam_paper=existing_quiz.exam_paper,
                    single_attempt=existing_quiz.single_attempt,
                    pass_mark=existing_quiz.pass_mark
                )
                new_quiz.courses.set([course_id])
                
                related_questions = existing_quiz.questions.all()
                new_quiz.questions.set(related_questions)

                serializer = CreateQuestionSerializer(data=data)
                if serializer.is_valid():
                    serializer.save(quizzes=[new_quiz.pk])
                    return new_quiz
                else:
                    new_quiz.delete()  # Rollback if question creation fails
                    return None
        except Quiz.DoesNotExist:
            return None

    def update_course_structure(self, course_id, old_quiz_id, new_quiz_id):
        # Update CourseStructure entries with the new quiz id
        CourseStructure.objects.filter(course=course_id ,content_type='quiz',content_id=old_quiz_id ).update(content_id=new_quiz_id)

class CreateChoiceView(APIView):
    """
        view to create choices in choice model for question
        triggers with POST request
        in URL : question_id in which we are inputting the content will be passed.
        while creating instance :
                    question = in url 
                    choice = request body
                    correct = request body
    """
    def post(self, request, question_id, *args, **kwargs):
        try:
            question = Question.objects.get(pk=question_id)
        except Question.DoesNotExist:
            return Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CreateChoiceSerializer(data=request.data, context={'question_id': question_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActivateCourseView(APIView):
    """
        view to activate the course.
        trigger with POST request.
        in URL : course_id of selected instance.
        table : Course
        if original_course field is null for this course_id 's instance:
        updating instance field:
                    change active from False to True
        if not null :
                compare course structure for set of  (content_type , content_id) of course_id in url and id of course which is mentioned in original_course.
                if match :
                        can't activate the course
                if not match:
                        activate the course by changing active from False to True
        
"validation if the course is allowed to be checked for being original course or not will be done only when course structure have instance of course ,
else activation is not allowed, as how the course will be viewed will be defined by that course structure only."

    """
    def post(self, request, course_id, *args, **kwargs):
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ActivateCourseSerializer(data={'course_id': course.id})
        # data is coming from serializer when course have at least one quiz mapped in course structure table.
        if serializer.is_valid():
            course = serializer.validated_data['course_id']

            if course.original_course is None:
                # If original_course is null, simply activate the course
                course.active = True
                course.save()
                return Response({"message": "Course activated successfully."}, status=status.HTTP_200_OK)
            else:
                # If original_course is not null, compare course structures
                original_course_structure = CourseStructure.objects.filter(course=course.original_course)\
                    .values_list('content_type', 'content_id')

                current_course_structure = CourseStructure.objects.filter(course=course)\
                    .values_list('content_type', 'content_id')

                original_course_structure_df = pd.DataFrame(original_course_structure, columns=['content_type', 'content_id'])
                current_course_structure_df = pd.DataFrame(current_course_structure, columns=['content_type', 'content_id'])

                if original_course_structure_df.equals(current_course_structure_df):
                    # Course structures match, can't activate the course
                    return Response({"error": "Cannot activate the course. Course structure matches original course."},
                                    status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Course structures don't match, activate the course
                    course.active = True
                    course.save()
                    return Response({"message": "Course activated successfully."}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InActivateCourseView(APIView):
    """
        view to inactivate the course.
        trigger with POST request.
        in URL : course_id of selected instance.
        table : Course
        
        do it by giving warning by counting the number of instances in course enrollment table where course_id is same as that in url and active is True. [to tell how many people are studying the course now]
        
        doing this : inactivating a course , it should be appearing for employees to study it or even register it any furthur customer,
        but the history of users regarding this course should not be erased.
        
        updating instance field:
                    change active from True to False        
    """
    def post(self, request, course_id,*args, **kwargs):
        serializer = InActivateCourseSerializer(data={'course_id': course_id})
        if serializer.is_valid():
            course = serializer.validated_data['course_id']
            # Count the number of active enrollments for the course
            active_enrollments_count = CourseEnrollment.objects.filter(course=course, active=True).count()
            
            # Inactivate the course
            course.active = False
            course.save()

            return Response({
                "message": "Course inactivated successfully.",
                "active_enrollments before inactivation": active_enrollments_count
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =================================================================
            # Version Part
# =================================================================
class CreateNewVersionCourseView(APIView):
    """
    view to create new version of already existing active course
    
    in url : course_id of selected instance , whoes versioning we are going to do , and feed it as orginial course in newly created instance.
    
    table : Course, Course Structure , [UploadReadingMaterial , UploadVideo , Quiz] their tables where they are in many to many relation with courses
    
    on saving , new instance of course will be created :
                slug = auto generated
                title = same as course in url for now
                summary = same as course in url for now
                created_at = updated_at = now()
                active = False
                original_course = course id in url
                version_number = count the instances for which course_id in url is originalcourse, and add 2 to that count, and pass it as version_number
    in course_structure table , taking the course_id from url, and id of newly created instance:
            copy what is related to id in url to new instance.
    similarly for all readingmaterial, video , quiz which are in relation with course_id in url , will be mapped with new instance too
    """
    def post(self, request, course_id, *args, **kwargs):
        try:
            original_course = Course.objects.get(pk=course_id)
            if not original_course.active:
                return Response({"error": "The original course is not active"}, status=status.HTTP_400_BAD_REQUEST)
            # Check if there are already two or more inactive versions
            inactive_versions_count = Course.objects.filter(Q(original_course=original_course) & Q(active=False)).count()
            if inactive_versions_count >= 2:
                return Response(
                    {"error": "Two or more inactive versions of this course already exist. Delete or activate them first."},
                    status=status.HTTP_400_BAD_REQUEST)
        except Course.DoesNotExist:
            return Response({"error": "Original course not found."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            with transaction.atomic():
                # Create new course instance based on original course
                new_course_data = {
                    'title': original_course.title,
                    'summary': original_course.summary,
                    'active': False,
                    'original_course': original_course.id,
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                    'version_number': Course.objects.filter(original_course=original_course).count() + 2
                }
                new_course_serializer = CourseSerializer(data=new_course_data)
                if new_course_serializer.is_valid():
                    new_course = new_course_serializer.save()
                else:
                    return Response({"error": new_course_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
                # Copy course structure from original course
                original_course_structure = CourseStructure.objects.filter(course=original_course)
                for structure in original_course_structure:
                    structure_data = CourseStructureSerializer(structure).data
                    structure_data['course'] = new_course.pk
                    structure_serializer = CourseStructureSerializer(data=structure_data)
                    if structure_serializer.is_valid():
                        structure_serializer.save()
                    else:
                        return Response({"error": structure_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
                related_reading_materials = UploadReadingMaterial.objects.filter(courses=original_course)
                new_course.reading_materials.set(related_reading_materials)
                    
                # Map existing UploadVideo
                related_videos = UploadVideo.objects.filter(courses=original_course)
                new_course.video_materials.set(related_videos)
                    
                # Map existing Quiz
                related_quizzes = Quiz.objects.filter(courses=original_course)
                new_course.quizzes.set(related_quizzes)
            
            return Response({"message": "New version of course created successfully."}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)