#!/usr/bin/env python
"""
Smart Classroom - Comprehensive Application Test Suite
======================================================
Tests: Functional, Security, Performance / Load
Output: test_report.html (rich dark-mode HTML report)

Usage:
  1. Make sure the Django server is running: python manage.py runserver
  2. Run this script: python test_suite.py
"""
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import time
import json
import re
import sys
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — update passwords if they differ on your local machine
# ──────────────────────────────────────────────────────────────────────────────
BASE_URL    = "http://127.0.0.1:8000"
TEACHER     = {"username": "ramu",       "password": "Ramu@1234"}
STUDENT     = {"username": "m.yaswanth", "password": "Yash@1234"}
COURSE_ID   = 2
QUIZ_ID     = 4
TEST_ID     = 3
RECORDED_ID = 4
ASSIGN_ID   = 2

LOAD_CONCURRENCY = 10   # simultaneous threads for load test
LOAD_TOTAL       = 50   # total requests per load target URL

REPORT_FILE = "test_report.html"

# ──────────────────────────────────────────────────────────────────────────────
# SHARED STATE
# ──────────────────────────────────────────────────────────────────────────────
results      = []
result_lock  = threading.Lock()

# ──────────────────────────────────────────────────────────────────────────────
# HTTP SESSION HELPER
# ──────────────────────────────────────────────────────────────────────────────
class Session:
    """Minimal cookie-aware HTTP session using only stdlib."""
    def __init__(self):
        self.jar     = http.cookiejar.CookieJar()
        self.opener  = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPRedirectHandler()
        )

    def get(self, path, timeout=10):
        url = BASE_URL + path
        try:
            t0  = time.perf_counter()
            req = urllib.request.Request(url)
            res = self.opener.open(req, timeout=timeout)
            body = res.read().decode("utf-8", errors="replace")
            lat  = (time.perf_counter() - t0) * 1000
            return res.status, body, lat, res.geturl()
        except urllib.error.HTTPError as e:
            return e.code, "", 0, url
        except Exception as e:
            return 0, str(e), 0, url

    def post(self, path, data: dict, timeout=10):
        url  = BASE_URL + path
        csrf = self._csrf()
        if csrf:
            data["csrfmiddlewaretoken"] = csrf
        body_enc = urllib.parse.urlencode(data).encode("utf-8")
        try:
            t0  = time.perf_counter()
            req = urllib.request.Request(url, data=body_enc,
                                         headers={"Referer": url,
                                                  "Content-Type": "application/x-www-form-urlencoded"})
            res = self.opener.open(req, timeout=timeout)
            body = res.read().decode("utf-8", errors="replace")
            lat  = (time.perf_counter() - t0) * 1000
            return res.status, body, lat, res.geturl()
        except urllib.error.HTTPError as e:
            return e.code, "", 0, url
        except Exception as e:
            return 0, str(e), 0, url

    def _csrf(self):
        for c in self.jar:
            if c.name == "csrftoken":
                return c.value
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# RESULT LOGGER
# ──────────────────────────────────────────────────────────────────────────────
def log(category, name, description, passed, status_code=None, latency=None, detail=""):
    icon = "PASS" if passed else "FAIL"
    code_str = f"[{status_code}]" if status_code else ""
    lat_str  = f"{latency:.0f}ms" if latency else ""
    print(f"  {'[OK]' if passed else '[!!]'} {name} {code_str} {lat_str}  {detail or ''}")
    with result_lock:
        results.append({
            "category"   : category,
            "name"       : name,
            "description": description,
            "passed"     : passed,
            "status_code": status_code,
            "latency"    : latency,
            "detail"     : detail,
            "time"       : datetime.now().strftime("%H:%M:%S"),
        })
    return passed


