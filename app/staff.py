from datetime import datetime, date
from flask import abort
import random

class Routes(object):
    api_path = '/api/v1/'
    api_employees = api_path + "employees"
    api_employee = api_path + 'employees/<int:employee_id>'
    api_employees_filter = api_path + 'employees/filter'

filter_columns = {
    'age': 'birthdate',
    'experience': 'enrollmentdate',
    'position': 'position'
}
filter_pointers = ['key', 'expr', 'value']
math_expressions = ['<', '<=', '=', '!=', '>=', '>']
string_expressions = ['=', '!=']
comparison_symbols = ['=', '>', '!', '<']
str_comparison_symbols = ['=', '!']
min_filters_number = 1
max_filters_number = 5
chars_decimals = range(32, 127)
available_chars_decimals = [45, 46] + list(range(48, 58)) + list(range(65, 91)) + list(range(97, 123))
min_int_filter_value = 0
max_int_filter_value = 65
min_str_length = 1
max_str_length = 120

def convert_str_to_date(s):
    return datetime.strptime(s, "%d.%m.%Y")

def convert_date_to_str(d):
    return d.strftime("%d.%m.%Y")

def is_date(s):
    try:
        convert_str_to_date(s)
        return True
    except ValueError:
        return False


def check_filtration(filters_list):
    if len(filters_list) > max_filters_number or \
            len(filters_list) < min_filters_number:
        abort(400)

    if len([f for f in filters_list if f['key'] == 'position']) > 1:
        abort(409)

    for filt in filters_list:
        if len([k for k in filter_pointers if k not in filt]) != 0 or \
                filt['key'] not in filter_columns.keys() or \
                filt['expr'] not in math_expressions or \
                (filt['key'] == 'position' and filt['expr'] not in string_expressions) or \
                (filt['key'] != 'position' and not filt['value'].isdigit()):
            abort(400)

    return filters_list


def calculate_years(from_date_str):
    from_date = convert_str_to_date(from_date_str)
    today = date.today()
    return today.year - from_date.year - ((today.month, today.day) < (from_date.month, from_date.day))


def is_correct_comparison(existed_value, expr, comparison_value, is_date=True):
    if is_date:
        existed_value = calculate_years(existed_value)
        comparison_value = int(comparison_value)

    if expr == '<':
        return existed_value < comparison_value
    elif expr == '<=':
        return existed_value <= comparison_value
    elif expr == '=':
        return existed_value == comparison_value
    elif expr == '!=':
        return existed_value != comparison_value
    elif expr == '>=':
        return existed_value >= comparison_value
    elif expr == '>':
        return existed_value > comparison_value


class FilterGenerator(object):
    def generate_filter(self, key, employees=None):
        if key != 'position':
            expr = random.choice(math_expressions)
            value = str(
                random.randint(
                    min_int_filter_value,
                    max_int_filter_value
                )
            )
        else:
            expr = random.choice(string_expressions)
            value = employees[
                random.randint(0, len(employees) - 1)
            ]['position']

        return {
            'key': key,
            'expr': expr,
            'value': value
        }

    def generate_filters_list(self, employees, start = min_filters_number + 1, stop = max_filters_number):
        filters_list = []
        for i in range(random.randint(start, stop)):
            filters_list.append(
                self.generate_filter(
                    random.choice(
                        list(filter_columns.keys())
                    ),
                    employees
                )
            )
        return filters_list

class EmployeeGenerator(object):
    def generate_str(self, start=min_str_length, stop=max_str_length):
        name = ''
        payload_length = random.randint(start, stop)
        for index in range(payload_length):
            name += random.choice(
                self.get_available_chars()
            )
        return name

    def generate_date(self):
        day = str(random.randint(0, 28)).zfill(2)
        month = str(random.randint(1, 12)).zfill(2)
        year = str(random.randint(1960, 2000))
        return '.'.join([day, month, year])

    def is_char_available(self, c):
        if c in self.get_available_chars():
            return True
        else:
            return False

    def get_available_chars(self):
        return [chr(c) for c in available_chars_decimals]

    def get_all_chars(self):
        return [chr(c) for c in chars_decimals]

    def generate_int_value(self):
        return str(
            random.randint(
                min_int_filter_value,
                max_int_filter_value
            )
        )

