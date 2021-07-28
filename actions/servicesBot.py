import pyodbc
import datetime

driver = 'SQL Server'
server = 'KATOIT'
database = 'OnlineShop'
cursor = None

'''
Select: SELECT * FROM TestDB.dbo.Person
Insert: INSERT INTO TestDB.dbo.Person (Name, Age, City)
                VALUES
                ('Bob',55,'Montreal'),
Update: UPDATE TestDB.dbo.Person
                SET Age = 29,City = 'Montreal'
                WHERE Name = 'Jon'
Delete: DELETE FROM TestDB.dbo.Person 
                WHERE [Name] in ('Bill','Mia')
'''


def get_db(sql_select):
    global cursor
    try:
        conn = pyodbc.connect('Driver={};'
                              'Server={};'
                              'Database={};'
                              'Trusted_Connection=yes;'.format(driver, server, database))
        cursor = conn.cursor()
        cursor.execute(sql_select)
    except Exception as e:
        print('Error Select database: {}'.format(e.args))
    finally:
        list_all = []
        for i in cursor:
            list_all.append(i)
        return list_all


def set_db(sql_insert):
    try:
        conn = pyodbc.connect('Driver={};'
                              'Server={};'
                              'Database={};'
                              'Trusted_Connection=yes;'.format(driver, server, database))
        cursor = conn.cursor()
        cursor.execute('''{}'''.format(sql_insert))
        conn.commit()
    except Exception as e:
        print('Error Insert database: {}'.format(e.args))
        print(sql_insert)
        return False
    finally:
        return True


def insert_order(data_insert):
    """ # listALL = ['id_customer', '0987191143', 'Nguyen Van An', 'address', 'total', 'amount', id_product] # """
    id_customer = data_insert[0]
    phone = data_insert[1]
    name = data_insert[2]
    address = data_insert[3]
    total = data_insert[4]
    amount = data_insert[5]
    id_product = data_insert[6]
    date = datetime.datetime.today().date()

    sql_insert_receipt = '''INSERT INTO {}.dbo.Receipt (id_customer, address, date, total) 
        VALUES ({},'{}',{},{})'''.format(database, id_customer, address, date, total)

    if id_customer is None:
        sql_insert_customer = '''INSERT INTO {}.dbo.Customer (name, phoneNumber) 
                                    VALUES ('{}','{}')'''.format(database, name, phone)
        if set_db(sql_insert_customer):
            sql_select_customer = 'SELECT * FROM {}.dbo.Customer ORDER BY id DESC'.format(database)
            id_customer = get_db(sql_select_customer)[0][0]
            sql_insert_receipt = '''INSERT INTO {}.dbo.Receipt (id_customer, address, date, total) 
                VALUES ({},'{}','{}',{})'''.format(database, id_customer, address, date, total)
    if set_db(sql_insert_receipt):
        sql_select_receipt = 'SELECT * FROM {}.dbo.Receipt ORDER BY id DESC'.format(database)
        id_receipt = get_db(sql_select_receipt)[0][0]
        sql_insert_detail_receipt = '''INSERT INTO {}.dbo.Detail_Receipt (id_receipt, id_product, amount) 
            VALUES ({},{},{})'''.format(database, id_receipt, id_product, amount)
        if set_db(sql_insert_detail_receipt):
            return True
    return False


def select_old_customers(phone_number):
    sql_select = 'SELECT * FROM ' + database + '.dbo.Customer WHERE phoneNumber = ' + phone_number
    sql_select2 = 'SELECT * FROM ' + database + '.dbo.Receipt WHERE id = '
    global cursor
    infoCustomer = []
    try:
        conn = pyodbc.connect('Driver={};'
                              'Server={};'
                              'Database={};'
                              'Trusted_Connection=yes;'.format(driver, server, database))
        cursor = conn.cursor()
        cursor.execute(sql_select)
    except Exception as e:
        print('Error Select database: {}'.format(e.args))
    finally:
        row = cursor.fetchone()
        if row:
            infoCustomer.append(row[1])
            cursor.execute(sql_select2 + str(row[0]) + 'ORDER BY id DESC')
            row2 = cursor.fetchone()
            address = str(row2[2]).split(', ')
            infoCustomer.append(address[2])
            infoCustomer.append(address[1])
            infoCustomer.append(address[0])
            infoCustomer.append(row2[0])
            print('Old Customer: {}'.format(phone_number), infoCustomer)
            return infoCustomer
        else:
            print('Old Customer: None')
            return None


# if __name__ == '__main__':
#     # phone_number = '0987191143'
#     # a = select_old_customers(phone_number)
#     # print(a)
#     # listALL = [1, '0987191143', 'Nguyen Van An', 'Yên Mạc, Yên Mô, Ninh Bình', 320000, 10, 1]
#     # listALL2 = [None, '0987191145', 'Nguyen Van An', 'Yên Thái, Yên Mô, Ninh Bình', 320000, 10, 1]
#     # insert_order(listALL2)
