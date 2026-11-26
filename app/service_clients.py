"""HTTP clients used by the gateway to talk to the domain services."""
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from types import SimpleNamespace
import json

from flask import abort, current_app
from app.security.jwt_tokens import create_service_token


class RemoteObject(SimpleNamespace):
    """Small template-friendly object built from a service JSON response."""
    def __getitem__(self, name):
        return getattr(self, name)

    def get(self, name, default=None):
        return getattr(self, name, default)

    def __getattr__(self, name):
        if name == 'is_membership_valid' and hasattr(self, 'membership_end'):
            return self.membership_end is None or self.membership_end >= date.today()
        if name == 'is_student_group' and hasattr(self, 'member_type'):
            return self.member_type in ('student', 'postgrad')
        if name == 'age' and getattr(self, 'date_of_birth', None):
            today, born = date.today(), self.date_of_birth
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if name == 'days_remaining' and getattr(self, 'due_date', None):
            return (self.due_date - date.today()).days if self.status == 'borrowed' else 0
        if name == 'days_overdue' and getattr(self, 'due_date', None):
            return max(0, (date.today() - self.due_date).days) if self.status == 'borrowed' else 0
        if name == 'is_overdue' and getattr(self, 'due_date', None):
            return self.status == 'borrowed' and self.due_date < date.today()
        raise AttributeError(name)


_DATE_FIELDS = {
    'date_of_birth', 'membership_start', 'membership_end',
    'loan_date', 'due_date', 'return_date', 'clearance_date', 'expires_at',
}
_DATETIME_FIELDS = {'created_at', 'updated_at', 'last_login', 'fine_paid_at', 'notified_at'}


def _decode(value, key=None):
    if isinstance(value, dict):
        converted = {name: _decode(item, name) for name, item in value.items()}
        if 'category_info' in converted:
            converted['category'] = converted.pop('category_info')
        return RemoteObject(**converted)
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if isinstance(value, str) and key in _DATE_FIELDS:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return value
    if isinstance(value, str) and key in _DATETIME_FIELDS:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


class RemotePagination:
    def __init__(self, payload):
        self.items = [_decode(item) for item in payload.get('data', [])]
        self.page = payload.get('meta', {}).get('page', 1)
        self.pages = payload.get('meta', {}).get('pages', 1)
        self.total = payload.get('meta', {}).get('total', len(self.items))
        self.per_page = payload.get('meta', {}).get('per_page', len(self.items) or 1)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return max(1, self.page - 1)

    @property
    def next_num(self):
        return min(self.pages, self.page + 1)

    def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=2):
        last = 0
        for number in range(1, self.pages + 1):
            if (number <= left_edge or number > self.pages - right_edge or
                    self.page - left_current <= number <= self.page + right_current):
                if last + 1 != number:
                    yield None
                yield number
                last = number


