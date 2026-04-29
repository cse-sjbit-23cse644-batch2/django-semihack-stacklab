import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

# Only USN is truly required — rest get defaults if missing
REQUIRED_COLUMNS = ['USN']

# These will be defaulted if not found
OPTIONAL_WITH_DEFAULTS = {
    'SubjectCode': 'GENERAL',
    'Marks': None,
    'SGPA': None,
    'Category': 'GM',
    'AdmissionQuota': 'CET',
}

COLUMN_ALIASES = {
    'usn': 'USN',
    'usn ': 'USN',
    'student_usn': 'USN',
    'roll_no': 'USN',
    'subjectcode': 'SubjectCode',
    'subject_code': 'SubjectCode',
    'subject code': 'SubjectCode',
    'subject': 'SubjectCode',
    'code': 'SubjectCode',
    'marks': 'Marks',
    'total_marks': 'Marks',
    'score': 'Marks',
    'sgpa': 'SGPA',
    'gpa': 'SGPA',
    'category': 'Category',
    'actual_category': 'Category',
    'actualcategory': 'Category',
    'actual category': 'Category',
    'caste': 'Category',
    'admissionquota': 'AdmissionQuota',
    'admission_quota': 'AdmissionQuota',
    'admission quota': 'AdmissionQuota',
    'quota': 'AdmissionQuota',
    'student_name': 'StudentName',
    'student name': 'StudentName',
    'name': 'StudentName',
    'names ': 'StudentName',
    'names': 'StudentName',
    'subjectname': 'SubjectName',
    'subject_name': 'SubjectName',
    'subject name': 'SubjectName',
    'semester': 'Semester',
    'sem': 'Semester',
    'grade': 'Grade',
    'academic_year': 'AcademicYear',
    'year': 'AcademicYear',
    'batch': 'Batch',
}

QUOTA_NORMALIZE = {
    'cet': 'CET',
    'cet-snq': 'CET-SNQ',
    'cet snq': 'CET-SNQ',
    'cetsnq': 'CET-SNQ',
    'comed-k': 'COMED-K',
    'comedk': 'COMED-K',
    'comed_k': 'COMED-K',
    'diploma cet': 'DIPLOMA CET',
    'diplomacet': 'DIPLOMA CET',
    'diploma  cet': 'DIPLOMA CET',
    'management': 'MANAGEMENT',
    'mgmt': 'MANAGEMENT',
    'nri': 'NRI',
    'hod': 'HOD',
}


def find_header_row(df_raw):
    """Find the row index that best matches expected column names."""
    key_words = ['usn', 'marks', 'sgpa', 'category', 'quota',
                 'subject', 'semester', 'admission', 'name', 'student']
    best_row = 0
    best_score = 0
    for i in range(min(25, len(df_raw))):
        row_vals = [str(v).strip().lower() for v in df_raw.iloc[i].values
                    if str(v) not in ('nan', 'None', '')]
        score = sum(1 for word in key_words
                    if any(word in cell for cell in row_vals))
        if score > best_score:
            best_score = score
            best_row = i
    return best_row if best_score >= 2 else 0


def normalize_columns(df):
    """Normalize column names to expected standard names."""
    df.columns = [str(col).strip() for col in df.columns]
    rename_map = {}
    for col in df.columns:
        normalized = col.lower().strip()
        normalized = normalized.replace('  ', ' ')
        if normalized in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[normalized]
        else:
            normalized2 = normalized.replace(' ', '_').replace('-', '_')
            if normalized2 in COLUMN_ALIASES:
                rename_map[col] = COLUMN_ALIASES[normalized2]
    df = df.rename(columns=rename_map)
    return df


def add_missing_columns(df):
    """Add default values for any missing optional columns."""
    for col, default in OPTIONAL_WITH_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default
            logger.info(f"Column '{col}' not found — using default: {default}")
    return df


def map_category(x):
    val = str(x).strip()
    if val.lower() in ('nan', 'none', ''):
        return 'GM'
    return val.upper()[:10]


def map_quota(x):
    val = str(x).strip()
    if val.lower() in ('nan', 'none', ''):
        return 'OTHER'
    return QUOTA_NORMALIZE.get(val.lower().strip(), val.upper()[:20])


