from django.db import models

CATEGORY_CHOICES = [
    ('GM', 'General Merit'),
    ('2A', '2A - OBC'),
    ('2B', '2B - OBC'),
    ('3A', '3A - OBC'),
    ('3B', '3B - OBC'),
    ('SC', 'Scheduled Caste'),
    ('SCG', 'SC - General'),
    ('SCH', 'SC - Horanadu'),
    ('SCK', 'SC - Kaadugolla'),
    ('SCR', 'SC - Rural'),
    ('ST', 'Scheduled Tribe'),
    ('STG', 'ST - General'),
    ('STH', 'ST - Horanadu'),
    ('1G', '1G Category'),
    ('HK', 'Hyderabad Karnataka'),
    ('2AG', '2A - General'),
    ('2AR', '2A - Rural'),
    ('3AG', '3A - General'),
    ('3BG', '3B - General'),
    ('3BR', '3B - Rural'),
    ('2AGR', '2A General Rural'),
    ('3AGR', '3A General Rural'),
    ('1GH', '1G Horanadu'),
    ('2B', '2B Category'),
    ('OTHER', 'Other'),
]

ADMISSION_QUOTA_CHOICES = [
    ('CET', 'CET'),
    ('CET-SNQ', 'CET - SNQ'),
    ('COMED-K', 'COMED-K'),
    ('DIPLOMA CET', 'Diploma CET'),
    ('MANAGEMENT', 'Management'),
    ('NRI', 'NRI'),
    ('HOD', 'HOD'),
    ('OTHER', 'Other'),
]

GRADE_CHOICES = [
    ('O', 'Outstanding (>=90)'),
    ('A+', 'Excellent (80-89)'),
    ('A', 'Very Good (70-79)'),
    ('B+', 'Good (60-69)'),
    ('B', 'Average (55-59)'),
    ('C', 'Satisfactory (50-54)'),
    ('P', 'Pass (40-49)'),
    ('F', 'Fail (<40)'),
    ('AB', 'Absent'),
]


class Subject(models.Model):
    subject_code = models.CharField(max_length=20, unique=True)
    subject_name = models.CharField(max_length=200)
    semester = models.IntegerField(default=1)
    max_marks = models.IntegerField(default=100)
    credits = models.IntegerField(default=4)

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"

    class Meta:
        ordering = ['subject_code']


class Result(models.Model):
    usn = models.CharField(max_length=20, db_index=True)
    student_name = models.CharField(max_length=200, blank=True, null=True)
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE,
        related_name='results', null=True, blank=True
    )
    subject_code = models.CharField(max_length=20, db_index=True)
    subject_name = models.CharField(max_length=200, blank=True, null=True)
    marks = models.FloatField(null=True, blank=True)
    max_marks = models.FloatField(default=100)
    grade = models.CharField(max_length=5, blank=True, null=True)
    sgpa = models.FloatField(null=True, blank=True)
    semester = models.IntegerField(default=1)
    category = models.CharField(max_length=10, default='GM')
    admission_quota = models.CharField(max_length=20, default='CET')
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    is_pass = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.marks is not None:
            self.is_pass = self.marks >= 40
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usn} - {self.subject_code} - {self.marks}"

    class Meta:
        ordering = ['usn', 'semester', 'subject_code']
        indexes = [
            models.Index(fields=['subject_code', 'semester']),
            models.Index(fields=['category']),
            models.Index(fields=['usn']),
        ]


class Backlog(models.Model):
    usn = models.CharField(max_length=20, db_index=True)
    student_name = models.CharField(max_length=200, blank=True, null=True)
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=200, blank=True, null=True)
    semester = models.IntegerField(default=1)
    marks = models.FloatField(null=True, blank=True)
    attempts = models.IntegerField(default=1)
    cleared = models.BooleanField(default=False)
    academic_year = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.usn} - {self.subject_code} (Sem {self.semester})"

    class Meta:
        ordering = ['usn', 'semester']
        unique_together = ['usn', 'subject_code', 'semester']


class NBAMetric(models.Model):
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=200, blank=True, null=True)
    semester = models.IntegerField(default=1)
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    appeared = models.IntegerField(default=0)
    passed = models.IntegerField(default=0)
    total_enrolled = models.IntegerField(default=0)
    mean_sgpa = models.FloatField(default=0.0)
    si = models.FloatField(default=0.0, verbose_name='Success Index')
    api = models.FloatField(default=0.0, verbose_name='Academic Performance Index')
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject_code} - SI:{self.si:.2f} API:{self.api:.2f}"

    class Meta:
        ordering = ['-calculated_at']
        unique_together = ['subject_code', 'semester', 'academic_year']


class Backlog(models.Model):
    usn = models.CharField(max_length=20, db_index=True)
    student_name = models.CharField(max_length=200, blank=True, null=True)
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=200, blank=True, null=True)
    semester = models.IntegerField(default=1)
    marks = models.FloatField(null=True, blank=True)
    attempts = models.IntegerField(default=1)
    cleared = models.BooleanField(default=False)
    academic_year = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.usn} - {self.subject_code} (Sem {self.semester})"

    class Meta:
        ordering = ['usn', 'semester']
        unique_together = ['usn', 'subject_code', 'semester']


class NBAMetric(models.Model):
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=200, blank=True, null=True)
    semester = models.IntegerField(default=1)
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    appeared = models.IntegerField(default=0)
    passed = models.IntegerField(default=0)
    total_enrolled = models.IntegerField(default=0)
    mean_sgpa = models.FloatField(default=0.0)
    si = models.FloatField(default=0.0, verbose_name='Success Index')
    api = models.FloatField(default=0.0, verbose_name='Academic Performance Index')
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject_code} - SI:{self.si:.2f} API:{self.api:.2f}"

    class Meta:
        ordering = ['-calculated_at']
        unique_together = ['subject_code', 'semester', 'academic_year']