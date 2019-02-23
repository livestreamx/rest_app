from os.path import abspath, dirname, exists
from shutil import rmtree
from json import loads, dumps
from time import sleep
import subprocess
import requests
import pytest
import allure
import random
from app import staff

from requests.exceptions import ConnectionError, ReadTimeout


# ------------------- DEFAULT STEPS -------------------- #
class BaseTestClass(
    staff.Routes,
    staff.FilterGenerator,
    staff.EmployeeGenerator
):
    standard_timeout = 1 #sec
    standard_loop_count = 10 #times
    start_unavailable_str_length = 121
    stop_unavailable_str_length = 4096

    def get_server(self):
        if hasattr(self, 'server'):
            return self.server
        else:
            raise AttributeError("Server not specified yet!")

    def get_server_host(self):
        return self.get_server().split("/")[-1].split(":")[0]

    def get_server_port(self):
        return self.get_server().split("/")[-1].split(":")[-1]

    def is_app_alive(self):
        try:
            requests.get(
                self.server + "/",
                timeout=self.standard_timeout
            )
        except ConnectionError:
            assert False, \
                "Could not connect to \'" + self.server + "\'!"

    @allure.step('Insert employee')
    def insert_employee(self, employee, is_broken=False):
        response = requests.post(
            self.get_server() + self.api_employees,
            json=employee,
            timeout=self.standard_timeout
        )

        if not is_broken:
            assert response.status_code == 201, \
                "Employee not inserted!"

            assert 'employee' in response.json(), \
                "No information about inserted employee in response!"

            employee = response.json()['employee'][0]

            assert 'uri' in employee, \
                "No URI that describes how to get information about inserted employee!"

            return employee

        else:
            assert response.status_code != 201, \
                "Broken employee construction inserted!"

            assert response.status_code == 400, \
                "Broken employee construction not correctly processed!"

    @allure.step("Default employees insertion")
    def insert_default_employees(self, is_empty_db=False):
        if is_empty_db and len(self.get_employees()) > 0:
            self.delete_employees()

        inserted_employees = []
        for employee in default_employees:
            inserted_employees.append(
                self.insert_employee(employee)
            )
        return inserted_employees

    @allure.step("Deletion of all employees")
    def delete_employees(self):
        try:
            response = requests.delete(
                self.server + self.api_employees,
                timeout=self.standard_timeout
            )

            assert response.status_code == 200, \
                "Employees not deleted!"

        except (ConnectionError, ReadTimeout) as err:
            assert False, \
                "Application not available! Caught exception: " + str(err)

    @allure.step("Getting all employees")
    def get_employees(self):
        response = requests.get(
            self.get_server() + self.api_employees,
            timeout=self.standard_timeout
        )

        assert response.status_code == 200, \
            "Employees not received!"

        assert 'employees' in response.json(), \
            "No information about employees in response!"

        return response.json()['employees']

    @allure.step("Get employee by URI")
    def get_employee_by_uri(self, uri, is_exists=True):
        response = requests.get(
            uri,
            timeout=self.standard_timeout
        )

        if is_exists:
            assert response.status_code == 200, \
                "Information about employee not received!"

            assert 'employee' in response.json(), \
                "No information about employees in response!"

            return response.json()['employee'][0]

        else:
            assert response.status_code == 404, \
                "Response code after selection of not existing URI is not 404!"

    @allure.step("Deletion of employee by URI")
    def delete_employee_by_uri(self, uri, is_exists=True):
        response = requests.delete(
            uri,
            timeout=self.standard_timeout
        )

        if is_exists:
            assert response.status_code == 200, \
                "Employee not deleted!"

            assert 'employee' in response.json(), \
                "No information about deleted employee in response!"

            return response.json()['employee'][0]

        else:
            assert response.status_code == 404, \
                "Response code after deletion of not existing URI is not 404!"

    @allure.step("Comparison of two employees lists by URI")
    def is_employees_lists_equal_by_uri(self, list1, list2):
        not_found_uris = []
        for list1_employee in list1:
            is_found = False
            for list2_employee in list2:
                if list1_employee['uri'] == list2_employee['uri']:
                    is_found = True
                    break

            if not is_found:
                not_found_uris.append(list1_employee['uri'])

        if len(not_found_uris) == 0:
            return True, []
        else:
            return False, not_found_uris

    @allure.step("Comparison of two employees lists without URI")
    def is_employees_list_equal_without_uri(self, inserted_list, default_list):
        not_found_uris = []
        for list1_employee in inserted_list:
            is_found = False
            for list2_employee in default_list:
                if list1_employee['name'] == list2_employee['name'] and \
                        list1_employee['birthdate'] == list2_employee['birthdate'] and \
                        list1_employee['enrollmentdate'] == list2_employee['enrollmentdate'] and \
                        list1_employee['position'] == list2_employee['position']:
                    is_found = True
                    break

            if not is_found:
                not_found_uris.append(list1_employee['uri'])

        if len(not_found_uris) == 0:
            return True, []
        else:
            return False, not_found_uris

    @allure.step("Comparison of two employees lists")
    def is_employees_lists_equal(self, list1, list2):
        not_found_uris = []
        for employee in list1:
            try:
                list2.index(employee)
            except ValueError:
                not_found_uris.append(employee['uri'])

        if len(not_found_uris) == 0:
            return True, []
        else:
            return False, not_found_uris

    @allure.step("Checking match of URI and full employees lists")
    def check_employees_lists_match(self, list1, list2, func):
        assert len(list1) == len(list2), \
            'Length of employees lists not equal!'

        is_equal, not_found_uris = func(list1, list2)

        if len(not_found_uris) != 0:
            attach_dict_to_report(dumps(not_found_uris), "Not found URIs")

        assert is_equal, \
            "Employees not found in other list!"

    @allure.step("Get inserted employees one by one")
    def get_employees_oneByOne(self, inserted_employees):
        received_employees = []
        for employee in inserted_employees:
            received_employees.append(
                self.get_employee_by_uri(employee['uri'])
            )
        return received_employees

    @allure.step("Deletion of employees one by one")
    def delete_employees_oneByOne(self, employees):
        deleted_employees = []
        for employee in employees:
            deleted_employees.append(
                self.delete_employee_by_uri(employee['uri'])
            )
        return deleted_employees

    @allure.step("Empty database checking")
    def is_db_empty(self):
        assert len(self.get_employees()) == 0, \
            "Database not empty!"

    @allure.step("Checking number of existing employees in database")
    def is_db_employees_number_equal_to(self, number):
        assert len(self.get_employees()) == number, \
            "Number of existing employees in database not equal to " + str(number) + "!"

    @allure.step("Checking presense of employees in database ({2})")
    def check_employees_presence(self, employees, is_positive):
        for employee in employees:
            is_employee_exists = is_positive
            try:
                self.get_employee_by_uri(employee['uri'])

                if not is_positive:
                    is_employee_exists = not is_positive

            except AssertionError:
                if is_positive:
                    is_employee_exists = not is_positive

            if is_positive:
                assert is_employee_exists, \
                    "Employee should exist in database!"
            else:
                assert not is_employee_exists, \
                    "Employee should not exist in database!"

    @allure.step("Deletion of random employees")
    def delete_random_employees(self, existed_employees, number_of_deleted_employees):
        deleted_employees = []

        for i in range(number_of_deleted_employees):
            deleted_employees.append(
                existed_employees[random.randint(0, len(existed_employees) - 1)]
            )
            self.delete_employee_by_uri(deleted_employees[i]['uri'])
            existed_employees.remove(deleted_employees[i])

        return existed_employees, deleted_employees

    @allure.step("Getting filtered employees from database")
    def get_filtered_employees_from_db(self, filters_list, position_conflict=False, is_broken=False):
        response = requests.post(
            self.get_server() + self.api_employees_filter,
            json=filters_list,
            timeout=self.standard_timeout
        )

        if position_conflict:
            assert response.status_code == 409, \
                "Position filters conflict not detected!"
            return []

        elif is_broken:
            assert response.status_code == 400, \
                "Request with broken filter not aborted!"
        else:
            assert response.status_code == 200, \
                "Employees not filtered!"

            assert 'employees' in response.json(), \
                "No information about filtered employees in response!"

            return response.json()['employees']

    @allure.step("Deletion of filtered employees from database")
    def delete_filtered_employees_from_db(self, filters_list, is_empty=False, position_conflict=False, is_broken=False):
        response = requests.delete(
            self.get_server() + self.api_employees_filter,
            json=filters_list,
            timeout=self.standard_timeout
        )

        if position_conflict:
            assert response.status_code == 409, \
                "Position filters conflict not detected!"

            return []

        else:
            if not is_empty and not is_broken:
                assert response.status_code == 200, \
                    "Employees not filtered!"

                assert 'employees' in response.json(), \
                    "No information about deleted filtered employees in response!"

                return response.json()['employees']

            elif is_empty:
                assert response.status_code == 404, \
                    "Not empty response for specified filters list!"

                return response.json()['employees']

            elif is_broken:
                assert response.status_code == 400, \
                    "Incorrectly defined filters list not aborted!"

                return []

    @allure.step('Getting filtered employees from list')
    def get_filtered_employees_from_list(self, employees, filters_list):
        filtered_employees = []
        excluded_employees = []

        if len([f for f in filters_list if f['key'] == 'position']) <= 1:

            for employee in employees:
                filtration_results = []
                for filt in filters_list:

                    if filt['key'] == 'position':
                        is_date = False
                    else:
                        is_date = True

                    if staff.is_correct_comparison(
                            employee[staff.filter_columns[filt['key']]],
                            filt['expr'],
                            filt['value'],
                            is_date=is_date
                    ):
                        filtration_results.append(True)
                    else:
                        filtration_results.append(False)
                        break

                if filtration_results.count(False) == 0:
                    filtered_employees.append(employee)
                else:
                    excluded_employees.append(employee)

        else:
            excluded_employees = employees

        return filtered_employees, excluded_employees

    @allure.step("Detection of position conflict")
    def is_position_conflict(self, filters_list):
        if len([f for f in filters_list if f['key'] == 'position']) > 1:
            return True
        else:
            return False

    @allure.step("Stress test \'{1}\'")
    def stress_test(self, test_name, threads=100, loops=10):
        test_file = abspath(dirname(__file__)) + "/" + test_name + ".jmx"
        assert exists(test_file), \
            "Test file not exists!"

        @allure.step("Test execution ({1} threads, {2} loops)")
        def test_execution(test_name, threads, loops):
            stress_test = subprocess.Popen(
                [
                    self.jmeter_path,
                    "-Jjmeter.save.saveservice.output_format=csv",
                    "-n",
                    "-t",
                    test_file,
                    "-Jserver_host=" + self.get_server_host(),
                    "-Jserver_port=" + self.get_server_port(),
                    "-Jthreads=" + str(threads),
                    "-Jloops=" + str(loops),
                    "-l",
                    self.jmeter_jtl_dir + "/" + test_name + ".csv",
                    "-j",
                    self.jmeter_jtl_dir + "/" + test_name + ".log"
                ],
                shell=False
            )
            stress_test.wait()

            return stress_test.returncode

        @allure.step("Test report generation")
        def generate_report(test_name):
            if exists(self.jmeter_jtl_dir + "/" + test_name):
                rmtree(self.jmeter_jtl_dir + "/" + test_name)

            report_generation = subprocess.Popen(
                [
                    self.jmeter_path,
                    "-g",
                    self.jmeter_jtl_dir + "/" + test_name + ".csv",
                    "-o",
                    self.jmeter_jtl_dir + "/" + test_name + "/"
                ],
                shell=False
            )
            report_generation.wait()

            allure.dynamic.link(
                self.report_server + "/" + test_name + '/index.html',
                name='JMeter Dashboard'
            )

            return report_generation.returncode

        result_code = test_execution(test_name, threads, loops)
        if result_code == 0:
            report_code = generate_report(test_name)

        assert result_code == 0, \
            "Test incorrectly completed!"

        assert report_code == 0, \
            "Report not successfully generated!"


