drop table if exists employees;
create table employees (
  id integer primary key autoincrement,
  name VARCHAR not null,
  birthdate VARCHAR not null,
  position VARCHAR not null,
  enrollmentdate VARCHAR not null
);