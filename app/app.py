from flask import Flask, jsonify, abort, make_response, request, url_for, g
from db.queries import Queries
import staff

app = Flask(__name__)
app.config.from_object(__name__)

with app.app_context():
    queries = Queries(app)

@app.teardown_appcontext
def close_db(error):
    queries.close_db()


def make_public_employee(employee):
    new_employee = {}
    for col in employee:
        if col == 'id':
            new_employee['uri'] = url_for('get_employee', employee_id=employee['id'], _external=True)
        else:
            new_employee[col] = employee[col]
    return new_employee


# --- ROUTES --- #
@app.route(staff.Routes.api_employees, methods=['GET'])
def get_employees():
    return jsonify(
        {
            'employees': list(map(make_public_employee, queries.select_all()))
        }
    )


@app.route(staff.Routes.api_employee, methods=['GET'])
def get_employee(employee_id):
    is_exist, employee = queries.select_employee_by_id(employee_id)

    if is_exist:
        code = 200
    else:
        code = 404

    return jsonify(
        {
            'employee': list(map(make_public_employee, employee))
        }
    ), code


@app.route(staff.Routes.api_employees, methods=['POST'])
def create_employee():
    if not request.json or \
            len([x for x in request.json if x in queries.employee_keys]) != \
            len(queries.employee_keys) or \
            not staff.is_date(request.json['birthdate']) or \
            not staff.is_date(request.json['enrollmentdate']) or \
            len(request.json['name']) > 120 or \
            len(request.json['position']) > 120:
        abort(400)

    is_created, employee = queries.insert_employee(request.json)

    if is_created:
        code = 201
    else:
        code = 409

    return jsonify(
        {
            'employee': list(map(make_public_employee, employee))
        }
    ), code


@app.route(staff.Routes.api_employees_filter, methods=['POST'])
def get_employees_with_filter():
    if not request.json or \
            type(request.json) != list:
        abort(400)

    filters = staff.check_filtration(request.json)

    return jsonify(
        {
            'employees': list(map(make_public_employee, queries.select_with_filtration(filters)))
        }
    )

@app.route(staff.Routes.api_employees, methods=['DELETE'])
def delete_employees():
    queries.delete_all()
    return jsonify({'result': True})


@app.route(staff.Routes.api_employee, methods=['DELETE'])
def delete_employee(employee_id):
    is_exist, employee = queries.delete_employee_by_id(employee_id)

    if is_exist:
        code = 200
    else:
        code = 404

    return jsonify(
        {
            'employee': list(map(make_public_employee, employee))
        }
    ), code


@app.route(staff.Routes.api_employees_filter, methods=['DELETE'])
def delete_employees_with_filter():
    if not request.json or \
            type(request.json) != list:
        abort(400)

    filters = staff.check_filtration(request.json)

    is_deleted, deleted_employees = queries.delete_employees(filters)

    if is_deleted:
        code = 200
    else:
        code = 404

    return jsonify(
        {
            'employees': list(map(make_public_employee, deleted_employees))
        }
    ), code


# -------------- #

if __name__ == '__main__':
    app.run(debug=True)