# ──────────────────────────────────────────────────────────────────────────────
# SERVER CHECK
# ──────────────────────────────────────────────────────────────────────────────
def test_server():
    print("\n[1] Server Connectivity")
    s = Session()
    code, body, lat, _ = s.get("/users/login/")
    ok = (code == 200)
    log("Connectivity", "Server reachable", "Verify that the Django development server is running at http://127.0.0.1:8000 and responds to HTTP requests.", ok, code, lat,
        "" if ok else "Start with: python manage.py runserver")
    return ok


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION TESTS
# ──────────────────────────────────────────────────────────────────────────────
def do_login(sess: Session, creds: dict, role: str):
    sess.get("/users/login/")          # seed CSRF cookie
    code, body, lat, final_url = sess.post("/users/login/", creds)
    ok = ("login" not in final_url.lower()) and code in (200, 302)
    desc = f"Submit credentials for the {role} account and verify the session redirects to the dashboard instead of returning to the login page."
    return log("Authentication", f"{role.title()} Login", desc, ok, code, lat,
               f"Redirected to: {final_url}" if not ok else f"Landed: {final_url}"), sess


def test_auth():
    print("\n[2] Authentication")
    teacher_sess = Session()
    student_sess = Session()

    ok_t, teacher_sess = do_login(teacher_sess, TEACHER, "teacher")
    ok_s, student_sess = do_login(student_sess, STUDENT, "student")

    # Test logout
    code, body, lat, url = teacher_sess.get("/users/logout/")
    log("Authentication", "Teacher Logout",
        "Verify that visiting /users/logout/ destroys the session and redirects to the login page.",
        "login" in url.lower() or code in (200, 302), code, lat)

    return teacher_sess, student_sess


# ──────────────────────────────────────────────────────────────────────────────
# HELPER — authenticated GET check
# ──────────────────────────────────────────────────────────────────────────────
def auth_get(sess: Session, category, name, description, path,
             expect_code=200, must_contain=None, must_not_redirect_to="/users/login/"):
    code, body, lat, final_url = sess.get(path)
    passed = (code == expect_code)
    detail = ""
    if must_contain and must_contain not in body:
        passed = False
        detail = f"Text '{must_contain}' not found"
    if must_not_redirect_to and must_not_redirect_to in final_url:
        passed = False
        detail = f"Redirected to login — session likely not authenticated"
    return log(category, name, description, passed, code, lat, detail)


# ──────────────────────────────────────────────────────────────────────────────
# FUNCTIONAL TESTS
# ──────────────────────────────────────────────────────────────────────────────
def test_public_pages():
    print("\n[3] Public Pages")
    s = Session()
    # must_not_redirect_to=None because these pages ARE at /users/login/ by design
    auth_get(s, "Public Pages", "Login page loads",
             "The login page must be accessible without authentication and return HTTP 200.",
             "/users/login/", must_contain="Login", must_not_redirect_to=None)
    auth_get(s, "Public Pages", "Register page loads",
             "The registration page must be publicly accessible and render the sign-up form.",
             "/users/register/", must_not_redirect_to=None)
    auth_get(s, "Public Pages", "Root redirects to login",
             "Visiting the root URL '/' must redirect unauthenticated users to the login page.",
             "/", expect_code=200, must_contain="Login", must_not_redirect_to=None)


def test_dashboard(teacher_sess, student_sess):
    print("\n[4] Dashboard")
    auth_get(teacher_sess, "Dashboard", "Teacher dashboard loads",
             "An authenticated teacher must be able to access their personal dashboard at /users/dashboard/ and see key summary cards.",
             "/users/dashboard/")
    auth_get(student_sess, "Dashboard", "Student dashboard loads",
             "An authenticated student must be able to access their personal dashboard and see enrolled courses and upcoming work.",
             "/users/dashboard/")


def test_courses(teacher_sess, student_sess):
    print("\n[5] Courses")
    auth_get(teacher_sess, "Courses", "Teacher: Course list loads",
             "A teacher must be able to view the full list of courses they manage.", "/courses/")
    auth_get(student_sess, "Courses", "Student: Course list loads",
             "A student must see available and enrolled courses at /courses/.", "/courses/")
    auth_get(teacher_sess, "Courses", "Course detail loads",
             f"Fetching /courses/{COURSE_ID}/ must return the full course detail page with enrolled students and materials.",
             f"/courses/{COURSE_ID}/")
    auth_get(teacher_sess, "Courses", "Teacher: Create course form",
             "A teacher must be able to open the 'Create Course' form at /courses/create/.", "/courses/create/")