# ------------------------------------------------------ #

@pytest.fixture(scope="class")
def test_fixture(request):
    test_params = loads(request.config.getoption("--test_parameters"))
    for p in test_params.keys():
        setattr(request.cls, p, test_params[p])

    app_file = "app.py"
    app_path = abspath(dirname(abspath(dirname(__file__)))) + "/" + app_file

    request.cls.app = subprocess.Popen(
        ['python3', app_path],
        shell=False
    )
    sleep(1)
    request.cls.is_app_alive(request.cls)
    request.cls.delete_employees(request.cls)

    def test_finish():
        request.cls.app.terminate()
        request.cls.app.wait(3000)

    request.addfinalizer(test_finish)


# ------------------------DEFAULTS---------------------- #
default_employees = [
    {
        'name': "Mukhamatnurov Vladislav Eduardovich",
        'birthdate': '02.07.1996',
        'position': 'Senior QA/QC engineer',
        'enrollmentdate': '01.09.2016'
    },
    {
        'name': "Ivanov Ivan Ivanovich",
        'birthdate': '01.01.1990',
        'position': 'Python developer',
        'enrollmentdate': '01.01.2010'
    },
    {
        'name': "Aleksey Alekseevich Alekseev",
        "birthdate": "02.02.1985",
        "position": "Senior python developer",
        "enrollmentdate": "15.03.2005"
    },
    {
        'name': "Petrov Petr Petrovich",
        "birthdate": "02.02.1980",
        "position": "Project manager",
        "enrollmentdate": "05.11.2000"
    },
    {
        'name': "Maksimov Maksim Maksimovich",
        "birthdate": "07.12.1998",
        "position": "QC engineer",
        "enrollmentdate": "24.07.2008"
    }
]


# ------------------------------------------------------ #


def dict_to_json(dictionary):
    js = dumps(dictionary, sort_keys=True, indent=4)
    return js


def attach_dict_to_report(dict, name):
    allure.attach(
        dict_to_json(dict),
        name,
        allure.attachment_type.JSON
    )


# -------------------------TESTS------------------------ #

@allure.story('Positive functional tests')
class Test_functional_positive(BaseTestClass):

    def test_insert_employees(self, test_fixture):
        allure.dynamic.description(
            'Base insertion of default employees with checking responses'
        )
        self.insert_default_employees()

    def test_delete_employees(self):
        allure.dynamic.description('Base deletion of employees with checking response')
        self.delete_employees()

    def test_get_employees_all(self):
        allure.dynamic.description(
            'Insertion and receiving of default employees with comparison of both lists, based on responses data'
        )
        inserted_employees = self.insert_default_employees()
        received_employees = self.get_employees()

        self.check_employees_lists_match(
            inserted_employees,
            received_employees,
            self.is_employees_lists_equal_by_uri
        )

    def test_get_employees_oneByOne(self):
        allure.dynamic.description(
            'Insertion and receiving \'one by one\' of default employees with comparison of both lists, based on responses data'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        self.check_employees_lists_match(
            inserted_employees,
            self.get_employees_oneByOne(inserted_employees),
            self.is_employees_lists_equal_by_uri
        )

    def test_get_employees_compare_all_and_oneByOne(self):
        allure.dynamic.description(
            'Insertion and receiving (full and \'one by one\' methods) of default employees with comparison of received lists, based on responses data'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        self.check_employees_lists_match(
            self.get_employees(),
            self.get_employees_oneByOne(inserted_employees),
            self.is_employees_lists_equal
        )

    def test_insert_employees_compare_with_default(self):
        allure.dynamic.description(
            'Insertion and receiving of default employees with comparison of default and inserted data'
        )
        self.insert_default_employees(is_empty_db=True)

        self.check_employees_lists_match(
            self.get_employees(),
            default_employees,
            self.is_employees_list_equal_without_uri
        )

    def test_delete_all_inserted_employees(self):
        allure.dynamic.description(
            'Insertion and deletion of default employees with database checking'
        )
        self.insert_default_employees(is_empty_db=True)
        self.delete_employees()
        self.is_db_empty()

    def test_delete_inserted_employees_oneByOne(self):
        allure.dynamic.description(
            'Insertion and deletion \'one by one\' of default employees with database checking'
        )
        self.delete_employees_oneByOne(
            self.insert_default_employees(is_empty_db=True)
        )
        self.is_db_empty()

    def test_delete_only_selected_employees(self):
        allure.dynamic.description(
            'Insertion and deletion only random selected employees with database checking'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)
        number_of_deleted_employees = random.randint(1, len(default_employees) - 1)

        inserted_employees, deleted_employees = \
            self.delete_random_employees(
                inserted_employees,
                number_of_deleted_employees
            )

        self.check_employees_presence(deleted_employees, False)
        self.check_employees_presence(inserted_employees, True)

        self.is_db_employees_number_equal_to(
            len(default_employees) - number_of_deleted_employees
        )

    def test_get_age_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by age'
        )
        self.insert_default_employees(is_empty_db=True)
        filt = self.generate_filter('age')

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            [filt]
        )
        filtered_db_employees = self.get_filtered_employees_from_db(
            [filt]
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            filtered_db_employees,
            self.is_employees_list_equal_without_uri
        )

    def test_get_experience_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by experience'
        )
        self.insert_default_employees(is_empty_db=True)
        filt = self.generate_filter('experience')

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            [filt]
        )
        filtered_db_employees = self.get_filtered_employees_from_db(
            [filt]
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            filtered_db_employees,
            self.is_employees_list_equal_without_uri
        )

    def test_get_position_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by position'
        )
        self.insert_default_employees(is_empty_db=True)
        filt = self.generate_filter('position', default_employees)

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            [filt]
        )
        filtered_db_employees = self.get_filtered_employees_from_db(
            [filt]
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            filtered_db_employees,
            self.is_employees_list_equal_without_uri
        )

    def test_get_allTypes_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration based on all filters types'
        )
        self.insert_default_employees(is_empty_db=True)
        filters_list = [
            self.generate_filter('age'),
            self.generate_filter('experience'),
            self.generate_filter('position', default_employees)
        ]

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            filters_list
        )
        filtered_db_employees = self.get_filtered_employees_from_db(
            filters_list
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            filtered_db_employees,
            self.is_employees_list_equal_without_uri
        )

    def test_get_max_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration based on 5 filters'
        )
        self.insert_default_employees(is_empty_db=True)
        filters_list = [
            self.generate_filter('age'),
            self.generate_filter('age'),
            self.generate_filter('experience'),
            self.generate_filter('experience'),
            self.generate_filter('position', default_employees)
        ]

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            filters_list
        )
        filtered_db_employees = self.get_filtered_employees_from_db(
            filters_list
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            filtered_db_employees,
            self.is_employees_list_equal_without_uri
        )

    def test_get_random_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees and checking their random filtration in loop'
        )
        for i in range(self.standard_loop_count):
            self.insert_default_employees(is_empty_db=True)

            filters_list = self.generate_filters_list(default_employees)

            filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
                default_employees,
                filters_list,
            )
            filtered_db_employees = self.get_filtered_employees_from_db(
                filters_list,
                position_conflict=self.is_position_conflict(filters_list)
            )

            self.check_employees_lists_match(
                filtered_default_employees,
                filtered_db_employees,
                self.is_employees_list_equal_without_uri
            )

    def test_delete_age_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees, deletion with age filter, checking that only necessary items deleted and \
             database integrity not broken'
        )
        self.insert_default_employees(is_empty_db=True)
        filt = self.generate_filter('age')

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            [filt]
        )

        if len(filtered_default_employees) == 0:
            is_empty = True
        else:
            is_empty = False

        deleted_db_employees = self.delete_filtered_employees_from_db(
            [filt],
            is_empty=is_empty
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            deleted_db_employees,
            self.is_employees_list_equal_without_uri
        )

        self.check_employees_presence(deleted_db_employees, False)

        self.check_employees_lists_match(
            excluded_employees,
            self.get_employees(),
            self.is_employees_list_equal_without_uri
        )

        self.is_db_employees_number_equal_to(
            len(excluded_employees)
        )

    def test_delete_experience_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees, deletion with experience filter, checking that only necessary items deleted and \
             database integrity not broken'
        )
        self.insert_default_employees(is_empty_db=True)
        filt = self.generate_filter('experience')

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            [filt]
        )

        if len(filtered_default_employees) == 0:
            is_empty = True
        else:
            is_empty = False

        deleted_db_employees = self.delete_filtered_employees_from_db(
            [filt],
            is_empty=is_empty
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            deleted_db_employees,
            self.is_employees_list_equal_without_uri
        )

        self.check_employees_presence(deleted_db_employees, False)

        self.check_employees_lists_match(
            excluded_employees,
            self.get_employees(),
            self.is_employees_list_equal_without_uri
        )

        self.is_db_employees_number_equal_to(
            len(excluded_employees)
        )

    def test_delete_position_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees, deletion with position filter, checking that only necessary items deleted and \
             database integrity not broken'
        )
        self.insert_default_employees(is_empty_db=True)
        filt = self.generate_filter('position', default_employees)

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            [filt]
        )

        if len(filtered_default_employees) == 0:
            is_empty = True
        else:
            is_empty = False

        deleted_db_employees = self.delete_filtered_employees_from_db(
            [filt],
            is_empty=is_empty
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            deleted_db_employees,
            self.is_employees_list_equal_without_uri
        )

        self.check_employees_presence(deleted_db_employees, False)

        self.check_employees_lists_match(
            excluded_employees,
            self.get_employees(),
            self.is_employees_list_equal_without_uri
        )

        self.is_db_employees_number_equal_to(
            len(excluded_employees)
        )

    def test_delete_allTypes_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees, deletion with all filters types, checking that only necessary items deleted and \
             database integrity not broken'
        )
        self.insert_default_employees(is_empty_db=True)
        filters_list = [
            self.generate_filter('age'),
            self.generate_filter('experience'),
            self.generate_filter('position', default_employees)
        ]

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            filters_list
        )

        if len(filtered_default_employees) == 0:
            is_empty = True
        else:
            is_empty = False

        deleted_db_employees = self.delete_filtered_employees_from_db(
            filters_list,
            is_empty=is_empty
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            deleted_db_employees,
            self.is_employees_list_equal_without_uri
        )

        self.check_employees_presence(deleted_db_employees, False)

        self.check_employees_lists_match(
            excluded_employees,
            self.get_employees(),
            self.is_employees_list_equal_without_uri
        )

        self.is_db_employees_number_equal_to(
            len(excluded_employees)
        )

    def test_delete_max_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees, deletion with max filters number, checking that only necessary items deleted and \
             database integrity not broken'
        )
        self.insert_default_employees(is_empty_db=True)
        filters_list = [
            self.generate_filter('age'),
            self.generate_filter('age'),
            self.generate_filter('experience'),
            self.generate_filter('experience'),
            self.generate_filter('position', default_employees)
        ]

        filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
            default_employees,
            filters_list
        )

        if len(filtered_default_employees) == 0:
            is_empty = True
        else:
            is_empty = False

        deleted_db_employees = self.delete_filtered_employees_from_db(
            filters_list,
            is_empty=is_empty
        )

        self.check_employees_lists_match(
            filtered_default_employees,
            deleted_db_employees,
            self.is_employees_list_equal_without_uri
        )

        self.check_employees_presence(deleted_db_employees, False)

        self.check_employees_lists_match(
            excluded_employees,
            self.get_employees(),
            self.is_employees_list_equal_without_uri
        )

        self.is_db_employees_number_equal_to(
            len(excluded_employees)
        )

    def test_delete_random_filtered_employees(self):
        allure.dynamic.description(
            'Insertion default employees, deletion with max filters number, checking that only necessary items deleted and \
             database integrity not broken (in loop)'
        )
        for i in range(self.standard_loop_count):
            self.insert_default_employees(is_empty_db=True)

            filters_list = self.generate_filters_list(default_employees)

            filtered_default_employees, excluded_employees = self.get_filtered_employees_from_list(
                default_employees,
                filters_list
            )

            if len(filtered_default_employees) == 0:
                is_empty = True
            else:
                is_empty = False

            deleted_db_employees = self.delete_filtered_employees_from_db(
                filters_list,
                is_empty=is_empty,
                position_conflict=self.is_position_conflict(filters_list)
            )

            self.check_employees_lists_match(
                filtered_default_employees,
                deleted_db_employees,
                self.is_employees_list_equal_without_uri
            )

            self.check_employees_presence(deleted_db_employees, False)

            self.check_employees_lists_match(
                excluded_employees,
                self.get_employees(),
                self.is_employees_list_equal_without_uri
            )

            self.is_db_employees_number_equal_to(
                len(excluded_employees)
            )


