import io
import json
import xlsxwriter
import csv

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Avg, Count, Q, Max, Min
from django.http import HttpResponse

from .models import Result, Subject, Backlog, NBAMetric
from .forms import (
    CSVUploadForm, CourseFilterForm, CategoryFilterForm,
    BacklogFilterForm, NBAFilterForm
)
from .utils import (
    validate_csv, parse_and_save, calculate_si, calculate_api,
    get_score_distribution, get_pass_fail_stats
)


# ─── Home Dashboard ────────────────────────────────────────────────
def home(request):
    total_results = Result.objects.count()
    total_students = Result.objects.values('usn').distinct().count()
    total_subjects = Subject.objects.count()
    total_backlogs = Backlog.objects.filter(cleared=False).count()

    # Recent uploads — show last 10
    recent_results = Result.objects.order_by('-uploaded_at')[:10]

    # Overall pass rate
    stats = get_pass_fail_stats(Result.objects.all())

    # Semester-wise pass rate for chart
    semester_data = []
    for sem in range(1, 9):
        sem_qs = Result.objects.filter(semester=sem, marks__isnull=False)
        if sem_qs.exists():
            s = get_pass_fail_stats(sem_qs)
            semester_data.append({
                'semester': sem,
                'pass_percent': s['pass_percent'],
                'total': s['total'],
            })

    context = {
        'total_results': total_results,
        'total_students': total_students,
        'total_subjects': total_subjects,
        'total_backlogs': total_backlogs,
        'stats': stats,
        'recent_results': recent_results,
        'semester_data_json': json.dumps(semester_data),
    }
    return render(request, 'analytics/home.html', context)


# ─── Upload ────────────────────────────────────────────────────────
def upload_results(request):
    form = CSVUploadForm()

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            academic_year = form.cleaned_data.get('academic_year') or '2024-25'

            df, errors = validate_csv(uploaded_file)

            if errors:
                for err in errors:
                    messages.error(request, err)
                return render(request, 'analytics/upload.html', {'form': form})

            semester_override = form.cleaned_data.get('semester')
            if semester_override and df is not None:
                df['Semester'] = semester_override

            saved, skipped, backlogs = parse_and_save(df, academic_year)

            messages.success(
                request,
                f"Upload successful! {saved} results saved, "
                f"{skipped} rows skipped, {backlogs} backlogs detected."
            )
            return redirect('home')

    return render(request, 'analytics/upload.html', {'form': form})


# ─── Course-Wise Analysis ──────────────────────────────────────────
def course_analysis(request):
    form = CourseFilterForm(request.GET or None)
    results_qs = Result.objects.all()
    stats = None
    dist = None

    if form.is_valid():
        subject_code = form.cleaned_data.get('subject_code')
        semester = form.cleaned_data.get('semester')
        academic_year = form.cleaned_data.get('academic_year')

        if subject_code:
            results_qs = results_qs.filter(subject_code__icontains=subject_code)
        if semester:
            results_qs = results_qs.filter(semester=semester)
        if academic_year:
            results_qs = results_qs.filter(academic_year=academic_year)

    if results_qs.exists():
        stats = get_pass_fail_stats(results_qs)
        dist = get_score_distribution(results_qs)

    # Per-subject aggregated stats
    subject_stats = (
        Result.objects
        .values('subject_code', 'subject_name', 'semester')
        .annotate(
            total=Count('id', filter=Q(marks__isnull=False)),
            passed=Count('id', filter=Q(is_pass=True)),
            avg_marks=Avg('marks'),
            avg_sgpa=Avg('sgpa'),
        )
        .order_by('subject_code')
    )

    if form.is_valid():
        if form.cleaned_data.get('subject_code'):
            subject_stats = subject_stats.filter(
                subject_code__icontains=form.cleaned_data['subject_code']
            )
        if form.cleaned_data.get('semester'):
            subject_stats = subject_stats.filter(semester=form.cleaned_data['semester'])

    subject_stats_list = []
    for s in subject_stats:
        total = s['total']
        passed = s['passed']
        s['pass_percent'] = round((passed / total * 100), 1) if total > 0 else 0
        s['fail_percent'] = round(100 - s['pass_percent'], 1)
        s['avg_marks'] = round(s['avg_marks'] or 0, 1)
        s['avg_sgpa'] = round(s['avg_sgpa'] or 0, 2)
        subject_stats_list.append(s)

    chart_labels = [s['subject_code'] for s in subject_stats_list]
    chart_pass = [s['pass_percent'] for s in subject_stats_list]
    chart_fail = [s['fail_percent'] for s in subject_stats_list]

    dist_labels = ['<40', '40-49', '50-59', '60-69', '70-79', '80-89', '90-100', 'Absent']
    dist_values = []
    if dist:
        dist_values = [
            dist['below_40'], dist['range_40_49'], dist['range_50_59'],
            dist['range_60_69'], dist['range_70_79'], dist['range_80_89'],
            dist['range_90_100'], dist['absent']
        ]

    context = {
        'form': form,
        'subject_stats': subject_stats_list,
        'stats': stats,
        'dist': dist,
        'subjects_list': Subject.objects.all().order_by('subject_code'),
        'chart_labels_json': json.dumps(chart_labels),
        'chart_pass_json': json.dumps(chart_pass),
        'chart_fail_json': json.dumps(chart_fail),
        'dist_labels_json': json.dumps(dist_labels),
        'dist_values_json': json.dumps(dist_values),
    }
    return render(request, 'analytics/course_dashboard.html', context)


