import io
import json
import multiprocessing
from contextlib import redirect_stdout




SAFE_MODULES = {
    'math',
    'statistics',
    'itertools',
    'functools',
    'collections',
    'heapq',
    'bisect',
    'json',
    're',
    'numpy',
    'pandas',
    'sklearn',
    'scipy',
}


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root_name = name.split('.')[0]
    if root_name not in SAFE_MODULES:
        raise ImportError(f"Import '{root_name}' is not allowed in coding tests.")
    return __import__(name, globals, locals, fromlist, level)


SAFE_BUILTINS = {
    'abs': abs,
    'all': all,
    'any': any,
    'bool': bool,
    'dict': dict,
    'enumerate': enumerate,
    'filter': filter,
    'float': float,
    'int': int,
    'len': len,
    'list': list,
    'map': map,
    'max': max,
    'min': min,
    'print': print,
    'range': range,
    'reversed': reversed,
    'round': round,
    'set': set,
    'sorted': sorted,
    'str': str,
    'sum': sum,
    'tuple': tuple,
    'zip': zip,
    '__import__': _safe_import,
}


def _normalize_value(value):
    if hasattr(value, 'to_dict'):
        try:
            return _normalize_value(value.to_dict(orient='list'))
        except TypeError:
            return _normalize_value(value.to_dict())
    if hasattr(value, 'tolist'):
        return _normalize_value(value.tolist())
    if isinstance(value, dict):
        return {str(key): _normalize_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_value(item) for item in value]
    return value


def _values_match(actual, expected):
    actual = _normalize_value(actual)
    expected = _normalize_value(expected)
    if isinstance(actual, float) and isinstance(expected, float):
        return abs(actual - expected) <= 1e-6
    return actual == expected


def _parse_args(raw_input):
    parsed = json.loads(raw_input)
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def _worker(code, function_name, cases, queue):
    stdout_buffer = io.StringIO()
    namespace = {
        '__builtins__': SAFE_BUILTINS,
        '__name__': '__main__',
    }
    try:
        with redirect_stdout(stdout_buffer):
            exec(code, namespace, namespace)
            target = namespace.get(function_name)
            if not callable(target):
                raise ValueError(f"Function '{function_name}' was not found in the submitted code.")

            results = []
            for case in cases:
                args = _parse_args(case['input_data'])
                expected = json.loads(case['expected_output'])
                actual = target(*args)
                passed = _values_match(actual, expected)
                results.append({
                    'order': case['order'],
                    'is_sample': case['is_sample'],
                    'weight': case['weight'],
                    'passed': passed,
                    'input_preview': case['input_data'],
                    'expected_preview': case['expected_output'],
                    'actual_preview': json.dumps(_normalize_value(actual)),
                    'explanation': case['explanation'],
                })
        queue.put({'results': results, 'stdout': stdout_buffer.getvalue()})
    except Exception as exc:
        queue.put({
            'error': f'{exc.__class__.__name__}: {exc}',
            'stdout': stdout_buffer.getvalue(),
        })


def _run_cases(code, function_name, cases, timeout_seconds=15):
    context = multiprocessing.get_context('spawn')
    queue = context.Queue()
    process = context.Process(
        target=_worker,
        args=(code, function_name, cases, queue),
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            'error': 'Execution timed out. Please simplify the code or avoid infinite loops.',
            'results': [],
            'stdout': '',
        }
    if queue.empty():
        return {
            'error': 'No grading result was returned.',
            'results': [],
            'stdout': '',
        }
    payload = queue.get()
    payload.setdefault('results', [])
    payload.setdefault('stdout', '')
    return payload


def evaluate_coding_question(question, code, include_hidden=False, run_all=False):
    from .models import Question
    
    if question.question_type != Question.QUESTION_TYPE_CODING:
        return {
            'obtained_marks': 0,
            'total_marks': question.marks,
            'passed_cases': 0,
            'total_cases': 0,
            'sample_cases_count': 0,
            'sample_cases_passed': 0,
            'hidden_cases_count': 0,
            'hidden_cases_passed': 0,
            'results': [],
            'error': '',
            'stdout': '',
        }

    cases_qs = question.test_cases.all()
    if run_all:
        # Run both sample and hidden cases
        pass
    elif include_hidden:
        hidden_cases = cases_qs.filter(is_sample=False)
        cases_qs = hidden_cases if hidden_cases.exists() else question.test_cases.filter(is_sample=True)
    else:
        cases_qs = cases_qs.filter(is_sample=True)

    cases = list(cases_qs.values('order', 'input_data', 'expected_output', 'is_sample', 'weight', 'explanation'))
    if not cases:
        return {
            'obtained_marks': 0,
            'total_marks': question.marks,
            'passed_cases': 0,
            'total_cases': 0,
            'sample_cases_count': 0,
            'sample_cases_passed': 0,
            'hidden_cases_count': 0,
            'hidden_cases_passed': 0,
            'results': [],
            'error': 'No grading test cases are configured for this coding question yet.',
            'stdout': '',
        }

    payload = _run_cases(code, question.expected_function_name, cases)
    if payload.get('error'):
        return {
            'obtained_marks': 0,
            'total_marks': question.marks,
            'passed_cases': 0,
            'total_cases': len(cases),
            'sample_cases_count': sum(1 for c in cases if c['is_sample']),
            'sample_cases_passed': 0,
            'hidden_cases_count': sum(1 for c in cases if not c['is_sample']),
            'hidden_cases_passed': 0,
            'results': payload.get('results', []),
            'error': payload['error'],
            'stdout': payload.get('stdout', ''),
        }

    total_weight = sum(case['weight'] for case in cases) or len(cases)
    passed_weight = sum(result['weight'] for result in payload['results'] if result['passed'])
    obtained = round((passed_weight / total_weight) * question.marks, 2)
    
    sample_cases_count = sum(1 for c in cases if c['is_sample'])
    sample_cases_passed = sum(1 for r in payload['results'] if r['is_sample'] and r['passed'])
    hidden_cases_count = sum(1 for c in cases if not c['is_sample'])
    hidden_cases_passed = sum(1 for r in payload['results'] if not r['is_sample'] and r['passed'])
    
    return {
        'obtained_marks': obtained,
        'total_marks': question.marks,
        'passed_cases': sum(1 for result in payload['results'] if result['passed']),
        'total_cases': len(payload['results']),
        'sample_cases_count': sample_cases_count,
        'sample_cases_passed': sample_cases_passed,
        'hidden_cases_count': hidden_cases_count,
        'hidden_cases_passed': hidden_cases_passed,
        'results': payload['results'],
        'error': '',
        'stdout': payload.get('stdout', ''),
    }
