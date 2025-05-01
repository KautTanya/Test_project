from django.contrib import admin
from .models import Course, Module, Lesson, UserCourse, LessonProgress, Payment, LessonAttachment
from ckeditor.widgets import CKEditorWidget
from django import forms

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title',)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title',)

# @admin.register(Lesson)
# class LessonAdmin(admin.ModelAdmin):
#     list_display = ('title', 'module', 'order')
#     list_filter = ('module',)
#     search_fields = ('title',)

@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'is_paid', 'date_enrolled')
    list_filter = ('is_paid',)

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'is_completed', 'completed_at')
    list_filter = ('is_completed',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ('order_reference','amount','currency','status','created_at')
    list_filter   = ('status','currency')
    search_fields = ('order_reference','status')

class LessonAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Lesson
        fields = '__all__'

class LessonAttachmentInline(admin.TabularInline):
    model = LessonAttachment
    extra = 1

class LessonAdmin(admin.ModelAdmin):
    form = LessonAdminForm
    inlines = [LessonAttachmentInline]
    list_display = ('title', 'module', 'order')
    list_filter = ('module',)
    search_fields = ('title',)
    
admin.site.register(Lesson, LessonAdmin)