class ServiceClient:
    service = ''

    @property
    def base_url(self):
        root = current_app.config['SERVICE_URLS'][self.service].rstrip('/')
        return f'{root}/api/v1/{self.service}'

    def request(self, method, path='', params=None, payload=None, files=None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url += '?' + urlencode({key: value for key, value in params.items() if value is not None and value != ''})
        headers = {'Authorization': f'Bearer {create_service_token(self.service)}'}
        body = None
        if payload is not None and hasattr(payload, 'to_dict'):
            payload = payload.to_dict(flat=True)
        if files:
            boundary = '----LibraryGatewayBoundary'
            parts = []
            for key, value in (payload or {}).items():
                parts.extend([f'--{boundary}\r\n'.encode(),
                              f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                              str(value).encode('utf-8'), b'\r\n'])
            for key, file_obj in files.items():
                if not file_obj or not getattr(file_obj, 'filename', ''):
                    continue
                raw = file_obj.read()
                file_obj.stream.seek(0)
                filename = file_obj.filename.replace('"', '')
                parts.extend([f'--{boundary}\r\n'.encode(),
                              f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode(),
                              b'Content-Type: application/octet-stream\r\n\r\n', raw, b'\r\n'])
            parts.append(f'--{boundary}--\r\n'.encode())
            body = b''.join(parts)
            headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
        elif payload is not None:
            body = json.dumps(payload, default=str).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        try:
            response = urlopen(Request(url, data=body, headers=headers, method=method), timeout=8)
            raw = response.read()
        except HTTPError as error:
            raw = error.read()
            try:
                error_payload = json.loads(raw.decode('utf-8'))
                message = error_payload.get('message')
            except (ValueError, AttributeError):
                error_payload = {}
                message = None
            if error.code == 409:
                return error_payload
            abort(error.code if error.code in (400, 403, 404, 409, 422) else 502,
                  description=message or f"Dịch vụ {self.service} trả về lỗi.")
        except (URLError, TimeoutError, OSError):
            abort(503, description=f"Dịch vụ {self.service} hiện không khả dụng.")
        if not raw:
            return {}
        try:
            return json.loads(raw.decode('utf-8'))
        except ValueError:
            abort(502, description=f"Dịch vụ {self.service} trả về dữ liệu không hợp lệ.")

    def _data(self, method, path='', params=None, payload=None, files=None):
        response = self.request(method, path, params, payload, files)
        return response.get('data', response)


class BooksClient(ServiceClient):
    service = 'books'

    def get_all_books(self, page=1, per_page=12, search=None, category_id=None,
                      status=None, circulation_type=None, department=None,
                      room=None, sort_by='title', order='asc'):
        return RemotePagination(self.request('GET', '', {
            'page': page, 'per_page': per_page, 'q': search, 'category': category_id,
            'status': status, 'circulation_type': circulation_type, 'department': department,
            'room': room, 'sort': sort_by, 'order': order,
        }))

    def get_all_categories(self):
        return [_decode(item) for item in self._data('GET', 'categories')]

    def get_departments(self):
        return self._data('GET', 'departments')

    def get_opac_facets(self, search=None, category_id=None, availability=None, room=None):
        return self._data('GET', 'facets', {
            'q': search, 'category': category_id, 'availability': availability, 'room': room,
        })

    def get_book_by_id(self, book_id):
        return _decode(self._data('GET', str(book_id)))

    def get_recent_loans(self, book_id, limit=10):
        return loans_client.get_all_loans(book_id=book_id, per_page=limit).items

    def create_book(self, data, cover_file=None):
        has_file = cover_file and getattr(cover_file, 'filename', '')
        result = self.request('POST', '', payload=data, files={'cover_image': cover_file} if has_file else None)
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def update_book(self, book_id, data, cover_file=None):
        has_file = cover_file and getattr(cover_file, 'filename', '')
        result = self.request('PUT', str(book_id), payload=data, files={'cover_image': cover_file} if has_file else None)
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def delete_book(self, book_id):
        result = self.request('DELETE', str(book_id))
        return result.get('success', False), result.get('error') or result.get('message')

    def create_category(self, name, description=None, color='#1B365D'):
        result = self.request('POST', 'categories', payload={'name': name, 'description': description, 'color': color})
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def delete_category(self, category_id):
        result = self.request('DELETE', f'categories/{category_id}')
        return result.get('success', False), result.get('error') or result.get('message')

    def __getattr__(self, name):
        if name in {'get_statistics', 'get_popular_books', 'search_books'}:
            def call(*args, **kwargs):
                if name == 'get_statistics':
                    return self._data('GET', 'statistics')
                if name == 'get_popular_books':
                    return self._data('GET', 'popular', {'limit': kwargs.get('limit', 10)})
                return self._data('GET', 'search', {'q': args[0] if args else kwargs.get('query_str', ''), 'limit': kwargs.get('limit', 10)})
            return call
        raise AttributeError(name)


class MembersClient(ServiceClient):
    service = 'members'

    def get_all_members(self, page=1, per_page=15, search=None, status=None,
                        member_type=None, faculty=None, sort_by='full_name', order='asc'):
        return RemotePagination(self.request('GET', '', {
            'page': page, 'per_page': per_page, 'q': search, 'status': status,
            'type': member_type, 'faculty': faculty, 'sort': sort_by, 'order': order,
        }))

    def get_member_by_id(self, member_id):
        return _decode(self._data('GET', str(member_id)))

    def get_member_by_code(self, code):
        result = self.request('GET', 'by-code', {'code': code})
        if result.get('status') == 'error':
            return None
        return _decode(result.get('data'))

    def lookup_reader_portal(self, identifier, email_or_phone):
        result = self.request('POST', 'lookup', payload={'identifier': identifier, 'verify': email_or_phone})
        if result.get('status') == 'error' or not result.get('data'):
            return None, result.get('message') or 'Không tìm thấy thông tin.'
        return _decode(result.get('data')), None

    def get_faculties(self):
        return self._data('GET', 'faculties')

    def create_member(self, data):
        result = self.request('POST', '', payload=data)
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def update_member(self, member_id, data):
        result = self.request('PUT', str(member_id), payload=data)
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def renew_card(self, member_id, months=12):
        result = self.request('POST', f'{member_id}/renew-card', payload={'months': months})
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def delete_member(self, member_id):
        result = self.request('DELETE', str(member_id))
        return result.get('success', False), result.get('error') or result.get('message')

    def check_graduation_clearance(self, member_id):
        return _decode(self._data('GET', f'{member_id}/clearance'))

    def confirm_graduation_clearance(self, member_id):
        result = self.request('POST', f'{member_id}/clearance', payload={})
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def list_clearance_candidates(self, search=None, graduation_year=None, status_filter=None, faculty=None):
        return [_decode(item) for item in self._data('GET', 'clearance', {
            'q': search, 'graduation_year': graduation_year, 'state': status_filter, 'faculty': faculty,
        })]

    def __getattr__(self, name):
        if name in {'get_statistics', 'search_members'}:
            def call(*args, **kwargs):
                if name == 'get_statistics':
                    return self._data('GET', 'statistics')
                return self._data('GET', 'search', {'q': args[0] if args else kwargs.get('query_str', '')})
            return call
        raise AttributeError(name)


class LoansClient(ServiceClient):
    service = 'loans'

    def get_all_loans(self, page=1, per_page=20, search=None, status=None,
                      member_id=None, book_id=None, sort_by='loan_date', order='desc'):
        return RemotePagination(self.request('GET', '', {
            'page': page, 'per_page': per_page, 'q': search, 'status': status,
            'member_id': member_id, 'book_id': book_id, 'sort': sort_by, 'order': order,
        }))

    def get_loan_by_id(self, loan_id):
        return _decode(self._data('GET', str(loan_id)))

    def create_loan(self, **data):
        result = self.request('POST', '', payload=data)
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def return_book(self, loan_id, **data):
        result = self.request('POST', f'{loan_id}/return', payload=data)
        return _decode(result.get('data')), result.get('fine', 0), result.get('error') or result.get('message')

    def renew_loan(self, loan_id, extension_days=None):
        result = self.request('POST', f'{loan_id}/renew', payload={'extension_days': extension_days})
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def pay_fine(self, loan_id):
        result = self.request('POST', f'{loan_id}/pay-fine', payload={})
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def mark_as_lost(self, loan_id, notes=None, pay_now=False):
        result = self.request('POST', f'{loan_id}/lost', payload={'notes': notes, 'pay_now': pay_now})
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def get_reservations(self, page=1, per_page=20, status=None, search=None, member_id=None, book_id=None):
        return RemotePagination(self.request('GET', 'reservations', {
            'page': page, 'per_page': per_page, 'status': status, 'q': search,
            'member_id': member_id, 'book_id': book_id,
        }))

    def create_reservation(self, book_id, member_id, notes=None):
        result = self.request('POST', 'reservations', payload={
            'book_id': book_id, 'member_id': member_id, 'notes': notes,
        })
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def cancel_reservation(self, reservation_id, member_id=None):
        payload = {'member_id': member_id} if member_id is not None else {}
        result = self.request('POST', f'reservations/{reservation_id}/cancel', payload=payload)
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def fulfill_reservation(self, reservation_id, librarian_id):
        result = self.request('POST', f'reservations/{reservation_id}/fulfill', payload={'librarian_id': librarian_id})
        return _decode(result.get('data')), result.get('error') or result.get('message')

    def __getattr__(self, name):
        if name in {'get_statistics', 'get_overdue_loans'}:
            def call(*args, **kwargs):
                return self._data('GET', 'statistics' if name == 'get_statistics' else 'overdue')
            return call
        raise AttributeError(name)


class ReportsClient(ServiceClient):
    service = 'reports'

    def get_dashboard_summary(self):
        return _decode(self._data('GET', 'dashboard'))

    def get_monthly_loan_chart(self, months=12):
        return self._data('GET', 'monthly-loans', {'months': months})

    def get_top_books(self, limit=10, period_days=30):
        return [_decode(item) for item in self._data('GET', 'top-books', {'limit': limit, 'period': period_days})]

    def get_top_members(self, limit=10, period_days=30):
        return [_decode(item) for item in self._data('GET', 'top-members', {'limit': limit, 'period': period_days})]

    def get_category_distribution(self):
        return self._data('GET', 'category-distribution')

    def get_overdue_report(self):
        return [_decode(item) for item in self._data('GET', 'overdue')]

    def get_fine_report(self, month=None, year=None):
        return _decode(self._data('GET', 'fines', {'month': month, 'year': year}))

    def get_system_alerts(self):
        return self._data('GET', 'alerts')

    def get_faculty_loan_stats(self):
        return self._data('GET', 'faculty-loans')


books_client = BooksClient()
members_client = MembersClient()
loans_client = LoansClient()
reports_client = ReportsClient()
