from os.path import join, abspath, dirname, exists
from flask import g
import sqlite3
import staff

class Queries(object):

    def __init__(self, app):
        self.app_handler = app
        self.database_name = 'rest_app.db'
        self.app_handler.config.update(dict(
            DATABASE=join(app.root_path, self.database_name),
            DEBUG=True,
            SECRET_KEY='development key',
            USERNAME='admin',
            PASSWORD='default'
        ))
        self.app_handler.config.from_envvar('APP_SETTINGS', silent=True)

        self.employee_keys = ['name', 'birthdate', 'position', 'enrollmentdate']

        self.init_db()

    def connect_db(self):
        rv = sqlite3.connect(self.app_handler.config['DATABASE'])
        rv.row_factory = sqlite3.Row
        return rv

    def get_db(self):
        if not hasattr(g, 'sqlite_db'):
            g.sqlite_db = self.connect_db()
        return g.sqlite_db

    def init_db(self):
        with self.app_handler.app_context():
            db_path = abspath(dirname( abspath(dirname(__file__)) )) + "/" +  self.database_name
            if not exists(db_path):
                db = self.get_db()
                with self.app_handler.open_resource(
                        abspath(dirname(__file__)) + '/schema.sql',
                        mode='r'
                ) as f:
                    db.cursor().executescript(f.read())
                db.commit()

    def close_db(self):
        if hasattr(g, 'sqlite_db'):
            g.sqlite_db.close()

    def insert_employee(self, employee_info):
        if len(
            self.execute_query(
                'select id from employees where name = \'' + \
                employee_info['name'] + \
                "\' and birthdate = \'" + \
                employee_info['birthdate'] + \
                '\'',
                commit=False
            )
        ) == 0:

            self.execute_query(
                'insert into employees (name, birthdate, position, enrollmentdate) values (?, ?, ?, ?)',
                vars=[
                     employee_info['name'],
                     employee_info['birthdate'],
                     employee_info['position'],
                     employee_info['enrollmentdate']
                ]
            )

            return True, self.execute_query(
                'select id from employees where name = \'' + \
                employee_info['name'] + \
                "\' and birthdate = \'" + \
                employee_info['birthdate'] + \
                '\'',
                commit=False
            )

        else:
            return False, []

    def delete_all(self):
        self.execute_query('delete from employees')

    def select_all(self):
        return self.execute_query(
            'select * from employees order by id',
            commit=False
        )

    def select_employee_by_id(self, id):
        employee = self.execute_query(
            'select * from employees where id = \'' + str(id) + '\'',
            commit=False
        )

        if len(employee) == 1:
            return True, employee
        else:
            return False, []

    def delete_employees(self, filters_list):
        employees_to_delete = self.select_with_filtration(filters_list)

        if len(employees_to_delete) > 0:
            query = 'delete from employees where '

            ids = []
            for employee in employees_to_delete:
                ids.append('id = \'' + str(employee['id']) + '\'')

            self.execute_query(query + ' or '.join(ids))
            return True, employees_to_delete

        else:
            return False, []

    def delete_employee_by_id(self, id):
        is_exist, employee = self.select_employee_by_id(id)

        if is_exist:
            query = 'delete from employees where id = \'' + str(id) + '\''
            self.execute_query(query)

        return is_exist, employee

    def process_row(self, row):
        row = dict(row)
        return row

    def select_with_filtration(self, filters_list=[]):
        db = self.get_db()
        query = 'select * from employees '
        query_end = ' order by id'

        for filt in filters_list:
            if filt['key'] == 'position':
                query += 'where position ' + filt['expr'] + ' \'' + filt['value'] + '\''
                break

        cur = db.execute(query + query_end)

        filtered_employees = []
        for employee in [self.process_row(r) for r in cur.fetchall()]:

            filtration_results = []
            for filt in filters_list:
                if filt['key'] in ['age', 'experience']:
                    if staff.is_correct_comparison(
                            employee[staff.filter_columns[filt['key']]], filt['expr'], filt['value']
                    ):
                        filtration_results.append(True)
                    else:
                        filtration_results.append(False)
                        break

            if filtration_results.count(False) == 0:
                filtered_employees.append(employee)

        return filtered_employees

    def execute_query(self, query, vars=None, commit=True):
        db = self.get_db()
        if vars:
            cur = db.execute(query, vars)
        else:
            cur = db.execute(query)
        if commit:
            db.commit()
        else:
            return [self.process_row(r) for r in cur.fetchall()]
