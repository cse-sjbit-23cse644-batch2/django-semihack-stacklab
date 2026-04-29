from django import forms


def get_category_choices():
    """Load actual categories from DB dynamically."""
    try:
        from .models import Result
        cats = Result.objects.values_list('category', flat=True).distinct().order_by('category')
        choices = [('', 'All Categories')]
        for c in cats:
            if c:
                choices.append((c, c))
        return choices
    except Exception:
        return [('', 'All Categories')]


def get_quota_choices():
    """Load actual quotas from DB dynamically."""
    try:
        from .models import Result
        quotas = Result.objects.values_list('admission_quota', flat=True).distinct().order_by('admission_quota')
        choices = [('', 'All Quotas')]
        for q in quotas:
            if q:
                choices.append((q, q))
        return choices
    except Exception:
        return [('', 'All Quotas')]


class CSVUploadForm(forms.Form):
    file = forms.FileField(
        label='Upload Results File',
        help_text='Accepted: CSV or Excel (.xlsx). Required columns: USN, SubjectCode, Marks, SGPA, Category, AdmissionQuota',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls',
        })
    )
    academic_year = forms.CharField(
        max_length=20, required=False, initial='2024-25',
        label='Academic Year',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 2024-25',
        })
    )
    semester = forms.IntegerField(
        required=False, initial=1, min_value=1, max_value=8,
        label='Semester Override',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 5',
        })
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            name = file.name.lower()
            if not (name.endswith('.csv') or name.endswith('.xlsx') or name.endswith('.xls')):
                raise forms.ValidationError("Only CSV or Excel files are accepted.")
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10 MB.")
        return file


class CourseFilterForm(forms.Form):
    subject_code = forms.CharField(
        required=False, label='Subject Code',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 23CST501',
        })
    )
    semester = forms.IntegerField(
        required=False, min_value=1, max_value=8, label='Semester',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 5',
        })
    )
    academic_year = forms.CharField(
        required=False, label='Academic Year',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 2024-25',
        })
    )


class CategoryFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load choices dynamically from DB
        self.fields['category'].choices = get_category_choices()
        self.fields['admission_quota'].choices = get_quota_choices()

    category = forms.ChoiceField(
        choices=[('', 'All Categories')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    admission_quota = forms.ChoiceField(
        choices=[('', 'All Quotas')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    semester = forms.IntegerField(
        required=False, min_value=1, max_value=8,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Semester',
        })
    )


class BacklogFilterForm(forms.Form):
    usn = forms.CharField(
        required=False, label='Student USN',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 1JB03CS001',
        })
    )
    subject_code = forms.CharField(
        required=False, label='Subject Code',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    semester = forms.IntegerField(
        required=False, min_value=1, max_value=8,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    cleared = forms.ChoiceField(
        choices=[('', 'All'), ('False', 'Pending'), ('True', 'Cleared')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class NBAFilterForm(forms.Form):
    semester = forms.IntegerField(
        required=False, min_value=1, max_value=8,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    academic_year = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 2024-25',
        })
    )
    subject_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )