from django import forms
from django.contrib.auth.models import User
from .models import Account, Task, Participation, MappingInfo, SchemaAttribute, MappingPair, ParsedFile


class LoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'password']


class GradeForm(forms.ModelForm):
    pass_state = forms.BooleanField(required=False)

    class Meta:
        model = ParsedFile
        fields = ['grading_score', 'pass_state']


class SchemaChoiceForm(forms.ModelForm):
    """
    docstring
    """
    task = Task
    mappingInfo = MappingInfo


# class UploadForm(forms.ModelForm):
#     """
#     docstring
#     """
#     class Meta:
#         model = ParsedFile
#         # fields = {'name', 'data'}
#         fields = ['derived_schema', 'file_original', 'start_date', 'end_date']

#     def save(self, commit=True):
#         self.instance = ParsedFile(**self.cleaned_data)

#         # if commit:
#         #     self.instance.save()
#             # self.instance.name = self.instance.file_original.name
#             # self.instance.save()
#         return self.instance


class CreateTask(forms.ModelForm):
    """
    docstring
    """
    class Meta:
        model = Task
        # fields = {'name', 'data'}
        fields = [
            'name',
            'minimal_upload_frequency',
            'description',
            'original_data_description',
        ]

    def save(self, commit=True):
        self.instance = Task(**self.cleaned_data)

        if commit:
            self.instance.save()
            # self.instance.name = self.instance.file_original.name
            # self.instance.save()
        return self.instance


# class CreateSchemaAttribute(forms.ModelForm):
#     """
#     docstring
#     """
#     class Meta:
#         model = SchemaAttribute
#         fields = [
#             'attr',
#         ]

#     def save(self, task, commit=True):
#         self.instance = SchemaAttribute(**self.cleaned_data)
#         self.instance.task = task

#         if commit:
#             self.instance.save()
#             # self.instance.name = self.instance.file_original.name
#             # self.instance.save()
#         return self.instance


# class CreateMappingInfo(forms.ModelForm):
#     """
#     docstring
#     """
#     class Meta:
#         model = MappingInfo
#         # fields = {'name', 'data'}
#         fields = [
#             'derived_schema_name',
#         ]

#     def save(self, task, commit=True):
#         self.instance = MappingInfo(**self.cleaned_data)
#         self.instance.task = task

#         if commit:
#             self.instance.save()
#             # self.instance.name = self.instance.file_original.name
#             # self.instance.save()
#         return self.instance


class CreateMappingPair(forms.ModelForm):
    """
    docstring
    """
    class Meta:
        model = MappingPair
        fields = [
            # 'mapping_info',
            'schema_attribute',
            'parsing_column_name',
        ]

    def save(self, mapping_info, commit=True):
        self.instance = MappingPair(**self.cleaned_data)
        # self.instance.task = task
        self.instance.mapping_info = mapping_info

        if commit:
            self.instance.save()
            # self.instance.name = self.instance.file_original.name
            # self.instance.save()
        return self.instance
