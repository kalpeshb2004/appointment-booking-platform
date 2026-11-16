import pymysql

# Django mysqlclient (MySQLdb) dhundta. PyMySQL ko MySQLdb bana ke de dete.
# version_info: Django version check karta, naye Django ko 2.2.1+ chahiye.
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()