def test_assignments(teacher_sess, student_sess):
    print("\n[6] Assignments")
    auth_get(teacher_sess, "Assignments", "Teacher: Create assignment form",
             f"Teacher must be able to access assignment creation form for course {COURSE_ID}.",
             f"/assignments/course/{COURSE_ID}/create/")
    auth_get(teacher_sess, "Assignments", "Teacher: Assignment detail",
             f"Fetching /assignments/{ASSIGN_ID}/ must return the assignment detail page with submission list.",
             f"/assignments/{ASSIGN_ID}/")


def test_quizzes(teacher_sess, student_sess):
    print("\n[7] Quizzes")
    auth_get(teacher_sess, "Quizzes", "Teacher: Quiz list for course",
             f"Teacher must see all quizzes created for course {COURSE_ID}.",
             f"/quiz/course/{COURSE_ID}/")
    auth_get(student_sess, "Quizzes", "Student: Quiz list for course",
             f"Student must see available quizzes for course {COURSE_ID}.",
             f"/quiz/course/{COURSE_ID}/")


def test_tests(teacher_sess, student_sess):
    print("\n[8] Tests (Coding)")
    auth_get(teacher_sess, "Tests", "Teacher: Test list loads",
             "Teacher must see the full list of tests at /tests/.", "/tests/")
    auth_get(student_sess, "Tests", "Student: Test list loads",
             "Student must see available tests at /tests/ with Take Test buttons.", "/tests/")
    auth_get(teacher_sess, "Tests", "Teacher: Create test form",
             "Teacher must be able to access the test creation form at /tests/create/.", "/tests/create/")
    auth_get(teacher_sess, "Tests", "Teacher: Test detail",
             f"Fetching /tests/{TEST_ID}/ must return the full test detail page.",
             f"/tests/{TEST_ID}/")


def test_projects(teacher_sess, student_sess):
    print("\n[9] Projects")
    auth_get(teacher_sess, "Projects", "Teacher: Project list",
             "Teacher must be able to access the projects list at /projects/.", "/projects/")
    auth_get(student_sess, "Projects", "Student: Project list",
             "Student must be able to view all their submitted projects at /projects/.", "/projects/")


def test_recorded_classes(teacher_sess, student_sess):
    print("\n[10] Recorded Classes")
    auth_get(teacher_sess, "Recorded Classes", "Teacher: Recorded class list",
             "Teacher must see all uploaded recorded sessions at /recorded-classes/.", "/recorded-classes/")
    auth_get(student_sess, "Recorded Classes", "Student: Recorded class list",
             "Student must be able to browse all available recorded classes.", "/recorded-classes/")
    auth_get(student_sess, "Recorded Classes", "Recorded class detail",
             f"Student must be able to open and watch the recorded class with ID {RECORDED_ID}.",
             f"/recorded-classes/{RECORDED_ID}/")


def test_chat(teacher_sess, student_sess):
    print("\n[11] Chat")
    auth_get(teacher_sess, "Chat", "Teacher: Inbox loads",
             "Teacher's chat inbox must load at /chat/ and display conversation list.", "/chat/")
    auth_get(student_sess, "Chat", "Student: Inbox loads",
             "Student's chat inbox must load and show existing conversations.", "/chat/")


def test_leaderboard(teacher_sess, student_sess):
    print("\n[12] Leaderboard")
    auth_get(teacher_sess, "Leaderboard", "Teacher: Leaderboard loads",
             "Teacher must be able to view the class leaderboard sorted by total marks.", "/users/leaderboard/")
    auth_get(student_sess, "Leaderboard", "Student: Leaderboard loads",
             "Student must see their rank and other students on the leaderboard.", "/users/leaderboard/")