@allure.story('Negative functional tests')
class Test_functional_negative(BaseTestClass):

    def test_insert_error_name(self, test_fixture):
        allure.dynamic.description(
            'Insertion of employee with special symbols at name and checking responses'
        )

        for char in self.get_all_chars():
            self.insert_employee(
                {
                    'name': char,
                    'birthdate': self.generate_date(),
                    'position': self.generate_str(),
                    'enrollmentdate': self.generate_date()
                },
                is_broken=not self.is_char_available(char)
            )

    def test_insert_error_birthdate(self):
        allure.dynamic.description(
            'Insertion of employee with special symbols at birthdate and checking responses'
        )

        for char in self.get_all_chars():
            self.insert_employee(
                {
                    'name': self.generate_str(),
                    'birthdate': char,
                    'position': self.generate_str(),
                    'enrollmentdate': self.generate_date()
                },
                is_broken=not staff.is_date(char)
            )

    def test_insert_error_position(self):
        allure.dynamic.description(
            'Insertion of employee with special symbols at position and checking responses'
        )

        for char in self.get_all_chars():
            self.insert_employee(
                {
                    'name': self.generate_str(),
                    'birthdate': self.generate_date(),
                    'position': char,
                    'enrollmentdate': self.generate_date()
                },
                is_broken=not self.is_char_available(char)
            )

    def test_insert_error_enrollmentdate(self):
        allure.dynamic.description(
            'Insertion of employee with special symbols at enrollmentdate and checking responses'
        )

        for char in self.get_all_chars():
            self.insert_employee(
                {
                    'name': self.generate_str(),
                    'birthdate': self.generate_date(),
                    'position': self.generate_str(),
                    'enrollmentdate': char
                },
                is_broken=not staff.is_date(char)
            )

    def test_insert_long_name(self):
        allure.dynamic.description(
            'Insertion of employee with long name and checking response'
        )

        self.insert_employee(
            {
                'name': self.generate_str(start=self.start_unavailable_str_length, stop=self.stop_unavailable_str_length),
                'birthdate': self.generate_date(),
                'position': self.generate_str(),
                'enrollmentdate': self.generate_date()
            },
            is_broken=True
        )

    def test_insert_long_position(self):
        allure.dynamic.description(
            'Insertion of employee with long position and checking response'
        )

        self.insert_employee(
            {
                'name': self.generate_str(),
                'birthdate': self.generate_date(),
                'position': self.generate_str(start=self.start_unavailable_str_length, stop=self.stop_unavailable_str_length),
                'enrollmentdate': self.generate_date()
            },
            is_broken=True
        )

    def test_insert_incomplete_employee(self):
        allure.dynamic.description(
            'Insertion of employee with incomplete structure (keys) and checking response'
        )

        employee = {
            'name': self.generate_str(),
            'birthdate': self.generate_date(),
            'position': self.generate_str(start=self.start_unavailable_str_length, stop=self.stop_unavailable_str_length),
            'enrollmentdate': self.generate_date()
        }

        for key in employee.keys():
            incomplete_employee = employee.copy()
            incomplete_employee.pop(key)

            self.insert_employee(
                incomplete_employee,
                is_broken=True
            )

    def test_insert_empty_employee(self):
        allure.dynamic.description(
            'Insertion of empty employee and checking response'
        )
        self.insert_employee(
            {},
            is_broken=True
        )

    def test_insert_employee_with_empty_name(self):
        allure.dynamic.description(
            'Insertion of employee with empty name and checking response'
        )
        self.insert_employee(
            {
                'name': '',
                'birthdate': self.generate_date(),
                'position': self.generate_str(),
                'enrollmentdate': self.generate_date()
            },
            is_broken=True
        )

    def test_insert_employee_with_empty_position(self):
        allure.dynamic.description(
            'Insertion of employee with empty position and checking response'
        )
        self.insert_employee(
            {
                'name': self.generate_str(),
                'birthdate': self.generate_date(),
                'position': '',
                'enrollmentdate': self.generate_date()
            },
            is_broken=True
        )

    def test_get_not_existing_employee(self):
        allure.dynamic.description(
            'Getting of not existing employee with checking response'
        )
        self.delete_employees()
        self.get_employee_by_uri(
            self.get_server() + self.api_employees + "/" + str(random.randint(0, self.stop_unavailable_str_length)),
            is_exists=False
        )

    def test_get_broken_uri(self):
        allure.dynamic.description(
            'Trying to get response from broken request for all chars'
        )
        for char in self.get_all_chars():
            self.get_employee_by_uri(
                self.get_server() + self.api_employees + "/" + char,
                is_exists=False
            )

    def test_delete_not_existing_employee(self):
        allure.dynamic.description(
            'Deletion of not existing employee with checking response'
        )
        self.delete_employees()
        self.delete_employee_by_uri(
            self.get_server() + self.api_employees + "/" + str(random.randint(0, self.stop_unavailable_str_length)),
            is_exists=False
        )

    def test_delete_broken_uri(self):
        allure.dynamic.description(
            'Trying to get response from broken deletion request for all chars'
        )
        for char in self.get_all_chars():
            self.delete_employee_by_uri(
                self.get_server() + self.api_employees + "/" + char,
                is_exists=False
            )

    def test_get_with_brokenValue_age_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by age with broken value'
        )
        self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if not c.isdigit()]:
            filt = {
                'key': 'age',
                'expr': random.choice(staff.math_expressions),
                'value': char
            }

            self.get_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

    def test_get_with_emptyValue_age_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by age with empty value'
        )
        self.insert_default_employees(is_empty_db=True)

        self.get_filtered_employees_from_db(
            [
                {
                    'key': 'age',
                    'expr': random.choice(staff.math_expressions),
                    'value': ''
                }
            ],
            is_broken=True
        )

    def test_get_with_brokenExpr_age_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by age with broken expression'
        )
        self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if c not in staff.comparison_symbols]:
            filt = {
                'key': 'age',
                'expr': char,
                'value': self.generate_int_value()
            }

            self.get_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

    def test_get_with_brokenValue_experience_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by experience with broken value'
        )
        self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if not c.isdigit()]:
            filt = {
                'key': 'experience',
                'expr': random.choice(staff.math_expressions),
                'value': char
            }

            self.get_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

    def test_get_with_emptyValue_experience_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by experience with empty value'
        )
        self.insert_default_employees(is_empty_db=True)

        self.get_filtered_employees_from_db(
            [
                {
                    'key': 'experience',
                    'expr': random.choice(staff.math_expressions),
                    'value': ''
                }
            ],
            is_broken=True
        )

    def test_get_with_brokenExpr_experience_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by experience with broken expression'
        )
        self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if c not in staff.comparison_symbols]:
            filt = {
                'key': 'experience',
                'expr': char,
                'value': self.generate_int_value()
            }

            self.get_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

    def test_get_with_brokenValue_position_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by position with broken value'
        )
        self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if not c in self.get_available_chars()]:
            filt = {
                'key': 'position',
                'expr': random.choice(staff.string_expressions),
                'value': char
            }

            self.get_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

    def test_get_with_emptyValue_position_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by position with empty value'
        )
        self.insert_default_employees(is_empty_db=True)

        self.get_filtered_employees_from_db(
            [
                {
                    'key': 'position',
                    'expr': random.choice(staff.string_expressions),
                    'value': ''
                }
            ],
            is_broken=True
        )

    def test_get_with_brokenExpr_position_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking their filtration by position with broken expression'
        )
        self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_available_chars() if c not in staff.str_comparison_symbols]:
            filt = {
                'key': 'position',
                'expr': char,
                'value': self.generate_str()
            }

            self.get_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

    def test_get_with_empty_filter_list(self):
        allure.dynamic.description(
            'Insertion default employees and checking that filtration not passed with empty filters list'
        )
        self.insert_default_employees(is_empty_db=True)

        self.get_filtered_employees_from_db(
            [],
            is_broken=True
        )

    def test_get_with_empty_filters(self):
        allure.dynamic.description(
            'Insertion default employees and checking that filtration not passed with empty filters'
        )
        self.insert_default_employees(is_empty_db=True)

        self.get_filtered_employees_from_db(
            [
                {}, {}, {}, {}, {}
            ],
            is_broken=True
        )

    def test_get_with_brokenKey_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking that filtration not passed with broken filters'
        )
        self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if c not in staff.string_expressions]:
            self.get_filtered_employees_from_db(
                [
                    {
                        'key': char,
                        'expr': random.choice(staff.math_expressions),
                        'value': self.generate_int_value()
                    }
                ],
                is_broken=True
            )

    def test_delete_with_brokenValue_age_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect age filter with broken value, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if not c.isdigit()]:
            filt = {
                'key': 'age',
                'expr': random.choice(staff.math_expressions),
                'value': char
            }

            self.delete_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

            self.check_employees_presence(inserted_employees, True)

            self.is_db_employees_number_equal_to(
                len(inserted_employees)
            )

    def test_delete_with_emptyValue_age_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect age filter with empty value, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        self.delete_filtered_employees_from_db(
            [
                {
                    'key': 'age',
                    'expr': random.choice(staff.math_expressions),
                    'value': ''
                }
            ],
            is_broken=True
        )
        self.check_employees_presence(inserted_employees, True)

        self.is_db_employees_number_equal_to(
            len(inserted_employees)
        )

    def test_delete_with_brokenExpr_age_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect age filter with broken expression, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if c not in staff.comparison_symbols]:
            filt = {
                'key': 'age',
                'expr': char,
                'value': self.generate_int_value()
            }

            self.delete_filtered_employees_from_db(
                [filt],
                is_broken=True
            )

            self.check_employees_presence(inserted_employees, True)

            self.is_db_employees_number_equal_to(
                len(inserted_employees)
            )

    def test_delete_with_brokenValue_experience_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect experience filter with broken value, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if not c.isdigit()]:
            filt = {
                'key': 'experience',
                'expr': random.choice(staff.math_expressions),
                'value': char
            }

            self.delete_filtered_employees_from_db(
                [filt],
                is_broken=True
            )
            self.check_employees_presence(inserted_employees, True)

            self.is_db_employees_number_equal_to(
                len(inserted_employees)
            )

    def test_delete_with_emptyValue_experience_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect experience filter with empty value, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        self.delete_filtered_employees_from_db(
            [
                {
                    'key': 'experience',
                    'expr': random.choice(staff.math_expressions),
                    'value': ''
                }
            ],
            is_broken=True
        )
        self.check_employees_presence(inserted_employees, True)

        self.is_db_employees_number_equal_to(
            len(inserted_employees)
        )

    def test_delete_with_brokenExpr_experience_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect experience filter with broken expression, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if c not in staff.comparison_symbols]:
            filt = {
                'key': 'experience',
                'expr': char,
                'value': self.generate_int_value()
            }

            self.delete_filtered_employees_from_db(
                [filt],
                is_broken=True
            )
            self.check_employees_presence(inserted_employees, True)

            self.is_db_employees_number_equal_to(
                len(inserted_employees)
            )

    def test_delete_with_brokenValue_position_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect position filter with broken value, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if not c in self.get_available_chars()]:
            filt = {
                'key': 'position',
                'expr': random.choice(staff.string_expressions),
                'value': char
            }

            self.delete_filtered_employees_from_db(
                [filt],
                is_broken=True
            )
            self.check_employees_presence(inserted_employees, True)

            self.is_db_employees_number_equal_to(
                len(inserted_employees)
            )

    def test_delete_with_emptyValue_position_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect position filter with empty value, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        self.delete_filtered_employees_from_db(
            [
                {
                    'key': 'position',
                    'expr': random.choice(staff.string_expressions),
                    'value': ''
                }
            ],
            is_broken=True
        )
        self.check_employees_presence(inserted_employees, True)

        self.is_db_employees_number_equal_to(
            len(inserted_employees)
        )

    def test_delete_with_brokenExpr_position_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by incorrect position filter with broken expression, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if c not in staff.str_comparison_symbols]:
            filt = {
                'key': 'position',
                'expr': char,
                'value': self.generate_str()
            }

            self.delete_filtered_employees_from_db(
                [filt],
                is_broken=True
            )
            self.check_employees_presence(inserted_employees, True)

            self.is_db_employees_number_equal_to(
                len(inserted_employees)
            )

    def test_delete_with_empty_filter_list(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion with empty filters list, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        self.delete_filtered_employees_from_db(
            [],
            is_broken=True
        )
        self.check_employees_presence(inserted_employees, True)

        self.is_db_employees_number_equal_to(
            len(inserted_employees)
        )

    def test_delete_with_empty_filters(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion with empty filters, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        self.delete_filtered_employees_from_db(
            [
                {}, {}, {}, {}, {}
            ],
            is_broken=True
        )
        self.check_employees_presence(inserted_employees, True)

        self.is_db_employees_number_equal_to(
            len(inserted_employees)
        )

    def test_delete_with_brokenKey_filter(self):
        allure.dynamic.description(
            'Insertion default employees and checking deletion by filter with broken key, \
            then database integrity control'
        )
        inserted_employees = self.insert_default_employees(is_empty_db=True)

        for char in [c for c in self.get_all_chars() if c not in staff.str_comparison_symbols]:
            self.delete_filtered_employees_from_db(
                [
                    {
                        'key': char,
                        'expr': random.choice(staff.math_expressions),
                        'value': self.generate_int_value()
                    }
                ],
                is_broken=True
            )
            self.check_employees_presence(inserted_employees, True)

            self.is_db_employees_number_equal_to(
                len(inserted_employees)
            )


@allure.story('Stress test: employees insertions')
class Test_stress_insertion(BaseTestClass):
    def test_employees_insertion(self, test_fixture):
        allure.dynamic.description(
            'Stress test with multiple employees insertion'
        )
        self.stress_test(
            "test_stress_insert",
            threads=100,
            loops=10
        )


@allure.story('Stress test: employees extractions')
class Test_stress_extraction(BaseTestClass):
    def test_employees_extraction(self, test_fixture):
        allure.dynamic.description(
            'Stress test with insertion of 1000 employees and multiple trying to get them'
        )
        self.stress_test(
            "test_stress_get_all",
            threads=1000,
            loops=10
        )


@allure.story('Stress test: employees filtration')
class Test_stress_filtration(BaseTestClass):
    def test_employees_filtration(self, test_fixture):
        allure.dynamic.description(
            'Stress test with multiple trying to get filtered employees'
        )
        self.stress_test(
            "test_stress_get_filtered",
            threads=1500,
            loops=10
        )

@allure.story('Stress test: multiple deletion')
class Test_stress_deletion(BaseTestClass):
    def test_employees_deletion(self, test_fixture):
        allure.dynamic.description(
            'Stress test with multiple deletion requests'
        )
        self.stress_test(
            "test_stress_delete_all",
            threads=100,
            loops=10
        )


# ------------------------------------------------------ #

if __name__ == "__main__":
    # -- input parameters from CI, for example
    test_parameters = {
        'server': 'http://localhost:5000',
        'reruns_number': '0',
        'reruns_delay': '0',
        'allure_dir': '/tmp/allure',
        'jmeter_jtl_dir': '/tmp/jmeter',
        'jmeter_path': abspath(dirname(
            abspath(dirname(
                abspath(dirname(
                    __file__
                ))
            ))
        )) + "/apache-jmeter/bin/jmeter",
        'report_server': 'http://localhost:8000'
    }

    test_path = abspath(__file__)

    subprocess.run(
        'py.test -l -p no:cacheprovider --rootdir=' + dirname(test_path) + \
        ' ' + test_path + \
        ' --test_parameters \'' + dumps(test_parameters) + '\'' + \
        " --reruns " + test_parameters['reruns_number'] + \
        " --reruns-delay " + test_parameters['reruns_delay'] + \
        ' --alluredir ' + test_parameters['allure_dir'],
        shell=True
    )
    # -- CI generate Allure report
