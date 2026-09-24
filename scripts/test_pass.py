import pymysql

passwords = ["root", "123456", "admin", "password", "1234", "root123", "mariadb", "12345678"]
found = None

for p in passwords:
    try:
        conn = pymysql.connect(host="localhost", user="root", password=p, connect_timeout=1)
        print(f"SUCCESS! MariaDB root password is: '{p}'")
        found = p
        conn.close()
        break
    except Exception as e:
        pass

if not found:
    print("Could not guess MariaDB root password from common list.")