def validate_csv(file_obj):
    """
    Validate uploaded CSV/Excel file.
    Only USN is required — all other columns are optional with defaults.
    Returns (dataframe, errors_list).
    """
    errors = []
    df = None

    try:
        filename = getattr(file_obj, 'name', '').lower()

        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df_raw = pd.read_excel(file_obj, header=None)
            header_row = find_header_row(df_raw)
            logger.info(f"Detected header row at index {header_row}")
            file_obj.seek(0)
            df = pd.read_excel(file_obj, header=header_row)
        else:
            try:
                content = file_obj.read()
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(content), encoding='latin-1')
            except Exception as e:
                errors.append(f"Could not parse file: {str(e)}")
                return df, errors

        # Normalize and add defaults
        df = normalize_columns(df)
        df = df.dropna(how='all')

        if df.empty:
            errors.append("The uploaded file has no data rows.")
            return df, errors

        # Check only USN is required
        if 'USN' not in df.columns:
            errors.append(
                f"USN column not found. Found: {', '.join(df.columns.tolist()[:10])}"
            )
            return df, errors

        # Add default values for missing columns
        df = add_missing_columns(df)

        # Drop rows with missing USN
        df = df[df['USN'].notna() & (df['USN'].astype(str).str.strip() != '')]
        df = df[~df['USN'].astype(str).str.lower().isin(['nan', 'none', 'usn'])]

        if df.empty:
            errors.append("No valid rows with USN found.")
            return df, errors

        # Coerce numeric columns
        df['Marks'] = pd.to_numeric(df['Marks'], errors='coerce')
        df['SGPA'] = pd.to_numeric(df['SGPA'], errors='coerce')

        # Standardize Category and Quota
        df['Category'] = df['Category'].apply(map_category)
        df['AdmissionQuota'] = df['AdmissionQuota'].apply(map_quota)

        # Set Semester
        if 'Semester' in df.columns:
            df['Semester'] = pd.to_numeric(
                df['Semester'], errors='coerce'
            ).fillna(1).astype(int)
        else:
            df['Semester'] = 1

        logger.info(f"Validated {len(df)} rows successfully.")

    except Exception as e:
        errors.append(f"Unexpected error reading file: {str(e)}")
        logger.exception("CSV validation error")

    return df, errors


def parse_and_save(df, academic_year=None):
    from .models import Result, Subject, Backlog

    saved = 0
    skipped = 0
    backlogs_created = 0

    for _, row in df.iterrows():
        try:
            usn = str(row['USN']).strip().upper()
            subject_code = str(row.get('SubjectCode', 'GENERAL')).strip().upper()

            if not usn or usn in ('NAN', 'NONE', ''):
                skipped += 1
                continue

            subject_name = str(row.get('SubjectName', '')).strip()
            if subject_name.lower() in ('nan', 'none'):
                subject_name = ''
            semester = int(row.get('Semester', 1))

            subject, _ = Subject.objects.get_or_create(
                subject_code=subject_code,
                defaults={
                    'subject_name': subject_name or subject_code,
                    'semester': semester,
                }
            )

            marks_val = row.get('Marks')
            marks = float(marks_val) if pd.notna(marks_val) else None

            sgpa_val = row.get('SGPA')
            sgpa = float(sgpa_val) if pd.notna(sgpa_val) else None

            grade_val = row.get('Grade', '')
            grade = str(grade_val).strip() if pd.notna(grade_val) else None
            if grade and grade.lower() in ('nan', 'none'):
                grade = None

            name_val = row.get('StudentName', '')
            student_name = str(name_val).strip() if pd.notna(name_val) else None
            if student_name and student_name.lower() in ('nan', 'none'):
                student_name = None

            result, created = Result.objects.update_or_create(
                usn=usn,
                subject_code=subject_code,
                semester=semester,
                defaults={
                    'student_name': student_name,
                    'subject': subject,
                    'subject_name': subject_name or subject_code,
                    'marks': marks,
                    'sgpa': sgpa,
                    'grade': grade,
                    'category': row.get('Category', 'GM'),
                    'admission_quota': row.get('AdmissionQuota', 'CET'),
                    'academic_year': academic_year,
                    'is_pass': (marks is not None and marks >= 40),
                }
            )
            if created:
                saved += 1

            if marks is not None and marks < 40:
                _, b_created = Backlog.objects.update_or_create(
                    usn=usn,
                    subject_code=subject_code,
                    semester=semester,
                    defaults={
                        'student_name': student_name,
                        'subject_name': subject_name or subject_code,
                        'marks': marks,
                        'academic_year': academic_year,
                        'cleared': False,
                    }
                )
                if b_created:
                    backlogs_created += 1

        except Exception as e:
            logger.warning(f"Skipping row due to error: {e}")
            skipped += 1
            continue

    return saved, skipped, backlogs_created


def calculate_si(passed, appeared):
    if appeared == 0:
        return 0.0
    return round((passed / appeared) * 100, 2)


def calculate_api(mean_sgpa, passed, appeared):
    if appeared == 0:
        return 0.0
    return round((mean_sgpa * passed / appeared) * 10, 2)


def get_score_distribution(queryset):
    from django.db.models import Count, Q
    return queryset.aggregate(
        below_40=Count('id', filter=Q(marks__lt=40)),
        range_40_49=Count('id', filter=Q(marks__gte=40, marks__lt=50)),
        range_50_59=Count('id', filter=Q(marks__gte=50, marks__lt=60)),
        range_60_69=Count('id', filter=Q(marks__gte=60, marks__lt=70)),
        range_70_79=Count('id', filter=Q(marks__gte=70, marks__lt=80)),
        range_80_89=Count('id', filter=Q(marks__gte=80, marks__lt=90)),
        range_90_100=Count('id', filter=Q(marks__gte=90, marks__lte=100)),
        absent=Count('id', filter=Q(marks__isnull=True)),
    )


def get_pass_fail_stats(queryset):
    total = queryset.filter(marks__isnull=False).count()
    passed = queryset.filter(is_pass=True).count()
    failed = queryset.filter(is_pass=False, marks__isnull=False).count()
    pass_percent = round((passed / total * 100), 2) if total > 0 else 0
    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'pass_percent': pass_percent,
        'fail_percent': round(100 - pass_percent, 2),
    }