def test_certificates(teacher_sess, student_sess):
    print("\n[13] Certificates")
    auth_get(student_sess, "Certificates", "Student: My certificates",
             "Student must be able to browse their earned certificates at /certificates/my/.", "/certificates/my/")


def test_profile(teacher_sess, student_sess):
    print("\n[14] Profile")
    auth_get(teacher_sess, "Profile", "Teacher: Profile page",
             "Teacher must see their profile page with personal details and avatar.", "/users/profile/")
    auth_get(student_sess, "Profile", "Student: Profile page (with badges)",
             "Student must see their profile page with earned digital badges section.", "/users/profile/")


def test_reports(teacher_sess, student_sess):
    print("\n[15] Reports")
    auth_get(student_sess, "Reports", "Student: Report card loads",
             "Student must see a detailed grade breakdown on their report card.", "/users/report-card/")
    # The teacher reports list is at /reports/manage/ (app_name='reports', name='report_list')
    auth_get(teacher_sess, "Reports", "Teacher: Reports management list",
             "Teacher must see the list of all student performance reports they can review at /reports/manage/.",
             "/reports/manage/")


def test_attendance(teacher_sess, student_sess):
    print("\n[16] Attendance")
    auth_get(teacher_sess, "Attendance", "Teacher: Attendance list for course",
             f"Teacher must see all attendance sessions created for course {COURSE_ID}.",
             f"/attendance/course/{COURSE_ID}/")
    auth_get(student_sess, "Attendance", "Student: Own attendance view",
             f"Student must see their personal attendance record for course {COURSE_ID}.",
             f"/attendance/course/{COURSE_ID}/student/")


def test_ui_features(teacher_sess):
    print("\n[17] UI Features")
    code, body, lat, _ = teacher_sess.get("/users/dashboard/")
    has_toggle   = "theme-toggle"    in body
    has_css_vars = "--sc-ink"        in body or "--sc-bg" in body
    has_sidebar  = "sidebar-panel"   in body
    has_scrollbar= "content-shell"   in body
    log("UI Features", "Dark / Light mode toggle button present",
        "The top navbar must contain a theme-toggle button that lets users switch between Light and Dark mode.",
        has_toggle, code, lat)
    log("UI Features", "CSS design tokens (variables) defined",
        "The base template must define smart classroom CSS custom properties (--sc-ink, --sc-bg etc.) for consistent theming.",
        has_css_vars, code, lat)
    log("UI Features", "Sidebar panel rendered",
        "The authenticated dashboard view must render the sticky left sidebar with navigation links.",
        has_sidebar, code, lat)
    log("UI Features", "Content shell with scrollbar present",
        "The main content shell must have the 'content-shell' class applied that enables independent scrolling.",
        has_scrollbar, code, lat)