# ─── Category-Wise Analysis ─────────────────────────────────────────
def category_analysis(request):
    form = CategoryFilterForm(request.GET or None)
    results_qs = Result.objects.all()

    if form.is_valid():
        cat = form.cleaned_data.get('category')
        quota = form.cleaned_data.get('admission_quota')
        semester = form.cleaned_data.get('semester')
        if cat:
            results_qs = results_qs.filter(category=cat)
        if quota:
            results_qs = results_qs.filter(admission_quota=quota)
        if semester:
            results_qs = results_qs.filter(semester=semester)

    cat_stats = (
        results_qs
        .values('category')
        .annotate(
            total=Count('id', filter=Q(marks__isnull=False)),
            passed=Count('id', filter=Q(is_pass=True)),
            avg_sgpa=Avg('sgpa'),
            avg_marks=Avg('marks'),
        )
        .order_by('category')
    )

    cat_data = []
    for c in cat_stats:
        total = c['total']
        passed = c['passed']
        c['pass_percent'] = round((passed / total * 100), 1) if total > 0 else 0
        c['avg_sgpa'] = round(c['avg_sgpa'] or 0, 2)
        c['avg_marks'] = round(c['avg_marks'] or 0, 1)
        cat_data.append(c)

    quota_stats = (
        results_qs
        .values('admission_quota')
        .annotate(
            total=Count('id', filter=Q(marks__isnull=False)),
            passed=Count('id', filter=Q(is_pass=True)),
            avg_sgpa=Avg('sgpa'),
        )
        .order_by('admission_quota')
    )

    quota_data = []
    for q in quota_stats:
        total = q['total']
        passed = q['passed']
        q['pass_percent'] = round((passed / total * 100), 1) if total > 0 else 0
        q['avg_sgpa'] = round(q['avg_sgpa'] or 0, 2)
        quota_data.append(q)

    toppers = (
        Result.objects.filter(sgpa__gte=9.5)
        .order_by('-sgpa')
        .values('usn', 'student_name', 'sgpa', 'category')
        .distinct()[:20]
    )

    context = {
        'form': form,
        'cat_data': cat_data,
        'quota_data': quota_data,
        'toppers': toppers,
        'chart_categories_json': json.dumps([c['category'] for c in cat_data]),
        'chart_pass_rates_json': json.dumps([c['pass_percent'] for c in cat_data]),
        'chart_avg_sgpa_json': json.dumps([c['avg_sgpa'] for c in cat_data]),
    }
    return render(request, 'analytics/category_comparison.html', context)


