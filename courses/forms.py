from django import forms
from django.forms import inlineformset_factory
from .models import Course, Module, Lesson, ContentBlock

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'price', 'is_published']

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title']

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'order']

class ContentBlockForm(forms.ModelForm):
    class Meta:
        model = ContentBlock
        fields = ['content_type', 'content', 'order']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }

ModuleFormSet = inlineformset_factory(Course, Module, form=ModuleForm, extra=1, can_delete=True)
LessonFormSet = inlineformset_factory(Module, Lesson, form=LessonForm, extra=1, can_delete=True)
ContentBlockFormSet = inlineformset_factory(Lesson, ContentBlock, form=ContentBlockForm,extra=1, can_delete=True)