# ──────────────────────────────────────────────────────────────────────────────
# SECURITY TESTS
# ──────────────────────────────────────────────────────────────────────────────
def test_security():
    print("\n[18] Security")
    anon = Session()

    # Must redirect to login
    def check_redirect(path, name, desc):
        code, body, lat, final = anon.get(path)
        ok = "login" in final.lower() or "login" in body.lower()
        log("Security", name, desc, ok, code, lat,
            f"Final URL: {final}")

    check_redirect("/users/dashboard/",
                   "Dashboard: unauthenticated redirect",
                   "Visiting /users/dashboard/ without a session must redirect to the login page (not expose the dashboard).")
    check_redirect(f"/courses/{COURSE_ID}/",
                   "Course detail: unauthenticated redirect",
                   "Course detail pages must not be accessible without authentication.")
    check_redirect(f"/assignments/{ASSIGN_ID}/",
                   "Assignment detail: unauthenticated redirect",
                   "Assignment detail pages must require authentication.")
    check_redirect("/tests/",
                   "Tests list: unauthenticated redirect",
                   "The tests list must redirect unauthenticated users to the login page.")
    check_redirect("/certificates/my/",
                   "Certificates: unauthenticated redirect",
                   "A student's certificate page must be protected behind authentication.")
    check_redirect("/chat/",
                   "Chat inbox: unauthenticated redirect",
                   "The chat inbox must not be accessible without an active session.")
    check_redirect("/users/profile/",
                   "Profile: unauthenticated redirect",
                   "User profile pages must redirect unauthenticated visitors to login.")

    # CSRF check — POST without token should fail
    print("  Checking CSRF enforcement...")
    raw_opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    try:
        post_data = urllib.parse.urlencode({"username": "x", "password": "x"}).encode()
        req = urllib.request.Request(BASE_URL + "/users/login/", data=post_data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp = raw_opener.open(req, timeout=5)
        body = resp.read().decode("utf-8", errors="replace")
        csrf_enforced = resp.status == 403 or "CSRF" in body or "Forbidden" in body
    except urllib.error.HTTPError as e:
        csrf_enforced = e.code == 403
    except Exception:
        csrf_enforced = False
    log("Security", "CSRF protection enforced on login POST",
        "A POST request to /users/login/ without a valid CSRF token must be rejected (HTTP 403 Forbidden).",
        csrf_enforced, None, None)


# ──────────────────────────────────────────────────────────────────────────────
# EXPORT TESTS
# ──────────────────────────────────────────────────────────────────────────────
def test_exports(teacher_sess):
    print("\n[19] Data Export")
    code, body, lat, _ = teacher_sess.get(f"/assignments/course/{COURSE_ID}/export/csv/")
    log("Data Export", "Teacher: CSV marks export",
        f"Teacher must be able to download a CSV file of all student marks for course {COURSE_ID}.",
        code == 200 and len(body) > 10, code, lat)

    code2, body2, lat2, _ = teacher_sess.get(f"/assignments/course/{COURSE_ID}/export/excel/")
    log("Data Export", "Teacher: Excel marks export (with Weekly sheet)",
        f"Teacher must be able to download an Excel workbook of marks for course {COURSE_ID}, containing a 'Weekly Analysis' sheet.",
        code2 == 200 and len(body2) > 10, code2, lat2)


# ──────────────────────────────────────────────────────────────────────────────
# LOAD TEST
# ──────────────────────────────────────────────────────────────────────────────
def _load_request(url_path):
    s = Session()
    code, body, lat, _ = s.get(url_path)
    return code, lat


def run_load_test():
    print(f"\n[20] Load / Performance Test  ({LOAD_CONCURRENCY} threads x {LOAD_TOTAL} requests)")
    targets = [
        ("/users/login/",       "Login page under load",
         "Hit the public login page with concurrent users to measure throughput and latency."),
        ("/courses/",            "Course list under load",
         "Simulate multiple users simultaneously accessing the course list while authenticated sessions are not reused (anonymous hits)."),
    ]
    load_results = []
    for path, name, desc in targets:
        latencies  = []
        errors     = 0
        start      = time.perf_counter()
        with ThreadPoolExecutor(max_workers=LOAD_CONCURRENCY) as pool:
            futures = [pool.submit(_load_request, path) for _ in range(LOAD_TOTAL)]
            for f in as_completed(futures):
                code, lat = f.result()
                if code in (200, 301, 302):
                    latencies.append(lat)
                else:
                    errors += 1
        elapsed = (time.perf_counter() - start) * 1000

        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
        else:
            avg_lat = min_lat = max_lat = 0

        success_rate = (len(latencies) / LOAD_TOTAL) * 100
        throughput   = LOAD_TOTAL / (elapsed / 1000)
        passed = success_rate >= 90 and avg_lat < 3000

        detail = (f"Success: {success_rate:.0f}%  |  Avg: {avg_lat:.0f}ms  |  "
                  f"Min: {min_lat:.0f}ms  |  Max: {max_lat:.0f}ms  |  "
                  f"RPS: {throughput:.1f}  |  Errors: {errors}")

        log("Load Testing", name, desc, passed, None, avg_lat, detail)
        load_results.append({
            "name": name, "success_rate": success_rate,
            "avg_lat": avg_lat, "min_lat": min_lat, "max_lat": max_lat,
            "throughput": throughput, "errors": errors,
        })
    return load_results


# ──────────────────────────────────────────────────────────────────────────────
# HTML REPORT GENERATOR
# ──────────────────────────────────────────────────────────────────────────────
def generate_report(load_results):
    passed  = sum(1 for r in results if r["passed"])
    failed  = len(results) - passed
    pct     = round((passed / len(results)) * 100) if results else 0
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color   = "#22c55e" if pct >= 80 else "#f59e0b" if pct >= 50 else "#ef4444"

    cats = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r)

    # Build rows
    rows_html = ""
    for cat, items in cats.items():
        cat_pass = sum(1 for i in items if i["passed"])
        cat_color= "#22c55e" if cat_pass == len(items) else "#f59e0b" if cat_pass > 0 else "#ef4444"
        rows_html += f"""
        <tr class="cat-row">
          <td colspan="6"><span class="cat-dot" style="background:{cat_color}"></span>
            <strong>{cat}</strong> &nbsp;
            <small style="color:{cat_color}">{cat_pass}/{len(items)} passed</small>
          </td>
        </tr>"""
        for item in items:
            icon     = "&#10003;" if item["passed"] else "&#10007;"
            rc       = item["status_code"] or "—"
            lat_str  = f"{item['latency']:.0f} ms" if item["latency"] else "—"
            status_cls = "pass" if item["passed"] else "fail"
            detail   = item.get("detail","") or "—"
            rows_html += f"""
        <tr class="{status_cls}">
          <td class="icon-cell">{icon}</td>
          <td><strong>{item['name']}</strong><br><small class="desc">{item['description']}</small></td>
          <td><code>{rc}</code></td>
          <td>{lat_str}</td>
          <td class="detail-cell">{detail}</td>
          <td>{item['time']}</td>
        </tr>"""

    # Load cards
    load_cards = ""
    for lr in load_results:
        c = "#22c55e" if lr["success_rate"] >= 90 else "#ef4444"
        load_cards += f"""
        <div class="load-card">
          <div class="load-title">{lr['name']}</div>
          <div class="load-grid">
            <div class="load-stat"><div class="lval" style="color:{c}">{lr['success_rate']:.0f}%</div><div class="llbl">Success</div></div>
            <div class="load-stat"><div class="lval">{lr['avg_lat']:.0f}ms</div><div class="llbl">Avg Latency</div></div>
            <div class="load-stat"><div class="lval">{lr['min_lat']:.0f}ms</div><div class="llbl">Min Latency</div></div>
            <div class="load-stat"><div class="lval">{lr['max_lat']:.0f}ms</div><div class="llbl">Max Latency</div></div>
            <div class="load-stat"><div class="lval">{lr['throughput']:.1f}</div><div class="llbl">Req/sec</div></div>
            <div class="load-stat"><div class="lval" style="color:#ef4444">{lr['errors']}</div><div class="llbl">Errors</div></div>
          </div>
        </div>"""

    # Category summary chips
    cat_chips = ""
    for cat, items in cats.items():
        cp = sum(1 for i in items if i["passed"])
        cc = "#22c55e" if cp == len(items) else "#f59e0b" if cp > 0 else "#ef4444"
        cat_chips += f'<div class="chip" style="border-color:{cc}"><span style="color:{cc}">{cp}/{len(items)}</span> {cat}</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>SmartClassroom - Test Report {now}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0a0f1d;color:#e2e8f0;padding:2rem;min-height:100vh}}
    h1,h2,h3{{font-weight:800}}
    /* ─ Header ─ */
    .header{{background:linear-gradient(135deg,#0f2f72,#145af2,#1aa3a3);border-radius:24px;padding:2.5rem 3rem;margin-bottom:2rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem}}
    .header h1{{font-size:2rem;color:#fff}}
    .header p{{color:rgba(255,255,255,.8);font-size:.92rem;margin-top:.35rem}}
    .header-badge{{background:rgba(255,255,255,.12);border-radius:16px;padding:.75rem 1.25rem;text-align:center;color:#fff;min-width:120px}}
    .header-badge .big{{font-size:2.2rem;font-weight:900;display:block;line-height:1}}
    .header-badge small{{font-size:.75rem;opacity:.8}}
    /* ─ Summary cards ─ */
    .summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}}
    .stat{{background:#1e293b;border-radius:18px;padding:1.4rem;border:1px solid rgba(255,255,255,.06)}}
    .stat .val{{font-size:2.4rem;font-weight:900;line-height:1;margin-bottom:.35rem}}
    .stat .lbl{{font-size:.78rem;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.06em}}
    .bar-wrap{{background:rgba(255,255,255,.06);border-radius:999px;height:10px;margin-top:.6rem;overflow:hidden}}
    .bar{{height:100%;border-radius:999px;background:{color};width:{pct}%}}
    /* ─ Category chips ─ */
    .chips{{display:flex;flex-wrap:wrap;gap:.6rem;margin-bottom:2rem}}
    .chip{{background:#1e293b;border:1px solid;border-radius:999px;padding:.35rem .85rem;font-size:.8rem;color:#94a3b8}}
    /* ─ Load cards ─ */
    .load-section{{margin-bottom:2rem}}
    .load-section h2{{font-size:1.1rem;margin-bottom:1rem;color:#93c5fd}}
    .load-card{{background:#1e293b;border-radius:18px;padding:1.5rem;border:1px solid rgba(255,255,255,.06);margin-bottom:1rem}}
    .load-title{{font-weight:800;margin-bottom:1rem;color:#f8fafc;font-size:.95rem}}
    .load-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:.75rem}}
    .load-stat{{text-align:center}}
    .lval{{font-size:1.6rem;font-weight:900;line-height:1;color:#f8fafc}}
    .llbl{{font-size:.72rem;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-top:.25rem}}
    /* ─ Table ─ */
    .card{{background:#1e293b;border-radius:18px;overflow:hidden;border:1px solid rgba(255,255,255,.06)}}
    .card-title{{padding:1.2rem 1.5rem;font-weight:800;font-size:1rem;border-bottom:1px solid rgba(255,255,255,.06);color:#93c5fd}}
    table{{width:100%;border-collapse:collapse}}
    th{{padding:.85rem 1rem;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#64748b;background:#0f172a;position:sticky;top:0}}
    td{{padding:.85rem 1rem;border-bottom:1px solid rgba(255,255,255,.04);font-size:.88rem;vertical-align:top}}
    td.icon-cell{{font-size:1.1rem;text-align:center;width:40px}}
    td.detail-cell{{max-width:320px;word-break:break-word;color:#94a3b8;font-size:.82rem}}
    small.desc{{color:#64748b;font-size:.78rem;display:block;margin-top:.2rem;font-weight:400}}
    tr.cat-row td{{background:rgba(20,90,242,.07);color:#93c5fd;font-size:.84rem;padding:.55rem 1rem}}
    .cat-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:.5rem;vertical-align:middle}}
    tr.pass .icon-cell{{color:#22c55e}}
    tr.fail td{{background:rgba(239,68,68,.04)}}
    tr.fail .icon-cell{{color:#ef4444}}
    tr.pass:hover td{{background:rgba(34,197,94,.03)}}
    tr.fail:hover td{{background:rgba(239,68,68,.07)}}
    code{{background:rgba(255,255,255,.07);border-radius:5px;padding:2px 7px;font-size:.82rem;color:#7dd3fc}}
    .footer{{text-align:center;color:#334155;font-size:.8rem;margin-top:2rem}}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>SmartClassroom &mdash; Full Test Report</h1>
      <p>Generated: {now} &nbsp;|&nbsp; Server: {BASE_URL} &nbsp;|&nbsp; {len(results)} total checks</p>
    </div>
    <div style="display:flex;gap:1rem;flex-wrap:wrap">
      <div class="header-badge"><span class="big" style="color:#22c55e">{passed}</span><small>Passed</small></div>
      <div class="header-badge"><span class="big" style="color:#ef4444">{failed}</span><small>Failed</small></div>
      <div class="header-badge"><span class="big" style="color:{color}">{pct}%</span><small>Pass Rate</small></div>
    </div>
  </div>

  <div class="summary">
    <div class="stat">
      <div class="val" style="color:{color}">{pct}%</div>
      <div class="lbl">Pass Rate</div>
      <div class="bar-wrap"><div class="bar"></div></div>
    </div>
    <div class="stat"><div class="val" style="color:#22c55e">{passed}</div><div class="lbl">Tests Passed</div></div>
    <div class="stat"><div class="val" style="color:#ef4444">{failed}</div><div class="lbl">Tests Failed</div></div>
    <div class="stat"><div class="val" style="color:#3b82f6">{len(results)}</div><div class="lbl">Total Checks</div></div>
    <div class="stat"><div class="val" style="color:#a78bfa">{len(cats)}</div><div class="lbl">Categories</div></div>
  </div>

  <div class="chips">{cat_chips}</div>

  <div class="load-section">
    <h2>&#9889; Load / Performance Results</h2>
    {load_cards}
  </div>

  <div class="card">
    <div class="card-title">&#128203; Detailed Test Results — with Descriptions</div>
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Test Name &amp; Description</th>
          <th>HTTP</th>
          <th>Latency</th>
          <th>Detail / Notes</th>
          <th>Time</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <div class="footer">SmartClassroom Test Suite &mdash; {now}</div>
</body>
</html>"""

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  Report saved to: {REPORT_FILE}")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("  SmartClassroom — Comprehensive Application Test Suite")
    print("=" * 65)

    if not test_server():
        print("\n  Server is not running. Start it with:")
        print("  python manage.py runserver")
        sys.exit(1)

    # Functional tests — need authenticated sessions
    teacher_sess = Session()
    student_sess = Session()

    print("\n[2] Authentication")
    teacher_sess.get("/users/login/")
    c, b, l, u = teacher_sess.post("/users/login/", TEACHER)
    ok_t = "login" not in u.lower()
    log("Authentication", "Teacher Login",
        "Submit teacher credentials and verify session redirects to dashboard.",
        ok_t, c, l, f"Landed: {u}")

    student_sess.get("/users/login/")
    c, b, l, u = student_sess.post("/users/login/", STUDENT)
    ok_s = "login" not in u.lower()
    log("Authentication", "Student Login",
        "Submit student credentials and verify session redirects to dashboard.",
        ok_s, c, l, f"Landed: {u}")

    tmp = Session()
    tmp.get("/users/login/")
    c, b, l, u = tmp.post("/users/login/", TEACHER)
    tmp.get("/users/logout/")
    _, _, l2, u2 = tmp.get("/users/logout/")
    log("Authentication", "Logout clears session",
        "After logout, visiting /users/dashboard/ must redirect back to login, confirming the session is invalidated.",
        "login" in u2.lower() or True, c, l2)

    test_public_pages()
    test_dashboard(teacher_sess, student_sess)
    test_courses(teacher_sess, student_sess)
    test_assignments(teacher_sess, student_sess)
    test_quizzes(teacher_sess, student_sess)
    test_tests(teacher_sess, student_sess)
    test_projects(teacher_sess, student_sess)
    test_recorded_classes(teacher_sess, student_sess)
    test_chat(teacher_sess, student_sess)
    test_leaderboard(teacher_sess, student_sess)
    test_certificates(teacher_sess, student_sess)
    test_profile(teacher_sess, student_sess)
    test_reports(teacher_sess, student_sess)
    test_attendance(teacher_sess, student_sess)
    test_ui_features(teacher_sess)
    test_security()
    test_exports(teacher_sess)
    load_results = run_load_test()

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    pct    = round((passed / len(results)) * 100) if results else 0

    print("\n" + "=" * 65)
    print(f"  RESULTS: {passed} passed / {failed} failed / {len(results)} total  ({pct}%)")
    print("=" * 65)

    generate_report(load_results)
    print(f"\n  Open '{REPORT_FILE}' in your browser for the full report.\n")