# ─── Backlog Tracking ───────────────────────────────────────────────
def backlog_tracking(request):
    form = BacklogFilterForm(request.GET or None)
    backlogs_qs = Backlog.objects.all()

    if form.is_valid():
        usn = form.cleaned_data.get('usn')
        subject_code = form.cleaned_data.get('subject_code')
        semester = form.cleaned_data.get('semester')
        cleared = form.cleaned_data.get('cleared')

        if usn:
            backlogs_qs = backlogs_qs.filter(usn__icontains=usn)
        if subject_code:
            backlogs_qs = backlogs_qs.filter(subject_code__icontains=subject_code)
        if semester:
            backlogs_qs = backlogs_qs.filter(semester=semester)
        if cleared == 'True':
            backlogs_qs = backlogs_qs.filter(cleared=True)
        elif cleared == 'False':
            backlogs_qs = backlogs_qs.filter(cleared=False)

    total_backlogs = Backlog.objects.filter(cleared=False).count()
    cleared_backlogs = Backlog.objects.filter(cleared=True).count()

    # Students with most backlogs
    most_backlogs = (
        Backlog.objects.filter(cleared=False)
        .values('usn', 'student_name')
        .annotate(backlog_count=Count('id'))
        .order_by('-backlog_count')[:10]
    )

    # Semester-wise backlog trend
    semester_trend = (
        Backlog.objects
        .values('semester')
        .annotate(count=Count('id'))
        .order_by('semester')
    )
    trend_labels = [f"Sem {t['semester']}" for t in semester_trend]
    trend_values = [t['count'] for t in semester_trend]

    # Subject-wise backlog count
    subject_backlogs = (
        Backlog.objects.filter(cleared=False)
        .values('subject_code', 'subject_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    context = {
        'form': form,
        'backlogs': backlogs_qs.order_by('-semester', 'usn')[:200],
        'total_backlogs': total_backlogs,
        'cleared_backlogs': cleared_backlogs,
        'most_backlogs': most_backlogs,
        'subject_backlogs': subject_backlogs,
        'trend_labels_json': json.dumps(trend_labels),
        'trend_values_json': json.dumps(trend_values),
    }
    return render(request, 'analytics/backlog_tracking.html', context)


# ─── NBA Metrics ────────────────────────────────────────────────────
def nba_report(request):
    form = NBAFilterForm(request.GET or None)
    results_qs = Result.objects.all()

    if form.is_valid():
        semester = form.cleaned_data.get('semester')
        academic_year = form.cleaned_data.get('academic_year')
        subject_code = form.cleaned_data.get('subject_code')

        if semester:
            results_qs = results_qs.filter(semester=semester)
        if academic_year:
            results_qs = results_qs.filter(academic_year=academic_year)
        if subject_code:
            results_qs = results_qs.filter(subject_code__icontains=subject_code)

    # Use is_pass (correct field name)
    subject_metrics = (
        results_qs
        .values('subject_code', 'subject_name', 'semester', 'academic_year')
        .annotate(
            appeared=Count('id', filter=Q(marks__isnull=False)),
            passed=Count('id', filter=Q(is_pass=True)),
            mean_sgpa=Avg('sgpa'),
            total_enrolled=Count('id'),
        )
        .order_by('semester', 'subject_code')
    )

    metrics_list = []
    for m in subject_metrics:
        appeared = m['appeared']
        passed = m['passed']
        mean_sgpa = m['mean_sgpa'] or 0
        si = calculate_si(passed, appeared)
        api = calculate_api(mean_sgpa, passed, appeared)

        metrics_list.append({
            **m,
            'si': si,
            'api': api,
            'mean_sgpa': round(mean_sgpa, 2),
            'pass_percent': round((passed / appeared * 100), 1) if appeared > 0 else 0,
        })

        # Save to NBAMetric model
        try:
            NBAMetric.objects.update_or_create(
                subject_code=m['subject_code'],
                semester=m['semester'],
                academic_year=m['academic_year'] or 'N/A',
                defaults={
                    'subject_name': m['subject_name'],
                    'appeared': appeared,
                    'passed': passed,
                    'total_enrolled': m['total_enrolled'],
                    'mean_sgpa': round(mean_sgpa, 2),
                    'si': si,
                    'api': api,
                }
            )
        except Exception:
            pass

    context = {
        'form': form,
        'metrics_list': metrics_list,
    }
    return render(request, 'analytics/nba_report.html', context)


# ─── Export NBA to Excel ─────────────────────────────────────────────
def export_nba_excel(request):
    form = NBAFilterForm(request.GET or None)
    results_qs = Result.objects.all()

    if form.is_valid():
        if form.cleaned_data.get('semester'):
            results_qs = results_qs.filter(semester=form.cleaned_data['semester'])
        if form.cleaned_data.get('academic_year'):
            results_qs = results_qs.filter(academic_year=form.cleaned_data['academic_year'])
        if form.cleaned_data.get('subject_code'):
            results_qs = results_qs.filter(
                subject_code__icontains=form.cleaned_data['subject_code']
            )

    subject_metrics = (
        results_qs
        .values('subject_code', 'subject_name', 'semester', 'academic_year')
        .annotate(
            appeared=Count('id', filter=Q(marks__isnull=False)),
            passed=Count('id', filter=Q(is_pass=True)),
            mean_sgpa=Avg('sgpa'),
            total_enrolled=Count('id'),
        )
        .order_by('semester', 'subject_code')
    )

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('NBA-SAR Metrics')

    header_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#1a56db', 'font_color': 'white',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11
    })
    cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'font_size': 10})
    title_fmt = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'
    })
    warn_fmt = workbook.add_format({
        'border': 1, 'align': 'center', 'font_size': 10,
        'bg_color': '#fef3c7', 'font_color': '#92400e'
    })

    worksheet.merge_range('A1:L1', 'NBA-SAR Academic Performance Metrics', title_fmt)
    worksheet.set_row(0, 30)

    headers = [
        'Subject Code', 'Subject Name', 'Semester', 'Academic Year',
        'Total Enrolled', 'Appeared', 'Passed', 'Failed',
        'Pass %', 'Success Index (SI)', 'API', 'Avg SGPA'
    ]
    for col, h in enumerate(headers):
        worksheet.write(1, col, h, header_fmt)
    worksheet.set_row(1, 22)

    col_widths = [15, 30, 10, 14, 14, 10, 10, 10, 10, 18, 10, 12]
    for i, w in enumerate(col_widths):
        worksheet.set_column(i, i, w)

    metrics_list = list(subject_metrics)
    for row_idx, m in enumerate(metrics_list):
        appeared = m['appeared']
        passed = m['passed']
        mean_sgpa = m['mean_sgpa'] or 0
        si = calculate_si(passed, appeared)
        api = calculate_api(mean_sgpa, passed, appeared)
        pass_pct = round((passed / appeared * 100), 1) if appeared > 0 else 0
        fmt = warn_fmt if pass_pct < 70 else cell_fmt

        row = row_idx + 2
        worksheet.write(row, 0, m['subject_code'], cell_fmt)
        worksheet.write(row, 1, m['subject_name'] or '', cell_fmt)
        worksheet.write(row, 2, m['semester'], cell_fmt)
        worksheet.write(row, 3, m['academic_year'] or '', cell_fmt)
        worksheet.write(row, 4, m['total_enrolled'], cell_fmt)
        worksheet.write(row, 5, appeared, cell_fmt)
        worksheet.write(row, 6, passed, cell_fmt)
        worksheet.write(row, 7, appeared - passed, cell_fmt)
        worksheet.write(row, 8, pass_pct, fmt)
        worksheet.write(row, 9, si, fmt)
        worksheet.write(row, 10, api, cell_fmt)
        worksheet.write(row, 11, round(mean_sgpa, 2), cell_fmt)

    note_row = len(metrics_list) + 3
    worksheet.merge_range(
        note_row, 0, note_row, 11,
        'Note: Yellow rows indicate pass% < 70 (needs attention)',
        cell_fmt
    )

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="NBA_SAR_Metrics.xlsx"'
    return response


# ─── Export Results CSV ──────────────────────────────────────────────
def export_results_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="results_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'USN', 'Student Name', 'Subject Code', 'Subject Name',
        'Marks', 'SGPA', 'Grade', 'Semester',
        'Category', 'Admission Quota', 'Pass/Fail', 'Academic Year'
    ])

    results = Result.objects.all().order_by('semester', 'subject_code', 'usn')
    for r in results:
        writer.writerow([
            r.usn, r.student_name, r.subject_code, r.subject_name,
            r.marks, r.sgpa, r.grade, r.semester,
            r.category, r.admission_quota,
            'Pass' if r.is_pass else 'Fail',
            r.academic_year,
        ])

    return response